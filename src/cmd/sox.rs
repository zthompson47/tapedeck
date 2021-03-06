use std::process::Stdio;

use tokio::process::Command;

pub fn play() -> Command {
    let mut cmd = Command::new("play");
    cmd.args(&["-t", "raw"])
        .args(&["-r", "44.1k"])
        .args(&["-e", "signed-integer"])
        .args(&["-b", "16"])
        .args(&["--endian", "little"])
        .args(&["-c", "2"])
        .arg("-")
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    cmd
}
