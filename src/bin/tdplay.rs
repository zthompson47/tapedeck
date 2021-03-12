use std::path::PathBuf;

use libpulse_binding::{
    sample::{Format, Spec},
    stream::Direction,
};
use libpulse_simple_binding::Simple as Pulse;
use sqlx::sqlite::SqlitePool;
use structopt::StructOpt;
use tokio::{io::AsyncReadExt, runtime::Runtime, sync::mpsc};
use tracing::debug;

use tapedeck::{
    audio::dir::AudioDir,
    cmd::ffmpeg,
    database::{get_database_url, MIGRATOR},
    logging::init_logging,
    term,
};

const CHUNK: usize = 4096;

#[derive(StructOpt)]
struct Cli {
    #[structopt(short, long)]
    id: Option<i64>,
    #[structopt(parse(from_os_str))]
    music_url: Option<PathBuf>,
}

fn main() {
    term::with_raw_mode(|| {
        let rt = Runtime::new().unwrap();
        rt.block_on(run(&rt));
    });
}

async fn run(rt: &Runtime) {
    let _guard = init_logging("tapedeck");
    let (tx_audio, mut rx_audio) = mpsc::channel::<[u8; CHUNK]>(1);

    // PulseSink::get_sender|new(&self) -> mpsc::Sender
    std::thread::spawn(move || {
        let spec = Spec {
            format: Format::S16le,
            channels: 2,
            rate: 44100,
        };
        assert!(spec.is_valid());

        let pulse = Pulse::new(
            None,                // Use the default server
            "tapedeck",          // Our application’s name
            Direction::Playback, // We want a playback stream
            None,                // Use the default device
            "Music",             // Description of our stream
            &spec,               // Our sample format
            None,                // Use default channel map
            None,                // Use default buffering attributes
        )
        .unwrap();

        while let Some(buf) = rx_audio.blocking_recv() {
            pulse.drain().unwrap();
            pulse.write(&buf).unwrap();
        }
    });

    // Connect to database
    let pool = SqlitePool::connect(&get_database_url("tapedeck").unwrap())
        .await
        .unwrap();
    MIGRATOR.run(&pool).await.unwrap();

    let args = Cli::from_args();

    match args.music_url {
        // Play single file, directory, or web stream
        Some(ref music_url) => {
            let music_url = music_url.to_str().unwrap();
            let mut source = ffmpeg::read(music_url).await.spawn().unwrap();
            let mut reader = source.stdout.take().unwrap();
            let mut buf: [u8; CHUNK] = [0; CHUNK];

            rt.spawn(async move {
                while let Ok(len) = reader.read_exact(&mut buf).await {
                    if len != CHUNK {
                        debug!("WTF wrong size chunk from ffmpeg reader");
                    }
                    tx_audio.send(buf).await.unwrap();
                }
            });
        }
        None => match args.id {
            // Play music_dir from database
            Some(id) => {
                let music_files = AudioDir::get_audio_files(&pool, id).await;
                let mut playlist = Vec::<tokio::process::Child>::new();
                for file in music_files.iter() {
                    match ffmpeg::read(file.path.as_str()).await.spawn() {
                        Ok(task) => {
                            playlist.push(task);
                        }
                        Err(e) => debug!("{:?}", e),
                    }
                }
                rt.spawn(async move {
                    let mut buf: [u8; CHUNK] = [0; CHUNK];
                    for file in playlist.iter_mut() {
                        debug!("--READ-->> {:?}", file);
                        let mut reader = file.stdout.take().unwrap();
                        while let Ok(len) = reader.read_exact(&mut buf).await {
                            tx_audio.send(buf).await.unwrap();
                            if len != buf.len() {
                                break;
                            }
                        }
                    }
                });
                //return;  TODO quit when playlist is done playing
            }
            None => {}
        },
    }

    KeyCommand::listen_and_quit().await;
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

    async fn listen_and_quit() {
        let mut stdin = tokio::io::stdin();
        let mut buf: [u8; 1] = [0; 1];

        loop {
            stdin.read_exact(&mut buf).await.unwrap();
            match KeyCommand::from_byte(buf[0]) {
                KeyCommand::Quit => {
                    debug!("Got QUIT signal");
                    break;
                }
                KeyCommand::Unknown(cmd) => {
                    debug!("keyboard input >{}<", cmd);
                }
            }
        }
    }
}
