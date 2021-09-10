use std::{cmp::Ordering, collections::HashMap, convert::TryFrom, path::PathBuf};

use crossterm::style::Colorize;
use structopt::StructOpt;
use tokio::runtime::Runtime;
use walkdir::WalkDir;

use tapedeck::{
    audio_dir::{MaybeFetched, MediaDir, MediaFile, MediaType},
    database::Store,
    logging::dev_log,
};

#[derive(StructOpt)]
struct Cli {
    #[structopt(short, long)]
    list: bool,
    #[structopt(parse(from_os_str))]
    search_path: Option<PathBuf>,
}

fn main() -> Result<(), anyhow::Error> {
    let _log = dev_log();
    let args = Cli::from_args();
    let rt = Runtime::new()?;

    if args.list {
        rt.block_on(list_dirs())?;
    } else if let Some(path) = args.search_path {
        rt.block_on(import_dirs(path))?;
    }

    Ok(())
}

/// Get all audio_dir records from the database and print them to stdout.
async fn list_dirs() -> Result<(), anyhow::Error> {
    //let db = get_database("tapedeck").await?;
    let store = Store::new().unwrap();
    let audio_dirs = MediaDir::get_audio_dirs(&store).await.unwrap();

    for dir in audio_dirs.iter() {
        println!(
            "{}. {}",
            // All AudioDir from the database have `id`
            &dir.id.unwrap().to_string().magenta(),
            &dir.location.to_string_lossy(),
        );
    }

    Ok(())
}

/// Search search_path for audio directories and save to database.
async fn import_dirs(search_path: PathBuf) -> Result<(), anyhow::Error> {
    //let db = get_database("tapedeck").await?;
    let store = Store::new().unwrap();
    let mut mime_type_count: HashMap<String, usize> = HashMap::new();
    let mut new_files: Vec<MediaFile> = Vec::new();
    let mut found_audio = false;

    // Sort directories-first with file entries forming an alpahbetized
    // contiguous list followed by their parent directory.
    for entry in WalkDir::new(search_path)
        .contents_first(true)
        .sort_by(
            |a, b| match (a.file_type().is_dir(), b.file_type().is_dir()) {
                (true, false) => Ordering::Less,
                (false, true) => Ordering::Greater,
                (true, true) | (false, false) => a.file_name().cmp(b.file_name()),
            },
        )
        .into_iter()
        .flatten()
    {
        let path = entry.path();
        let guess = mime_guess::from_path(path);

        // Try to identify file by mime type
        if let Some(guess) = guess.first() {
            if guess.type_() == "audio" {
                found_audio = true;
            }

            if ["audio", "text"].contains(&guess.type_().as_str()) {
                // Count by mime type for summary output
                let counter = mime_type_count
                    .entry(guess.essence_str().to_string())
                    .or_insert(0);
                *counter += 1;

                // Create new AudioFile
                new_files.push(MediaFile {
                    id: None,
                    location: path.as_os_str().to_owned(),
                    media_type: MediaType::Audio(guess.clone()),
                    file_size: i64::try_from(entry.metadata()?.len()).ok(),
                    directory: MaybeFetched::None,
                });
            }
        }

        // Look for non-mime support files
        if path.is_file() {
            if let Some(ext) = path.extension() {
                if ["md5", "st5"].contains(&ext.to_str().unwrap_or("")) {
                    new_files.push(MediaFile {
                        id: None,
                        location: path.as_os_str().to_owned(),
                        media_type: MediaType::Checksum(ext.to_os_string()),
                        file_size: i64::try_from(entry.metadata()?.len()).ok(),
                        directory: MaybeFetched::None,
                    });
                }
            }
        }

        // Fold each completed directory into results
        if path.is_dir() {
            if found_audio {
                found_audio = false;
                // Create new MediaDir
                let mut audio_dir = MediaDir::from(path.to_owned());
                audio_dir.extend(std::mem::take(&mut new_files));
                audio_dir.last_modified = timestamp(entry.metadata()?.modified()?);

                // Insert into database
                match audio_dir.db_insert(&store).await {
                    Ok(_) => print!("{}", &audio_dir),
                    Err(_) => println!("dup"), // TODO
                }
            } else {
                new_files.clear();
            }
        }
    }
    println!("{:#?}", mime_type_count);

    Ok(())
}

use chrono::{DateTime, Utc};
use std::time::SystemTime;
fn timestamp(t: SystemTime) -> i64 {
    let utc: DateTime<Utc> = DateTime::from(t);
    utc.timestamp_millis()
}
