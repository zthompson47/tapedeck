use isahc::prelude::*;
#[allow(unused_imports)]
use log::debug;
use smol::process::{Command, Stdio};

pub async fn read(uri: &str) -> Command {
    let stream_url = stream_from_playlist(uri).await.unwrap();
    let mut cmd = Command::new("ffmpeg");

    cmd.args(&["-ac", "2"])
        .args(&["-i", stream_url.as_str()])
        .args(&["-f", "s16le"])
        .args(&["-ar", "44.1k"])
        .args(&["-acodec", "pcm_s16le"])
        .arg("-")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    cmd
}

pub async fn stream_from_playlist(uri: &str)
    -> Result<String, String>
{
    use crate::pls;

    // Fetch remote playlist file
    let mut response = isahc::get_async(uri)
        .await
        .map_err(|e|{ e.to_string() })?;
    let text = response.text_async().await.unwrap();

    // Parse out primary stream url
    let playlist = pls::parse(text.as_str()).unwrap();
    let files = playlist.files();
    Ok(files[0].clone())
}

#[allow(dead_code)]
pub fn to_icecast(host: &str, port: i32, mount: &str, pw: &str)
    -> Command
{
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
        .arg(format!("icecast://source:{}@{}:{}/{}", pw, host, port, mount));
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
