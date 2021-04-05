use std::ffi::OsString;
use std::process::Stdio;

use tokio::process::Command;

use crate::playlist;

pub async fn audio_from_url(url: &OsString) -> Command {
    let url = match url {
        url if url.to_string_lossy().starts_with("http") => {
            let stream_url = stream_from_playlist(url).await.unwrap();
            OsString::from(stream_url)
        }
        _ => url.to_owned(),
    };

    let mut cmd = Command::new("ffmpeg");

    cmd.args(&["-ac", "2"])
        .args(&[OsString::from("-i"), url])
        .args(&["-f", "s16le"])
        .args(&["-ar", "44.1k"])
        .args(&["-acodec", "pcm_s16le"])
        .arg("-")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());

    cmd
}

pub async fn stream_from_playlist(url: &OsString) -> reqwest::Result<String> {
    let url: String = OsString::from(url).to_string_lossy().to_string();
    let text = reqwest::get(&url).await?.text().await?;

    // Parse out primary stream url
    let playlist = playlist::parse(text.as_str()).unwrap();
    let files = playlist.files();

    Ok(files[0].clone())
}

#[allow(dead_code)]
pub fn to_icecast(host: &str, port: i32, mount: &str, pw: &str) -> Command {
    let mut cmd = Command::new("ffmpeg");
    cmd.arg("-re")
        .args(&["-ac", "2"])
        .args(&["-ar", "44.1k"])
        .args(&["-f", "s16le"])
        .args(&["-i", "-"])
        .arg("-vn")
        .args(&["-codec:a", "libvorbis"])
        .args(&["-q:a", "8.0"])
        .args(&["-content_type", "audio/ogg"])
        .args(&["-f", "ogg"])
        .arg(format!(
            "icecast://source:{}@{}:{}/{}",
            pw, host, port, mount
        ));
    cmd
}

#[allow(dead_code)]
pub fn to_udp(host: &str, port: &str) -> Command {
    let mut cmd = Command::new("ffmpeg");
    cmd.arg("-re")
        .args(&["-ac", "2"])
        .args(&["-ar", "44.1k"])
        .args(&["-f", "s16le"])
        .args(&["-i", "-"])
        .arg("-vn")
        .args(&["-acodec", "mp3"])
        .args(&["-q:a", "0"])
        .args(&["-f", "mp3"])
        .arg(format!("udp://{}:{}", host, port));
    cmd
}

#[allow(dead_code)]
pub fn to_file(path: &str) -> Command {
    let mut cmd = Command::new("ffmpeg");
    cmd.args(&["-ac", "2"])
        .args(&["-ar", "44.1k"])
        .args(&["-f", "s16le"])
        .args(&["-i", "-"])
        .args(&["-f", "s16le"])
        .args(&["-ar", "44.1k"])
        .arg("y")
        .args(&["-c:a", "copy"])
        .arg(path);
    cmd
}
