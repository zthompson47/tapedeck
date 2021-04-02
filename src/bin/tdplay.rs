use std::{io::Write, path::PathBuf};

use bytes::Bytes;
use crossterm::{
    style::{Colorize, Print},
    terminal::{self, EnterAlternateScreen, LeaveAlternateScreen, SetTitle},
    QueueableCommand,
};
use structopt::StructOpt;
use tokio::{
    runtime::Runtime,
    sync::{mpsc, oneshot},
};

use tapedeck::{
    audio_dir::{MediaDir, MediaFile},
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

    // Set window title
    let mut stdout = std::io::stdout();
    stdout.queue(SetTitle("⦗✇ Tapedeck ✇⦘"))?;
    stdout.queue(EnterAlternateScreen)?;
    stdout.flush()?;

    // Enable unbuffered non-blocking stdin for reactive keyboard input
    with_raw_mode(|| {
        let rt = Runtime::new().unwrap();
        rt.block_on(run(&rt, args)).unwrap();
    })?;

    stdout.queue(LeaveAlternateScreen)?;
    stdout.flush()?;

    Ok(())
}

async fn run(rt: &Runtime, args: Cli) -> Result<(), anyhow::Error> {
    let _logging = start_logging("tapedeck");

    // Create sqlite connection pool
    let db = get_database("tapedeck").await?;

    // Task to drive the audio output device
    let (tx_audio, rx_audio) = mpsc::channel::<Bytes>(2);
    let _pulse = start_pulse(rx_audio);

    // Task to accept keyboard as user interface
    let (tx_cmd, mut rx_cmd) = mpsc::unbounded_channel();
    let _ui = start_ui(tx_cmd.clone());

    // Task to control audio playback
    let mut transport = Transport::new(tx_audio);
    let playback = transport.get_handle();

    // Execute command line
    if let Some(music_url) = args.music_url {
        // Play one music url
        transport.extend(vec![MediaFile::from(music_url)]);
        rt.spawn(transport.run(tx_cmd.clone()));
    } else if let Some(id) = args.id {
        // Play an audio directory from the database
        let music_files = MediaDir::get_audio_files(&db, id).await;
        transport.extend(music_files);
        rt.spawn(transport.run(tx_cmd.clone()));
    }

    // Wait for commands and dispatch
    while let Some(command) = rx_cmd.recv().await {
        match command {
            Command::Info => {
                // Concatenate and display text files from media directory
                if let Some(directory) = playback.now_playing().await?.directory(&db).await {
                    if let Some(text_files) = directory.text_files(&db).await {
                        let pager = Pager::from(text_files).await;
                        let (x, y) = terminal::size()?;
                        pager.render(x, y);
                    }
                }
            }
            Command::NextTrack => playback.next_track()?,
            Command::PrevTrack => playback.prev_track()?,
            Command::Print(msg) => print!("{}\r\n", msg.green()),
            Command::Quit => break,
            _ => {}
        }
    }

    Ok(())
}

/*
trait ScreenMode {
    fn render(&self, x: u16, y: u16);
    //fn _render(&self, Vec<String>, //  hmm - pager will need to make calls to render so that it can get the frame rate correct..  pager will only render after keyboard input..  whereas a meter widget will need to refresh frequently[
}
*/



struct Pager {
    lines: Vec<String>,
    cursor: usize,
    // tx,rx for being a 'mode' and able to filter keyboard input
    //  - mode can accept Render trait so all modes have a chance to
    //    redraw the screen as well as intercept input commands
}

impl Pager {
    async fn from(files: Vec<MediaFile>) -> Self {
        let mut lines = String::new();
        for file in files {
            lines.push_str(&tokio::fs::read_to_string(file.location).await.unwrap());
        }
        Self {
            lines: lines.split("\n").map(|line| line.to_owned()).collect(),
            cursor: 0,
        }
    }

    fn render(&self, x: u16, y: u16) {
        //let (_x, y) = size().unwrap();
        let (_x, y) = (x, y);

        use crossterm::{cursor::*, style::*, terminal::*};
        let mut stdout = std::io::stdout();

        stdout.queue(MoveTo(0, 0)).unwrap();
        stdout.queue(Print("---------000-----------\n")).unwrap();
        for i in 0..y - 3 {
            stdout.queue(MoveTo(0, i)).unwrap();
            stdout.queue(Print(&self.lines[i as usize])).unwrap();
            //stdout.queue(Print("\n")).unwrap();
        }
        stdout.flush().unwrap();
    }
}
