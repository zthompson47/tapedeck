use std::process::{Command, Stdio};
use structopt::StructOpt;

#[derive(StructOpt)]
struct Cli {
    #[structopt(parse(from_os_str))]
    fname: std::path::PathBuf,
}

fn main() {
    let args = Cli::from_args();
    let fname = args.fname.to_str().unwrap();

    println!("Playing {}", fname);

    let mut cmd = Command::new("mplayer")
        .arg("-playlist")
        .arg(fname)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .expect("mplayer won't start");

    cmd.wait().expect("command wasn't running");
}
