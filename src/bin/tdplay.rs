use crossterm::terminal;
use log::trace;
use smol::{
    self,
    channel::{Receiver, Sender},
    prelude::*,
    process::{Command, Stdio},
};
use std::{self, panic, path::PathBuf, str};
use structopt::StructOpt;

use tracing::{debug, info, Level};
use tracing_log::LogTracer;
use tracing_subscriber::FmtSubscriber;

fn main() {
    let args = Cli::from_args();
    init_logging();
    with_raw_mode(|| {
        let (msg_out, msg_in) = smol::channel::unbounded();
        smol::spawn(quit(msg_out)).detach();
        smol::block_on(play(args.fname, msg_in));
    });
}

/// Capture command line arguments.
#[derive(StructOpt)]
struct Cli {
    #[structopt(parse(from_os_str))]
    fname: PathBuf,
}

/// Initialize logging system.
fn init_logging() {
    // Support log crate
    LogTracer::init().unwrap();

    // Send logs to stderr
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::TRACE)
        .with_writer(RawWriter::new)
        .finish();
    tracing::subscriber::set_global_default(subscriber).expect("problem setting global logger");

    info!("Logging initialized...");
    trace!("[trace] Logging initialized...");
}

#[derive(Debug, Default)]
struct RawWriter;

impl RawWriter {
    fn new() -> Self {
        RawWriter::default()
    }
}

impl std::io::Write for RawWriter {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        let buf = str::from_utf8(buf).unwrap();

        // `buf` is only terminated by '\n', so add '\r' (search c_oflag OPOST)
        #[allow(clippy::explicit_write)]
        write!(std::io::stderr(), "{}\r", buf).unwrap();

        Ok(buf.len())
    }

    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
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
async fn play(fname: PathBuf, msg_in: Receiver<&str>) {
    trace!("ENTER player");
    let mut cmd = Command::new("mplayer")
        .arg("-playlist")
        .arg(fname)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .expect("mplayer won't start");
    trace!("..player: started mplayer");

    //rcv_quit.next().await;
    let result = msg_in.recv().await;
    trace!("<><><><><><>BEFORE<><><><><><><>");
    match result {
        Ok(_) => trace!("..player>>{}<<: GOT QUIT SIG -->{:?}<--", cmd.id(), result,),
        Err(err) => trace!("------->>ERR:{:?}", err),
    }
    trace!("<><><><><><>AFTER<><><><><><><>");
    //trace!("..player: GOT QUIT SIG -->{}<--");

    //cmd.kill().expect("can't kill process");
    unsafe {
        // cmd.kill() is SIGKILL - leaves orphaned mplayer process
        libc::kill(cmd.id() as i32, libc::SIGTERM);
    };
    cmd.status().await.unwrap();
}

/// Wait for a quit signal from the keyboard.
async fn quit(msg_out: Sender<&str>) {
    let mut stdin = smol::Unblock::new(std::io::stdin());
    let mut buf = [0; 1];

    loop {
        stdin.read(&mut buf).await.expect("can't read stdin");
        match buf[0] {
            3 | 113 => {
                // `^C` or `q`
                debug!("Got QUIT signal");
                msg_out.try_send("42").ok();
                break;
            }
            _ => {
                debug!("keyboard input >{}<", buf[0]);
                continue;
            }
        }
    }
}
