use std::time::{Duration, Instant};

use bytes::Bytes;
use futures::future::FutureExt;
use tokio::sync::oneshot;
use tokio::{io::AsyncReadExt, process, sync::mpsc, task::unconstrained};

use crate::audio_dir::MediaFile;
use crate::ffmpeg::audio_from_url;
use crate::user::Command;

/// Plays a playlist and responds to user commands.
#[derive(Debug)]
pub struct Transport {
    files: Vec<MediaFile>,
    cursor: usize,
    tx_transport_cmd: mpsc::UnboundedSender<TransportCommand>,
    rx_transport_cmd: mpsc::UnboundedReceiver<TransportCommand>,
    tx_audio: mpsc::Sender<Bytes>,
}

/// Commands for manipulating playback.
#[derive(Debug)]
pub enum TransportCommand {
    NextTrack,
    PrevTrack,
    NowPlaying(oneshot::Sender<MediaFile>),
}

pub struct TransportHandle {
    pub tx_transport_cmd: mpsc::UnboundedSender<TransportCommand>,
}

impl TransportHandle {
    pub fn next_track(&self) -> Result<(), anyhow::Error> {
        self.tx_transport_cmd.send(TransportCommand::NextTrack)?;
        Ok(())
    }
    pub fn prev_track(&self) -> Result<(), anyhow::Error> {
        self.tx_transport_cmd.send(TransportCommand::PrevTrack)?;
        Ok(())
    }
    pub async fn now_playing(&self) -> Result<MediaFile, anyhow::Error> {
        let (tx, rx) = oneshot::channel();
        self.tx_transport_cmd
            .send(TransportCommand::NowPlaying(tx))?;
        Ok(rx.await?)
    }
}

impl Transport {
    /// Create a new Transport out of channel endpoints.
    pub fn new(tx_audio: mpsc::Sender<Bytes>) -> Self {
        let (tx_transport_cmd, rx_transport_cmd) = mpsc::unbounded_channel();
        Self {
            files: Vec::new(),
            cursor: 0,
            tx_audio,
            tx_transport_cmd,
            rx_transport_cmd,
        }
    }

    pub fn get_handle(&self) -> TransportHandle {
        TransportHandle {
            tx_transport_cmd: self.tx_transport_cmd.clone(),
        }
    }

    /// Add files to the end of the playlist.
    pub fn extend(&mut self, files: Vec<MediaFile>) {
        self.files.extend(files);
    }

    /// Return the file at the cursor.
    pub fn now_playing(&self) -> &MediaFile {
        &self.files[self.cursor]
    }

    /// Stream audio to output device and respond to user commands.
    pub async fn run(mut self, tx_cmd: mpsc::UnboundedSender<Command>) {
        let mut buf = [0u8; 4096];

        'play: loop {
            // Get next file to play
            let mut audio_child = match self.get_audio_child_at_cursor().await {
                Ok(child) => child,
                Err(err) => {
                    tracing::error!("{err}");
                    break 'play;
                }
            };
            let mut audio_reader = audio_child
                .stdout
                .take()
                .ok_or_else(|| anyhow::Error::msg("could not take music file's stdout"))
                .unwrap(); // TODO propagate error

            let mut audio_err = audio_child.stderr.take().unwrap();

            let path = std::path::PathBuf::from(&self.now_playing().location);
            tx_cmd
                .send(Command::Print(
                    path.file_name().unwrap().to_string_lossy().to_string(), // TODO ? Cow?
                ))
                .unwrap(); // TODO got panic here pressing esc to exit..

            // PrevTrack usually restarts the current track, but it goes back
            // to the _actual_ previous track when called at the beginning of
            // a track. Useful for navigating back and forth in the playlist.
            const DOUBLE_TAP: Duration = Duration::from_millis(333);
            let start_time = Instant::now();

            tracing::debug!("---------->> about to play at cursor {}", self.cursor);
            tracing::debug!("---------->> audio_reader: {:?}", audio_reader);

            // Send audio file to output device
            while let Ok(len) = audio_reader.read(&mut buf).await {
                //tracing::debug!("---------->> READING AUDIO OUTPUT");
                if len == 0 {
                    tracing::debug!("---------->> LEN IS 0");
                    // TODO error handling in general
                    let success = audio_child.wait().await.unwrap().success();
                    if !success {
                        let mut err_buf = String::new();
                        audio_err.read_to_string(&mut err_buf).await.unwrap();
                        tracing::debug!("{err_buf}");
                        break;
                    }
                    tracing::debug!("====>> audio_child exit success: {success}");
                    self.cursor += 1;
                    continue 'play;
                } else {
                    let chunk = Bytes::copy_from_slice(&buf[0..len]);
                    self.tx_audio.send(chunk).await.unwrap();
                }

                // Poll for transport commands that interrupt playback
                if let Some(Some(cmd)) = unconstrained(self.rx_transport_cmd.recv()).now_or_never()
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
                        TransportCommand::NowPlaying(tx) => {
                            tx.send(self.now_playing().clone()).unwrap();
                        }
                    }
                }
            }
            self.cursor += 1;
        }
        tx_cmd.send(Command::Quit).unwrap();
    }

    /// Create a stream of audio data from the current playlist position.
    async fn get_audio_child_at_cursor(&mut self) -> Result<process::Child, anyhow::Error> {
        if self.cursor >= self.files.len() {
            return Err(anyhow::Error::msg(format!(
                "cursor index ({}) out of bounds ({}), just quit",
                self.cursor,
                self.files.len()
            )));
        }
        let file_url = &self.now_playing().location;
        Ok(audio_from_url(file_url).await.spawn()?)
    }
}
