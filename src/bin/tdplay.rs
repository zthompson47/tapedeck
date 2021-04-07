use std::{io::Write, path::PathBuf};

use bytes::Bytes;
use crossterm::{
    cursor,
    event::KeyCode,
    terminal::{LeaveAlternateScreen, SetTitle},
    QueueableCommand,
};
use structopt::StructOpt;
use tokio::{runtime::Runtime, sync::mpsc};

use tapedeck::{
    audio_dir::{MediaDir, MediaFile},
    database::get_database,
    logging::dev_log,
    screen::{Screen, ScreenHandle},
    system::start_pulse,
    terminal::with_raw_mode,
    transport::Transport,
    user::{Command, User, UserHandle},
};

#[derive(StructOpt)]
struct Cli {
    #[structopt(short, long)]
    id: Option<i64>,
    #[structopt(parse(from_os_str))]
    music_url: Option<PathBuf>,
}

fn main() -> Result<(), anyhow::Error> {
    let _ = dev_log();
    let args = Cli::from_args();

    // Set window title
    let mut stdout = std::io::stdout();
    stdout.queue(SetTitle("⦗✇ Tapedeck ✇⦘"))?;
    stdout.queue(cursor::Hide)?;
    stdout.flush()?;

    // Enable unbuffered, non-blocking stdin for reactive keyboard input
    with_raw_mode(|| {
        let rt = Runtime::new().unwrap();
        rt.block_on(run(args)).unwrap();
    })?;

    // Restore terminal
    stdout.queue(cursor::Show)?;
    println!();
    stdout.flush()?;

    Ok(())
}

async fn run(args: Cli) -> Result<(), anyhow::Error> {
    // Create sqlite connection pool
    let db = get_database("tapedeck").await?;

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

    // Execute command line
    if let Some(music_url) = args.music_url {
        // Play one music url
        transport.extend(vec![MediaFile::from(music_url)]);
        tokio::spawn(transport.run(tx_cmd.clone()));
    } else if let Some(id) = args.id {
        // Play an audio directory from the database
        let music_files = MediaDir::get_audio_files(&db, id).await;
        transport.extend(music_files);
        tokio::spawn(transport.run(tx_cmd.clone()));
    }

    let screen = Screen::new().run();

    // Wait for commands and dispatch
    while let Some(command) = rx_cmd.recv().await {
        match command {
            Command::Info => {
                // Concatenate and display text files from media directory
                if let Some(directory) = playback.now_playing().await?.directory(&db).await {
                    if let Some(text_files) = directory.text_files(&db).await {
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
            lines: lines.split("\n").map(|line| line.to_owned()).collect(),
            cursor: 0,
        })
    }

    async fn run(&mut self, ui: UserHandle, screen: ScreenHandle) {
        screen.enter_alternate_screen();
        screen.draw(&self.lines[self.cursor..].to_vec());

        // Take user input channel
        let mut rx_input = ui.take_input().await;
        while let Some(event) = rx_input.recv().await {
            match event.code {
                KeyCode::Char(ch) => match ch {
                    'q' => break,
                    'j' => {
                        //tracing::debug!("j:{}:{}", self.cursor, self.lines.len());
                        if self.cursor < self.lines.len() - 2 {
                            self.cursor += 1;
                            screen.draw(&self.lines[self.cursor..].to_vec());
                        }
                    },
                    'k' => {
                        //tracing::debug!("k:{}:{}", self.cursor, self.lines.len());
                        if self.cursor > 0 {
                            self.cursor -= 1;
                            screen.draw(&self.lines[self.cursor..].to_vec());
                        }
                    },
                    _ => {}
                },
                _ => {}
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
