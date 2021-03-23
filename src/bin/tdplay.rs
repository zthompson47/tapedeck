use std::{io::Write, path::PathBuf};

use bytes::Bytes;
use crossterm::{style::Colorize, terminal::SetTitle, QueueableCommand};
use structopt::StructOpt;
use tokio::{runtime::Runtime, sync::mpsc};

use tapedeck::{
    audio_dir::{AudioDir, AudioFile},
    database::get_database,
    logging::start_logging,
    system::start_pulse,
    terminal::with_raw_mode,
    transport::{Transport, TransportCommand},
    user::{start_ui, Command},
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

    let mut stdout = std::io::stdout();
    stdout.queue(SetTitle("⦗✇ Tapedeck ✇⦘"))?;
    stdout.flush()?;

    with_raw_mode(|| {
        let rt = Runtime::new().unwrap();
        rt.block_on(run(&rt, args)).unwrap();
    })
}

/// Run the application.
async fn run(rt: &Runtime, args: Cli) -> Result<(), anyhow::Error> {
    let _ = start_logging("tapedeck");
    let db = get_database("tapedeck").await?;

    // Initialize audio output device
    let (tx_audio, rx_audio) = mpsc::channel::<Bytes>(2);
    let _ = start_pulse(rx_audio);

    // Use keyboard as user interface
    let (tx_cmd, mut rx_cmd) = mpsc::unbounded_channel();
    let _ = start_ui(tx_cmd.clone());

    // Control the playback
    let (tx_transport, rx_transport) = mpsc::unbounded_channel::<TransportCommand>();
    let mut transport = Transport::new(tx_audio, rx_transport);

    match args.music_url {
        // Play one music url
        Some(ref music_url) => {
            transport.extend(vec![AudioFile::from(music_url)]);
            rt.spawn(transport.run(tx_cmd.clone()));
        }
        None => match args.id {
            // Play an audio directory from the database
            Some(id) => {
                let music_files = AudioDir::get_audio_files(&db, id).await;
                transport.extend(music_files);
                rt.spawn(transport.run(tx_cmd.clone()));
            }
            _ => {}
        },
    }

    while let Some(command) = rx_cmd.recv().await {
        match command {
            Command::Info => {}
            Command::NextTrack => {
                tx_transport.send(TransportCommand::NextTrack)?;
            }
            Command::PrevTrack => {
                tx_transport.send(TransportCommand::PrevTrack)?;
            }
            Command::Print(msg) => print!("{}\r\n", msg.green()),
            Command::Quit => break,
            _ => {}
        }
    }

    Ok(())
}
