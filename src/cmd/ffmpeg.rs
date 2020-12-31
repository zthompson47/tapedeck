use log::debug;
//use pls;
//use smol::{net, prelude::*, process::{Command, Stdio}};
use smol::process::{Command, Stdio};
//use std::io::prelude::*;
//use url::{Url, ParseError};

use isahc::prelude::*;

#[allow(dead_code)]
pub async fn read(uri: &str) -> Command {
    debug!("hmmmmmmmmmmm!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!11");
    let stream_url = stream_from_playlist(uri).await.unwrap();
    /*
    match playlist {
        Ok(result) => debug!("RESULT: {:?}", result),
        Err(err) => debug!("ERR: {:?}", err)
    }
    */

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

pub async fn stream_from_playlist(uri: &str) -> Result<String, String> {
    use crate::pls;

    let mut response = isahc::get_async(uri).await.map_err(|e|{ e.to_string() })?;
    let text = response.text_async().await.unwrap();
    let playlist = pls::parse(text.as_str()).unwrap();
    //debug!("!!!!!!!!!!>>{:?}<<!!!!!!!!!!!", &playlist.files());
    //let mut stream = smol::stream::iter(&mut text.chars());
    //let list = pls::parse(&mut response.body()).unwrap();
    //let first = list.get(0).unwrap().path.to_string();
    //Ok(text)
    let files = playlist.files();
    Ok(files[0].clone())
}

/*
// https://jmarshall.com/easy/http/#sample
pub async fn _stream_from_playlist(uri: &str) -> Result<String, String> {
    debug!(">>>>>>>>>>>>>>>>>>>>>>111<<<<<<<<<<<<<<<<<<<<<<<<<<<<<");
    let url = Url::parse(uri).unwrap();
    debug!(">>>>>>>>>>>>>>>>>>>>>>222<<<<<<<<<<<<<<<<<<<<<<<<<<<<<");

    //let host_n_sock = format!("{}:{}", url.host_str().unwrap(), url.port().unwrap());
    //debug!(">>>>>>>>>>>>>>>>>>>>>>{}<<<<<<<<<<<<<<<<<<<<<<<<<<<<<", host_n_sock);
    let mut stream = net::TcpStream::connect("somafm.com:80").await.map_err(|e|{ e.to_string() })?;

    debug!(">>>>>>>>>>>>>>>>>>>>>>333<<<<<<<<<<<<<<<<<<<<<<<<<<<<<");

    let req_str = format!("GET {} HTTP/1.1\r\n\r\n", url.path());
    let req = req_str.as_bytes();

    stream.write_all(req).await.map_err(|e|{ e.to_string() })?;
    debug!(">>>>>>>>>>>>>>>>>>>>>>444<<<<<<<<<<<<<<<<<<<<<<<<<<<<<");
    let mut buf = [0; 4096];
    stream.read(&mut buf).await.map_err(|e|{ e.to_string() })?;
    debug!(">>>>>>>>>>>>>>>>>>>>>>555<<<<<<<<<<<<<<<<<<<<<<<<<<<<<");

    let z = std::str::from_utf8(&buf).unwrap();
    debug!(">>>>>>>>>>>>>>>>>>>>>>{}<<<<<<<<<<<<<<<<<<<<<<<<<<<<<", z);

    Ok(String::from(z))
}
*/

#[allow(dead_code)]
pub fn to_icecast(host: &str, port: i32, mount_point: &str, password: &str) -> Command {
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
        .arg(format!("icecast://source:{}@{}:{}/{}", password, host, port, mount_point));
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
