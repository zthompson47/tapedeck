use std::{
    path::PathBuf,
    thread::{self, JoinHandle},
};

use crossterm::terminal;
use libpulse_binding::{
    sample::{Format, Spec},
    stream::Direction,
};
use libpulse_simple_binding::Simple as Pulse;
use structopt::StructOpt;
use tokio::{io::AsyncReadExt, sync::mpsc};
use tracing::debug;

use tapedeck::{
    audio::dir::AudioDir,
    database::{get_db_pool, MIGRATOR},
    ffmpeg::audio_from_url,
    logging::init_logging,
};

const CHUNK: usize = 4096;

#[derive(StructOpt)]
struct Cli {
    #[structopt(short, long)]
    id: Option<i64>,
    #[structopt(parse(from_os_str))]
    music_url: Option<PathBuf>,
}

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {
    let _guard = init_logging("tapedeck");
    let args = Cli::from_args();

    let db = get_db_pool("tapedeck").await?;
    MIGRATOR.run(&db).await?;

    let (tx_audio, rx_audio) = mpsc::channel::<[u8; CHUNK]>(2);
    let _pulse = init_pulse(rx_audio);

    match args.music_url {
        // Play single file, directory, or web stream
        Some(ref music_url) => {
            let music_url = music_url.to_str().unwrap();
            let mut source = audio_from_url(music_url).await.spawn()?;
            let mut reader = source.stdout.take().unwrap();
            let mut buf: [u8; CHUNK] = [0; CHUNK];

            tokio::spawn(async move {
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
                let music_files = AudioDir::get_audio_files(&db, id).await;
                let mut playlist = Vec::<tokio::process::Child>::new();
                for file in music_files.iter() {
                    match audio_from_url(file.path.as_str()).await.spawn() {
                        Ok(task) => playlist.push(task),
                        Err(e) => debug!("{:?}", e),
                    }
                }
                tokio::spawn(async move {
                    let mut buf: [u8; CHUNK] = [0; CHUNK];
                    for file in playlist.iter_mut() {
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

    async fn listen_and_quit() {
        let mut stdin = tokio::io::stdin();
        let mut buf: [u8; 1] = [0; 1];

        terminal::enable_raw_mode().unwrap();
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
        terminal::disable_raw_mode().unwrap();
    }
}

fn init_pulse(mut rx_audio: mpsc::Receiver<[u8; CHUNK]>) -> JoinHandle<()> {
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
