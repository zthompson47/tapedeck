use std::path::PathBuf;

use bytes::BytesMut;
use structopt::StructOpt;
use tokio::{runtime::Runtime, sync::mpsc};

use tapedeck::{
    audio_dir::AudioDir,
    database::get_database,
    keyboard::{init_key_command, KeyCommand},
    logging::init_logging,
    system::init_pulse,
    terminal::with_raw_mode,
    transport::{Transport, TransportCommand},
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
    let (tx_transport, rx_transport) = mpsc::unbounded_channel::<TransportCommand>();
    let mut transport = Transport::new(tx_audio, rx_transport);

    match args.music_url {
        // Play one music file and quit
        Some(ref music_url) => {
            transport.queue(vec![music_url.to_str().unwrap().to_string()]);
            rt.spawn(transport.run(tx_cmd.clone()));
        }
        None => match args.id {
            // Play list of music files from database
            Some(id) => {
                let music_files = AudioDir::get_audio_files(&db, id).await;
                transport.queue(music_files.iter().map(|x| x.path.clone()).collect());
                rt.spawn(transport.run(tx_cmd.clone()));
            }
            _ => {}
        },
    }

    while let Some(cmd) = rx_cmd.recv().await {
        match cmd {
            KeyCommand::NextTrack => {
                tx_transport.send(TransportCommand::NextTrack).unwrap();
            }
            KeyCommand::PrevTrack => {
                tx_transport.send(TransportCommand::PrevTrack).unwrap();
            }
            KeyCommand::Print(msg) => print!("{}\r\n", msg),
            KeyCommand::Quit => break,
        }
    }

    Ok(())
}
