use std::path::PathBuf;

use bytes::BytesMut;
use structopt::StructOpt;
use tokio::{io::AsyncReadExt, process, runtime::Runtime, sync::mpsc};
use tracing::debug;

use tapedeck::{
    audio_dir::{AudioDir, AudioFile},
    database::get_database,
    ffmpeg::audio_from_url,
    keyboard::{init_key_command, KeyCommand},
    logging::init_logging,
    system::init_pulse,
    terminal::with_raw_mode,
};

#[derive(StructOpt)]
struct Cli {
    #[structopt(short, long)]
    id: Option<i64>,
    #[structopt(parse(from_os_str))]
    music_url: Option<PathBuf>,
}

fn main() -> Result<(), anyhow::Error> {
    let args = Cli::from_args();
    with_raw_mode(|| {
        let rt = Runtime::new().unwrap();
        rt.block_on(run(&rt, args)).unwrap();
    })
}

async fn run(rt: &Runtime, args: Cli) -> Result<(), anyhow::Error> {
    let _guard = init_logging("tapedeck");
    let db = get_database("tapedeck").await?;

    // Initialize audio output device
    let (tx_audio, rx_audio) = mpsc::channel::<BytesMut>(2);
    let _pulse = init_pulse(rx_audio);

    // Use keyboard for user interface
    let (tx_cmd, mut rx_cmd) = mpsc::unbounded_channel();
    let _key_cmd = init_key_command(tx_cmd.clone());

    // Control the playback
    let (tx_transport, mut rx_transport) = mpsc::unbounded_channel::<String>();

    // Process command line arguments
    match args.music_url {
        // Play one music file and quit
        Some(ref music_url) => {
            let music_url = music_url.to_str().unwrap();
            let mut music_task = audio_from_url(music_url).await.spawn()?;
            let mut audio = music_task.stdout.take().unwrap();
            const CHUNK: usize = 4096;
            let mut buf = BytesMut::with_capacity(CHUNK);
            buf.resize(CHUNK, 0);

            rt.spawn(async move {
                while let Ok(len) = audio.read_exact(&mut buf).await {
                    tx_audio.send(buf.clone()).await.unwrap();
                    if len != CHUNK {
                        break;
                    }
                }
                tx_cmd.send(KeyCommand::Quit).unwrap();
            });
        }
        None => match args.id {
            // Play list of music files from database
            Some(id) => {
                // Get music_dir from database
                let music_files = AudioDir::get_audio_files(&db, id).await;

                // Queue opened audio files
                const BACK_PRESSURE: usize = 2;
                let (tx_files, mut rx_files) = mpsc::channel::<process::Child>(BACK_PRESSURE);
                rt.spawn(async move {
                    for file in music_files.iter() {
                        match audio_from_url(file.path.as_str()).await.spawn() {
                            Ok(file) => tx_files.send(file).await.unwrap(),
                            Err(e) => debug!("{:?}", e),
                        }
                    }
                });

                // Play audio from backpressure queue
                rt.spawn(async move {
                    const CHUNK: usize = 4096;
                    let mut buf = BytesMut::with_capacity(CHUNK);
                    buf.resize(CHUNK, 0);
                    while let Some(mut file) = rx_files.recv().await {
                        let mut reader = file.stdout.take().unwrap();
                        while let Ok(len) = reader.read_exact(&mut buf).await {
                            tx_audio.send(buf.clone()).await.unwrap();

                            // Check for NextTrack
                            if let Ok(Some(cmd)) = tokio::time::timeout(
                                tokio::time::Duration::from_millis(0),
                                rx_transport.recv(),
                            )
                            .await
                            {
                                match cmd.as_str() {
                                    "next_track" => break,
                                    _ => {}
                                }
                            }

                            // TODO Make sure this will really detect end of file.
                            // https://doc.rust-lang.org/std/io/trait.Read.html#method.read_exact
                            // Looks like we need to check for ErrorKind::UnexpectedEof instead.
                            if len != CHUNK {
                                break;
                            }
                        }
                    }
                    tx_cmd.send(KeyCommand::Quit).unwrap();
                });
            }
            None => {}
        },
    }

    while let Some(cmd) = rx_cmd.recv().await {
        match cmd {
            KeyCommand::NextTrack => {
                tx_transport.send("next_track".into()).unwrap();
            }
            KeyCommand::Quit => break,
            _ => {}
        }
    }

    Ok(())
}

struct _Player {
    files: Vec<AudioFile>,
    last_played: usize,
    state: _PlayerState,
}

enum _PlayerState {
    Playing,
    Paused,
    Stopped,
}
