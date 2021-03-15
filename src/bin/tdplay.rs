use std::path::PathBuf;

use structopt::StructOpt;
use tokio::{io::AsyncReadExt, process, runtime::Runtime, sync::mpsc};
use tracing::debug;

use tapedeck::{
    audio::{dir::AudioDir, init_pulse, Chunk, ChunkLen},
    database::get_database,
    ffmpeg::audio_from_url,
    keyboard::init_key_command,
    logging::init_logging,
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
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(run(&rt, args)).unwrap();
    })
}

async fn run(rt: &Runtime, args: Cli) -> Result<(), anyhow::Error> {
    let _guard = init_logging("tapedeck");
    let db = get_database("tapedeck").await?;

    // Initialize audio output
    let (tx_audio, rx_audio) = mpsc::channel::<Chunk>(2);
    let _pulse = init_pulse(rx_audio);

    // Use keyboard to generate commands
    let (tx_quit, mut rx_quit) = mpsc::unbounded_channel();
    let _key_cmd = init_key_command(tx_quit.clone());

    // Process command line arguments
    match args.music_url {
        // Play one music file and quit
        Some(ref music_url) => {
            let music_url = music_url.to_str().unwrap();
            let mut music_task = audio_from_url(music_url).await.spawn()?;
            let mut audio = music_task.stdout.take().unwrap();
            let mut buf = Chunk::new();

            rt.spawn(async move {
                while let Ok(len) = audio.read_exact(&mut buf).await {
                    tx_audio.send(buf).await.unwrap();
                    if len != Chunk::len() {
                        break;
                    }
                }
                tx_quit.send(()).unwrap();
            });
        }
        None => match args.id {
            // Play list of music files from database
            Some(id) => {
                // Get music_dir from database
                let music_files = AudioDir::get_audio_files(&db, id).await;

                // Read files and send to backpressure queue
                let (tx, mut rx) = mpsc::channel::<process::Child>(2);
                rt.spawn(async move {
                    for file in music_files.iter() {
                        match audio_from_url(file.path.as_str()).await.spawn() {
                            Ok(file) => tx.send(file).await.unwrap(),
                            Err(e) => debug!("{:?}", e),
                        }
                    }
                });

                // Play audio from backpressure queue
                rt.spawn(async move {
                    let mut buf = Chunk::new();
                    while let Some(mut file) = rx.recv().await {
                        let mut reader = file.stdout.take().unwrap();
                        while let Ok(len) = reader.read_exact(&mut buf).await {
                            tx_audio.send(buf).await.unwrap();
                            if len != Chunk::len() {
                                break;
                            }
                        }
                    }
                    tx_quit.send(()).unwrap();
                });
            }
            None => {}
        },
    }

    // Wait for quit signal
    rx_quit.recv().await.unwrap();
    Ok(())
}

fn _println(s: &str) {
    print!("{}\r\n", s);
}
