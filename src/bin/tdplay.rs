use std::{self, /*panic,*/ path::PathBuf, str};

//use crossterm::terminal;
use log::debug;
use smol::{
    channel::{Receiver, Sender},
    prelude::*,
    Unblock,
};
use structopt::StructOpt;

use allotropic::init_logging;
use tapedeck::{cmd, term};

#[derive(StructOpt)]
struct Cli {
    #[structopt(parse(from_os_str))]
    fname: PathBuf,
}

fn main() {
    let _guard = init_logging("td");
    let args = Cli::from_args();
    term::with_raw_mode(|| {
        let (quit_out, quit_in) = smol::channel::unbounded();
        smol::spawn(quit(quit_out)).detach();
        smol::block_on(play(args.fname, quit_in)).unwrap();
    });
}

/// Play an audio stream.
async fn play(fname: PathBuf, quit_in: Receiver<&str>) -> Result<(), std::io::Error> {
    let fname = fname.to_str().unwrap();

    let mut source = cmd::ffmpeg::read(fname).await.spawn()?;
    let mut reader = source.stdout.take().unwrap();
    let mut sink = cmd::sox::play().spawn()?;
    let mut writer = sink.stdin.take().unwrap();

    let (snd, rcv) = smol::channel::bounded(1);

    let playlist = smol::spawn(async move {
        let mut buf = [0; 1024];
        loop {
            match reader.read(&mut buf).await {
                Ok(_n) => {
                    // TODO check num bytes read
                    // and send count with buf
                    //print!("{}", n)
                }
                Err(err) => debug!("!!!{}!!!", err.to_string()),
            }
            match snd.send(buf).await {
                Ok(()) => {}
                Err(err) => {
                    debug!("!!!{}!!!", err.to_string());
                    break;
                }
            }
        }
    });

    let player = smol::spawn(async move {
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
    quit_in.recv().await.unwrap();
    source.kill().unwrap();
    sink.kill().unwrap();

    // Wait for processes
    source.status().await.unwrap();
    sink.status().await.unwrap();

    // Wait for tasks
    playlist.await;
    player.await;

    Ok(())
}

/// Process a quit signal from the keyboard.
async fn quit(quit_out: Sender<&str>) {
    let mut stdin = Unblock::new(std::io::stdin());
    let mut buf = [0; 1];

    loop {
        stdin.read(&mut buf).await.expect("can't read stdin");
        match buf[0] {
            3 | 113 => {
                // `^C` or `q`
                debug!("Got QUIT signal");
                quit_out.try_send("42").ok();
                break;
            }
            _ => {
                debug!("keyboard input >{}<", buf[0]);
                continue;
            }
        }
    }
}
