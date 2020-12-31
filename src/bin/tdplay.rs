use crossterm::terminal;
use log::debug;
use smol::{
    channel::{Receiver, Sender},
    prelude::*,
    Unblock
};
use std::{self, panic, path::PathBuf, str};
use structopt::StructOpt;
use tapedeck::{cmd, logging};

fn main() {
    let args = Cli::from_args();
    logging::init_logging();
    with_raw_mode(|| {
        let (msg_out, msg_in) = smol::channel::unbounded();
        smol::spawn(quit(msg_out)).detach();
        smol::block_on(play(args.fname, msg_in)).expect("block on play");
    });
}

/// Capture command line arguments.
#[derive(StructOpt)]
struct Cli {
    #[structopt(parse(from_os_str))]
    fname: PathBuf,
}

/// Create a scope with the terminal in raw mode.  Attempt to catch
/// panics so we can disable raw mode before exiting.
fn with_raw_mode(f: impl FnOnce() + panic::UnwindSafe) {
    let saved_hook = panic::take_hook();
    panic::set_hook(Box::new(|_| {
        // Do nothing: overrides console error message from panic!()
    }));

    terminal::enable_raw_mode().expect("raw mode enabled");
    let result = panic::catch_unwind(|| {
        f();
    });
    terminal::disable_raw_mode().expect("raw mode disabled");

    panic::set_hook(saved_hook);
    if let Err(err) = result {
        panic::resume_unwind(err);
    }
}

/// Play an audio stream.
async fn play(fname: PathBuf, msg_in: Receiver<&str>) -> Result<(), std::io::Error> {
    let fname = fname.to_str().unwrap();
    let mut command = cmd::ffmpeg::read(fname).await;

    let mut source = command.spawn()?;
    let mut reader = source.stdout.take().unwrap();

    let mut sink = cmd::sox::play().spawn()?;
    let mut writer = sink.stdin.take().unwrap();

    let (snd, rcv) = smol::channel::unbounded(); // bounded(100);

    let _playlist = smol::spawn(async move {
        let mut buf = [0; 1024];
        loop {
            match reader.read(&mut buf) .await {
                Ok(_n) => {
                    // TODO check num bytes read and send count with buf
                    //print!("{}", n)
                },
                Err(err) => debug!("WWTF!!!OH NO!!!!!!AAAAAARGGGGGGGG!!!!!!")
            }
            match snd.send(buf).await {
                Ok(_) => {},
                Err(err) => {
                    debug!("!!!{}!!!", err.to_string());
                    break;
                }
            }
        }
    }).detach();

    let _player = smol::spawn(async move {
        loop {
            let buf: [u8; 1024] = rcv.recv().await.unwrap();
            match writer.write(&buf).await {
                Ok(_n) => {
                    // TODO compare num bytes written to bytes from buf
                    /*print!("{:?}", buf)*/
                },
                Err(err) => {
                    debug!("!!!{}!!!", err.to_string());
                    break;
                }
            }
        }
    }).detach();

    // Wait for QUIT signal
    msg_in.recv().await.unwrap();

    /*
    // kill() is SIGKILL - leaves orphaned mplayer process..
    unsafe {
        libc::kill(source.id() as i32, libc::SIGTERM);
        libc::kill(sink.id() as i32, libc::SIGTERM);
    };
    */
    source.kill().unwrap();
    sink.kill().unwrap();

    // Wait for processes to end
    source.status().await.unwrap();
    sink.status().await.unwrap();

    Ok(())
}

/// Process a quit signal from the keyboard.
async fn quit(quit_signal: Sender<&str>) {
    let mut stdin = Unblock::new(std::io::stdin());
    let mut buf = [0; 1];

    loop {
        stdin.read(&mut buf).await.expect("can't read stdin");
        match buf[0] {
            3 | 113 => {
                // `^C` or `q`
                debug!("Got QUIT signal");
                quit_signal.try_send("42").ok();
                break;
            }
            _ => {
                debug!("keyboard input >{}<", buf[0]);
                continue;
            }
        }
    }
}
