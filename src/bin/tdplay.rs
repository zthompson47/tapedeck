use std::{
    io::Read,
    path::PathBuf,
    thread::{self, JoinHandle},
};

use libpulse_binding::{
    sample::{Format, Spec},
    stream::Direction,
};
use libpulse_simple_binding::Simple as Pulse;
use structopt::StructOpt;
use tokio::{io::AsyncReadExt, process, runtime::Runtime, sync::mpsc};
use tracing::debug;

use tapedeck::{
    audio::dir::AudioDir, database::get_database, ffmpeg::audio_from_url, logging::init_logging,
    terminal::with_raw_mode,
};

const CHUNK: usize = 4096;

type Chunk = [u8; CHUNK];

trait ChunkLen {
    fn len() -> usize {
        CHUNK
    }
    fn new() -> Chunk {
        [0; CHUNK]
    }
}

impl ChunkLen for Chunk {}

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

    let (tx_audio, rx_audio) = mpsc::channel::<Chunk>(2);
    let _pulse = init_pulse(rx_audio);

    let (tx_quit, mut rx_quit) = mpsc::unbounded_channel();
    let _key_cmd = init_key_command(tx_quit.clone());

    match args.music_url {
        Some(ref music_url) => {
            // Play single file, directory, or web stream
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
            Some(id) => {
                // Get music_dir from database
                let music_files = AudioDir::get_audio_files(&db, id).await;

                // Backpressure queue to limit open files
                let (tx, mut rx) = mpsc::channel::<process::Child>(2);

                // Read the files
                rt.spawn(async move {
                    for file in music_files.iter() {
                        match audio_from_url(file.path.as_str()).await.spawn() {
                            Ok(task) => tx.send(task).await.unwrap(),
                            Err(e) => debug!("{:?}", e),
                        }
                    }
                });

                // Play the audio
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

enum KeyCommand {
    Quit,
    Unknown(u8),
}

impl KeyCommand {
    fn from_byte(b: u8) -> Self {
        match b {
            3 | 113 => Self::Quit,
            _ => Self::Unknown(b),
        }
    }
}

fn init_key_command(tx_quit: mpsc::UnboundedSender<()>) -> JoinHandle<()> {
    thread::spawn(move || {
        let mut stdin = std::io::stdin();
        let mut buf: [u8; 1] = [0; 1];

        loop {
            stdin.read_exact(&mut buf).unwrap();
            match KeyCommand::from_byte(buf[0]) {
                KeyCommand::Quit => {
                    debug!("Got QUIT signal");
                    tx_quit.send(()).unwrap();
                    break;
                }
                KeyCommand::Unknown(cmd) => {
                    debug!("keyboard input >{}<", cmd);
                }
            }
        }
    })
}

fn init_pulse(mut rx_audio: mpsc::Receiver<Chunk>) -> JoinHandle<()> {
    thread::spawn(move || {
        let spec = Spec {
            format: Format::S16le,
            channels: 2,
            rate: 44100,
        };
        if !spec.is_valid() {
            debug!("Spec not valid: {:?}", spec);
            panic!("!!!!!!!!SPEC NOT VALID!!!!!!!!");
        }

        let pulse = match Pulse::new(
            None,                // Use the default server
            "tapedeck",          // Our application’s name
            Direction::Playback, // We want a playback stream
            None,                // Use the default device
            "Music",             // Description of our stream
            &spec,               // Our sample format
            None,                // Use default channel map
            None,                // Use default buffering attributes
        ) {
            Ok(pulse) => pulse,
            Err(e) => {
                debug!("{:?}", e);
                panic!("!!!!!!!!NO PULSEAUDIO!!!!!!!!");
            }
        };

        while let Some(buf) = rx_audio.blocking_recv() {
            match pulse.write(&buf) {
                Ok(_) => {}
                Err(e) => debug!("{:?}", e),
            }
            //pulse.drain().unwrap();
        }
    })
}

fn _println(s: &str) {
    print!("{}\r\n", s);
}
