use std::{self, path::PathBuf, str};

use structopt::StructOpt;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
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
    let _guard = init_logging("tapedeck");
    let args = Cli::from_args();
    term::with_raw_mode(|| {
        let (tx_quit, rx_quit) = mpsc::unbounded_channel();
        let rt = Runtime::new().unwrap();
        rt.spawn(quit(tx_quit));
        rt.block_on(play(args.fname, rx_quit)).unwrap();
    });
}

/// Play an audio stream.
async fn play(
    fname: PathBuf,
    mut rx_quit: mpsc::UnboundedReceiver<&str>,
) -> Result<(), std::io::Error> {
    let fname = fname.to_str().unwrap();

    let mut source = cmd::ffmpeg::read(fname).await.spawn()?;
    let mut reader = source.stdout.take().unwrap();
    let mut sink = cmd::sox::play().spawn()?;
    let mut writer = sink.stdin.take().unwrap();

    let (snd, mut rcv) = mpsc::channel(1);

    let playlist = tokio::spawn(async move {
        let mut buf: [u8; 1024] = [0; 1024];
        loop {
            reader.read(&mut buf).await.unwrap();
            match snd.send(buf).await {
                Ok(()) => {}
                Err(err) => {
                    debug!("!!!{}!!!", err.to_string());
                    break;
                }
            }
        }
    });

    let player = tokio::spawn(async move {
        loop {
            let buf: [u8; 1024] = rcv.recv().await.unwrap();
            match writer.write(&buf).await {
                Ok(_n) => {
                    // TODO compare num bytes written to bytes from buf
                    /*print!("{:?}", buf)*/
                }
                Err(err) => {
                    debug!("!!!{}!!!", err.to_string());
                    break;
                }
            }
        }
    });

    // Receive quit signal
    rx_quit.recv().await.unwrap();
    source.kill().await.unwrap();
    sink.kill().await.unwrap();

    // Wait for processes
    source.wait().await.unwrap();
    sink.wait().await.unwrap();

    // Wait for tasks
    playlist.await.unwrap();
    player.await.unwrap();

    Ok(())
}

/// Process a quit signal from the keyboard.
async fn quit(quit_out: mpsc::UnboundedSender<&str>) {
    let mut stdin = tokio::io::stdin();
    let mut buf: [u8; 1] = [0; 1];

    loop {
        stdin.read(&mut buf).await.expect("can't read stdin");
        match buf[0] {
            3 | 113 => {
                // `^C` or `q`
                debug!("Got QUIT signal");
                quit_out.send("42").ok();
                break;
            }
            _ => {
                debug!("keyboard input >{}<", buf[0]);
                continue;
            }
        }
    }
}
