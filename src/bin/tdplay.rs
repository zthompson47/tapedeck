use crossterm::terminal;
use log::trace;
use smol::{
    self, prelude::*,
    channel::{Receiver, Sender},
    process::{Command, Stdio},
};
use std::{panic, str};
use structopt::StructOpt;

use tracing::{debug, info, Level};
use tracing_log::LogTracer;
use tracing_subscriber::FmtSubscriber;

fn main() {
    println!("000EEEEEEEEEEEEENTER");
    let result = ctrlc::set_handler(move || {
        println!("ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZzz");
    });
    match result {
        Ok(ok) => println!("AAAA{:?}AAAA", ok),
        Err(err) => println!("CCCC{:?}cccc", err),
    };
    println!("111EEEEEEEEEEEEENTER");

    let args = Cli::from_args();
    init_logging();
    debug!("------------>>>>>>>>>>>>>>>>>>>>>>>>>");
    with_raw_mode(|| {
        let (msg_out, msg_in) = smol::channel::unbounded();
        smol::spawn(quit(msg_out)).detach();
        smol::block_on(play(args.fname, msg_in));
    });
    std::thread::sleep(std::time::Duration::from_millis(3000));
}

/// Capture command line arguments.
#[derive(StructOpt)]
struct Cli {
    #[structopt(parse(from_os_str))]
    fname: std::path::PathBuf,
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
    tracing::subscriber::set_global_default(subscriber)
        .expect("problem setting global logger");

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

    terminal::enable_raw_mode().expect("enabling raw mode");
    let result = panic::catch_unwind(|| {
        f();
    });
    terminal::disable_raw_mode().expect("disabling raw mode");

    panic::set_hook(saved_hook);
    if result.is_err() {
        panic::resume_unwind(result.unwrap_err());
    }
}

/// Play an audio stream.
async fn play(fname: std::path::PathBuf, msg_in: Receiver<&str>) {
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
        Ok(_) => trace!(
            "..player>>{}<<: GOT QUIT SIG -->{:?}<--",
            cmd.id(),
            result,
        ),
        Err(err) => trace!("------->>ERR:{:?}", err),
    }
    trace!("<><><><><><>AFTER<><><><><><><>");
    //trace!("..player: GOT QUIT SIG -->{}<--");

    //cmd.kill().expect("can't kill process");
    unsafe { // cmd.kill() is SIGKILL - leaves orphaned mplayer process
        libc::kill(cmd.id() as i32, libc::SIGTERM);
    };
    cmd.status().await.unwrap();
}

/// Wait for a quit signal from the keyboard.
async fn quit(msg_out: Sender<&str>) {
    let mut stdin = smol::Unblock::new(std::io::stdin());
    let mut buf = [0; 1];

    loop {
        trace!("..quitter: waiting for input");
        let c = stdin.read(&mut buf).await
            .expect("can't read stdin");
        trace!("..quitter: GOT input! {}", c);
        assert!(c == 1);
        match buf[0] {
            113 => { // `q`
                trace!("Got QUIT signal");
                //to_quit.send(42);
                msg_out.try_send("42").ok();
                break;
            },
            _ => continue,
        }
    }
}
