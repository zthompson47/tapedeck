use std::time::{Duration, Instant};

use bytes::Bytes;
use tokio::{io::AsyncReadExt, process, sync::mpsc, time::timeout};

use crate::ffmpeg::audio_from_url;
use crate::user::Command;

#[derive(Debug)]
pub struct Transport {
    files: Vec<String>,
    cursor: usize,
    rx_transport: mpsc::UnboundedReceiver<TransportCommand>,
    tx_audio: mpsc::Sender<Bytes>,
}

#[derive(Debug)]
pub enum TransportCommand {
    NextTrack,
    PrevTrack,
}

impl Transport {
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

    pub fn queue(&mut self, files: Vec<String>) {
        self.files.extend(files);
    }

    pub async fn run(mut self, tx_cmd: mpsc::UnboundedSender<Command>) {
        let mut buf = [0u8; 4096];

        'play: loop {
            // Get reader for next queued music file
            let mut audio = match self.get_reader().await {
                Ok(reader) => reader,
                Err(_) => break 'play,
            };

            tx_cmd
                .send(Command::Print(self.files[self.cursor].clone()))
                .unwrap();

            // PrevTrack usually restarts the current track, but it goes back
            // to the _actual_ previous track when called at the beginning of a track.
            // Useful for navigating back and forth in the playlist.
            const DOUBLE_TAP: Duration = Duration::from_millis(333);
            let start_time = Instant::now();

            // Send audio file to output device
            while let Ok(len) = audio.read(&mut buf).await {
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

    async fn get_reader(&mut self) -> Result<process::ChildStdout, anyhow::Error> {
        if self.cursor >= self.files.len() {
            return Err(anyhow::Error::msg("cursor index out of bounds, just quit"));
        }
        let file = self.files[self.cursor].as_str();
        tracing::debug!("the file:{:?}", file);
        let mut file = audio_from_url(file).await.spawn()?;
        file.stdout
            .take()
            .ok_or(anyhow::Error::msg("could not take music file's stdout"))
    }
}
