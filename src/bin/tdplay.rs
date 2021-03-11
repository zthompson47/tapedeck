use std::path::PathBuf;

use libpulse_binding::sample::{Format, Spec};
use libpulse_binding::stream::Direction;
use libpulse_simple_binding::Simple as Pulse;
use structopt::StructOpt;
use tokio::io::AsyncReadExt;
use tokio::runtime::Runtime;
use tokio::sync::mpsc;
use tracing::debug;

use tapedeck::{cmd, logging::init_logging, term};

#[derive(StructOpt)]
struct Cli {
    #[structopt(parse(from_os_str))]
    fname: PathBuf,
}

fn main() {
    term::with_raw_mode(|| {
        let rt = Runtime::new().unwrap();
        rt.block_on(run(&rt));
    });
}

async fn run(rt: &Runtime) {
    let _guard = init_logging("tapedeck");
    let (tx_audio, mut rx_audio) = mpsc::unbounded_channel::<[u8; 4096]>();

    std::thread::spawn(move || {
        let spec = Spec {
            format: Format::S16le,
            channels: 2,
            rate: 44100,
        };
        assert!(spec.is_valid());

        let s = Pulse::new(
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
            s.write(&buf).unwrap();
            // s.drain().unwrap();
        }
    });

    let args = Cli::from_args();
    let music_file = args.fname.to_str().unwrap();
    let mut source = cmd::ffmpeg::read(music_file).await.spawn().unwrap();
    let mut reader = source.stdout.take().unwrap();
    let mut buf: [u8; 4096] = [0; 4096];

    rt.spawn(async move {
        while let Ok(len) = reader.read_exact(&mut buf).await {
            if len != 4096 {
                dbg!("WTF wrong size chunk from ffmpeg reader");
            }
            tx_audio.send(buf).unwrap();
        }
    });

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
