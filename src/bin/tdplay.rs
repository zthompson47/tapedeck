use std::{io::Write, path::PathBuf};

use bytes::Bytes;
use clap::Parser;
use crossterm::{event::KeyCode, terminal::LeaveAlternateScreen, QueueableCommand};
use tokio::sync::mpsc;

use tapedeck::{
    audio_dir::{MediaDir, MediaFile},
    database::Store,
    logging,
    screen::{Screen, ScreenHandle},
    system::start_pulse,
    terminal::TuiMode,
    transport::Transport,
    user::{Command, User, UserHandle},
};

#[derive(Parser)]
struct Cli {
    #[arg(short, long)]
    id: Option<i64>,
    music_url: Option<PathBuf>,
}

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {
    let _log = logging::init();
    tracing::info!("Start tdplay");

    let args = Cli::parse();

    if let Ok(_tui) = TuiMode::enter() {
        run(args).await?;
    }

    Ok(())
}

async fn run(args: Cli) -> Result<(), anyhow::Error> {
    let store = Store::new()?;

    // Channel for processing top-level commands
    let (tx_cmd, mut rx_cmd) = mpsc::unbounded_channel();

    // Task to drive the audio output device
    let (tx_audio, rx_audio) = mpsc::channel::<Bytes>(2);
    let _pulse = start_pulse(rx_audio);

    // Task to accept keyboard as user interface
    let user = User::new(tx_cmd.clone());
    let ui = user.get_handle();
    tokio::spawn(user.run());

    // Task to control audio playback
    let mut transport = Transport::new(tx_audio);
    let playback = transport.get_handle();

    // Start playing the audio files.
    let music_files = if let Some(music_url) = args.music_url {
        vec![MediaFile::from(music_url)]
    } else if let Some(id) = args.id {
        MediaDir::get_audio_files(&store, id)?
    } else {
        vec![]
    };
    transport.extend(music_files);
    tokio::spawn(transport.run(tx_cmd.clone()));

    let screen = Screen::new().run();

    // Wait for commands and dispatch
    while let Some(command) = rx_cmd.recv().await {
        match command {
            Command::Info => {
                // Concatenate and display text files from media directory
                if let Some(directory) = playback.now_playing().await?.directory(&store) {
                    if let Some(text_files) = directory.text_files(&store) {
                        if let Ok(mut pager) = Pager::new(text_files).await {
                            let screen = screen.clone();
                            let ui = ui.clone();
                            tokio::spawn(async move { pager.run(ui, screen).await });
                        }
                    }
                }
            }
            Command::NextTrack => playback.next_track()?,
            Command::PrevTrack => playback.prev_track()?,
            Command::Print(message) => screen.status(message),
            Command::Quit => break,
        }
    }

    Ok(())
}

struct Pager {
    lines: Vec<String>,
    cursor: usize,
}

impl Pager {
    async fn new(files: Vec<MediaFile>) -> Result<Pager, std::io::Error> {
        let mut lines = String::new();
        for file in files {
            lines.push_str(&tokio::fs::read_to_string(file.location).await?);
        }
        Ok(Self {
            lines: lines.split('\n').map(|line| line.to_owned()).collect(),
            cursor: 0,
        })
    }

    async fn run(&mut self, ui: UserHandle, screen: ScreenHandle) {
        screen.enter_alternate_screen();
        screen.draw(&self.lines[self.cursor..]);

        // Take user input channel
        let mut rx_input = ui.take_input().await;
        while let Some(event) = rx_input.recv().await {
            if let KeyCode::Char(ch) = event.code {
                match ch {
                    'q' => break,
                    'j' => {
                        //tracing::debug!("j:{}:{}", self.cursor, self.lines.len());
                        if self.cursor < self.lines.len() - 2 {
                            self.cursor += 1;
                            screen.draw(&self.lines[self.cursor..]);
                        }
                    }
                    'k' => {
                        //tracing::debug!("k:{}:{}", self.cursor, self.lines.len());
                        if self.cursor > 0 {
                            self.cursor -= 1;
                            screen.draw(&self.lines[self.cursor..]);
                        }
                    }
                    _ => {}
                }
            }
        }

        screen.leave_alternate_screen();
    }
}

impl Drop for Pager {
    fn drop(&mut self) {
        let mut stdout = std::io::stdout();
        stdout.queue(LeaveAlternateScreen).unwrap();
        stdout.flush().unwrap();
    }
}
