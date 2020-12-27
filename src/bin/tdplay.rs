use crossterm::terminal;
use log::trace;
use smol::{
    self, prelude::*,
    channel::{Receiver, Sender},
    process::{Command, Stdio},
};
use std::panic;
use structopt::StructOpt;
use tracing::{info, /*trace,*/ Level};
use tracing_subscriber::FmtSubscriber;

type Result = std::result::Result<(), String>;

#[derive(StructOpt)]
struct Cli {
    #[structopt(parse(from_os_str))]
    fname: std::path::PathBuf,
}

fn with_raw_mode(f: impl FnOnce() + panic::UnwindSafe) -> Result {
    panic::set_hook(Box::new(|_| {
        // Do nothing, overriding console error message from panic
    }));

    terminal::enable_raw_mode().expect("barf enable raw mode");
    let result = panic::catch_unwind(|| {
        f();
    });
    terminal::disable_raw_mode().expect("barf disable raw mode");

    match result {
        Ok(_) => Ok(()),
        Err(err) => panic::resume_unwind(err),
    }
}

fn init_logging() {
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::TRACE)
        .finish();

    tracing::subscriber::set_global_default(subscriber)
        .expect("problem setting global logger");

    info!("Logging initialized...");
    trace!("[trace] Logging initialized...");
}

fn main() -> Result {
    init_logging();

    let args = Cli::from_args();
    let (msg_out, msg_in) = smol::channel::unbounded();

    with_raw_mode(|| {
        smol::spawn(quit(msg_out)).detach();
        smol::block_on(play(args.fname, msg_in)).expect("block_on failed");
    })
}

async fn play(fname: std::path::PathBuf, msg_in: Receiver<&str>) -> Result {
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

    unsafe {
        libc::kill(cmd.id() as i32, libc::SIGTERM);
    };
    //cmd.kill().expect("can't kill process");

    if let Err(msg) = cmd.status().await {
        Err(msg.to_string())
    } else {
        Ok(())
    }
}

async fn quit(msg_out: Sender<&str>) -> Result {
    trace!("ENTER quitter");
    let mut stdin = smol::Unblock::new(std::io::stdin());
    let mut buf = [0; 1];

    loop {
        trace!("..quitter: waiting for input");
        let c = stdin.read(&mut buf).await
            .expect("can't read stdin");
        trace!("..quitter: GOT input! {}", c);
        assert!(c == 1);
        match buf[0] {
            113 => {
                trace!("Got QUIT signal");
                //to_quit.send(42);
                msg_out.try_send("42").ok();
                break;
            },
            _ => continue,
        }
    }

    Ok(())
}
