use std::time::{Duration, Instant};

use bytes::Bytes;
use tokio::{io::AsyncReadExt, process, sync::mpsc, time::timeout};

use crate::audio_dir::AudioFile;
use crate::ffmpeg::audio_from_url;
use crate::user::Command;

/// Plays a playlist and responds to user commands.
#[derive(Debug)]
pub struct Transport {
    files: Vec<AudioFile>,
    cursor: usize,
    rx_transport: mpsc::UnboundedReceiver<TransportCommand>,
    tx_audio: mpsc::Sender<Bytes>,
}

/// Commands for manipulating playback.
#[derive(Debug)]
pub enum TransportCommand {
    NextTrack,
    PrevTrack,
}

impl Transport {
    /// Create a new Transport out of channel endpoints.
    pub fn new(
        tx_audio: mpsc::Sender<Bytes>,
        rx_transport: mpsc::UnboundedReceiver<TransportCommand>,
    ) -> Self {
        Self {
            files: Vec::new(),
            cursor: 0,
            tx_audio,
            rx_transport,
        }
    }

    /// Add files to the end of the playlist.
    pub fn extend(&mut self, files: Vec<AudioFile>) {
        self.files.extend(files);
    }

    /// Return the file at the cursor.
    pub fn now_playing(&self) -> &AudioFile {
        &self.files[self.cursor]
    }

    /// Stream audio to output device and respond to user commands.
    pub async fn run(mut self, tx_cmd: mpsc::UnboundedSender<Command>) {
        tracing::debug!("----------/??????????????????????????????????????????");
        let mut buf = [0u8; 4096];

        'play: loop {
            // Get next file to play
            let mut audio_reader = match self.get_reader_at_cursor().await {
                Ok(reader) => reader,
                Err(_) => break 'play,
            };

            tx_cmd
                .send(Command::Print(self.now_playing().location.to_string()))
                .unwrap(); // TODO got panic here pressing esc to exit..

            // PrevTrack usually restarts the current track, but it goes back
            // to the _actual_ previous track when called at the beginning of a track.
            // Useful for navigating back and forth in the playlist.
            const DOUBLE_TAP: Duration = Duration::from_millis(333);
            let start_time = Instant::now();

            // Send audio file to output device
            while let Ok(len) = audio_reader.read(&mut buf).await {
                if len == 0 {
                    self.cursor += 1;
                    continue 'play;
                } else {
                    let chunk = Bytes::copy_from_slice(&buf[0..len]);
                    self.tx_audio.send(chunk).await.unwrap();
                }

                // Poll for transport commands that interrupt playback
                if let Ok(Some(cmd)) =
                    timeout(Duration::from_millis(0), self.rx_transport.recv()).await
                {
                    match cmd {
                        TransportCommand::NextTrack => {
                            if self.cursor < self.files.len() - 1 {
                                self.cursor += 1;
                            }
                            continue 'play;
                        }
                        TransportCommand::PrevTrack => {
                            if start_time.elapsed() < DOUBLE_TAP {
                                self.cursor = self.cursor.saturating_sub(1);
                            }
                            continue 'play;
                        }
                    }
                }
            }
            self.cursor += 1;
        }
        tx_cmd.send(Command::Quit).unwrap();
    }

    /// Create a stream of audio data from the current playlist position.
    async fn get_reader_at_cursor(&mut self) -> Result<process::ChildStdout, anyhow::Error> {
        if self.cursor >= self.files.len() {
            return Err(anyhow::Error::msg("cursor index out of bounds, just quit"));
        }
        let file = self.now_playing().location.to_string();
        tracing::debug!("the file:{:?}", file);
        let mut file = audio_from_url(&file).await.spawn()?;
        file.stdout
            .take()
            .ok_or_else(|| anyhow::Error::msg("could not take music file's stdout"))
    }
}
