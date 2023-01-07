use std::ffi::OsString;
use std::fmt;
use std::os::unix::ffi::{OsStrExt, OsStringExt}; // TODO system predicate
use std::path::PathBuf;

use crossterm::style::Stylize;
use mime_guess::{self, Mime};
use rusqlite::{named_params, params};

use crate::database::Store;

/// A directory containing media files.
#[derive(Clone, Debug, Default)]
pub struct MediaDir {
    pub id: Option<i64>,
    pub last_modified: u64,
    pub location: OsString,
    files: Vec<MediaFile>,
}

/// A media file.
#[derive(Clone, Debug, Default)]
pub struct MediaFile {
    pub id: Option<i64>,
    pub file_size: Option<i64>,
    pub media_type: MediaType,
    pub location: OsString,
    pub directory: MaybeFetched<MediaDir>,
}

#[derive(Clone, Debug)]
pub enum MaybeFetched<T> {
    Id(i64),
    Record(T),
    None,
}

impl<T> Default for MaybeFetched<T> {
    fn default() -> Self {
        Self::None
    }
}

#[derive(Clone, Debug)]
pub enum MediaType {
    Audio(Mime),
    Checksum(OsString),
    Unknown,
}

impl Default for MediaType {
    fn default() -> Self {
        MediaType::Unknown
    }
}

impl fmt::Display for MediaType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}",
            match self {
                Self::Audio(m) => m.essence_str().to_string(),
                Self::Checksum(m) => format!("checksum/{}", m.to_str().unwrap_or("-")),
                Self::Unknown => "-/-".to_string(),
            }
        )
    }
}

impl Extend<MediaFile> for MediaDir {
    fn extend<T: IntoIterator<Item = MediaFile>>(&mut self, iter: T) {
        for f in iter {
            self.files.push(f);
        }
    }
}

impl From<PathBuf> for MediaFile {
    fn from(p: PathBuf) -> Self {
        Self {
            location: p.as_os_str().to_owned(),
            ..MediaFile::default()
        }
    }
}

impl From<PathBuf> for MediaDir {
    fn from(p: PathBuf) -> Self {
        Self {
            location: p.as_os_str().to_owned(),
            ..MediaDir::default()
        }
    }
}

impl MediaFile {
    pub fn directory(&self, store: &Store) -> Option<MediaDir> {
        tokio::task::block_in_place(|| match &self.directory {
            MaybeFetched::Id(id) => {
                let mut stmt = store
                    .conn
                    .prepare(
                        r#"
                    select id, location, last_modified
                    from media_dir
                    where id = ?
                    "#,
                    )
                    .unwrap();
                let mut rows = stmt.query(params![id]).unwrap();

                rows.next().unwrap().map(|directory| MediaDir {
                    id: Some(directory.get(0).unwrap()),
                    last_modified: directory.get(2).unwrap(),
                    location: OsString::from_vec(directory.get(1).unwrap()),
                    files: Vec::new(),
                })
            }
            MaybeFetched::Record(r) => Some(r.to_owned()),
            MaybeFetched::None => None,
        })
    }
}

impl MediaDir {
    pub fn files(&self) -> &Vec<MediaFile> {
        &self.files
    }

    /// Find a list of directories by matching path with a pattern.
    pub fn get_with_path(store: &Store, pattern: &str) -> Vec<MediaDir> {
        tokio::task::block_in_place(|| {
            let mut stmt = store
                .conn
                .prepare(
                    r#"
            select id, location, last_modified
            from media_dir
            where location like ?
            "#,
                )
                .unwrap();
            let rows = stmt
                .query_map([pattern], |row| {
                    Ok(MediaDir {
                        id: Some(row.get(0)?),
                        last_modified: row.get(2).unwrap(), // TODO!
                        location: OsString::from_vec(row.get(1)?),
                        ..MediaDir::default()
                    })
                })
                .unwrap();

            rows.map(|x| x.unwrap()).collect()
        })
    }

    pub fn get_audio_dirs(store: &Store) -> Result<Vec<MediaDir>, anyhow::Error> {
        tokio::task::block_in_place(|| {
            let mut stmt = store.conn.prepare(
                r#"
            select id, location, last_modified
            from media_dir
            "#,
            )?;
            let rows = stmt.query_map([], |row| {
                Ok(MediaDir {
                    id: Some(row.get(0)?),
                    last_modified: row.get(2).unwrap(), // TODO!
                    location: OsString::from_vec(row.get(1)?),
                    ..MediaDir::default()
                })
            })?;

            Ok(rows.map(|x| x.unwrap()).collect())
        })
    }

    /// Return a list of all audio files in a particular audio directory.
    pub fn get_audio_files(store: &Store, id: i64) -> Result<Vec<MediaFile>, anyhow::Error> {
        tokio::task::block_in_place(|| {
            let mut stmt = store.conn.prepare(
                r#"
            select id, location, file_size
            from media_file
            where media_dir_id = ?
            "#,
            )?;
            let rows = stmt.query_map([id], |row| {
                Ok(MediaFile {
                    id: Some(row.get(0)?),
                    location: OsString::from_vec(row.get(1)?),
                    file_size: row.get(2)?,
                    directory: MaybeFetched::Id(id),
                    ..MediaFile::default()
                })
            })?;

            Ok(rows.map(|x| x.unwrap()).collect())
        })
    }

    pub fn text_files(&self, store: &Store) -> Option<Vec<MediaFile>> {
        self.id.map(|id| Self::get_text_files(store, id))
    }

    pub fn get_text_files(store: &Store, id: i64) -> Vec<MediaFile> {
        tokio::task::block_in_place(|| {
            let mut stmt = store
                .conn
                .prepare(
                    r#"
            select id, location, file_size
            from media_file
            where media_dir_id = ?
            and media_type like 'text/%'
            "#,
                )
                .unwrap();

            let rows = stmt
                .query_map([id], |row| {
                    Ok(MediaFile {
                        id: Some(row.get(0).unwrap()),
                        location: OsString::from_vec(row.get(1).unwrap()),
                        file_size: row.get(2).unwrap(),
                        ..MediaFile::default()
                    })
                })
                .unwrap();

            rows.map(|x| x.unwrap()).collect()
        })
    }

    /// Save all records to database.
    pub fn db_insert(&mut self, store: &Store) -> Result<(), anyhow::Error> {
        tokio::task::block_in_place(|| {
            let mut stmt = store
                .conn
                .prepare(
                    "\
            insert into media_dir(location, last_modified)
            values(:location, :last_modified)",
                )
                .unwrap();
            let location = self.location.as_bytes();

            self.id = Some(stmt.insert(named_params! {
                ":location": location,
                ":last_modified": self.last_modified,
            })?);

            // Create MediaFile records
            for audio_file in &mut self.files[..] {
                let location = audio_file.location.as_bytes();
                let media_type = audio_file.media_type.to_string();

                let mut stmt = store
                    .conn
                    .prepare(
                        "\
                insert into media_file(location, media_type, file_size, media_dir_id)
                values(:location, :media_type, :file_size, :media_dir_id);
            ",
                    )
                    .unwrap();

                audio_file.id = Some(stmt.insert(named_params! {
                    ":location": location,
                    ":media_type": media_type,
                    ":file_size": audio_file.file_size,
                    ":media_dir_id": self.id,
                })?);
            }

            Ok(())
        })
    }
}

impl fmt::Display for MediaFile {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}:{}",
            self.media_type.to_string().green(),
            self.location.to_string_lossy().magenta()
        )
    }
}

impl fmt::Display for MediaDir {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // Id and path
        writeln!(
            f,
            "{}. {}",
            self.id.unwrap_or(-1).to_string().magenta(),
            self.location.to_string_lossy().blue()
        )?;

        // Limited list of `audio_file`s
        let mut i = 0;
        for file in self.files.iter() {
            if i > 5 {
                writeln!(f, " {}{}", file, "...".to_string().green())?;
                break;
            } else {
                writeln!(f, " {file}")?;
                i += 1
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults() {
        assert_eq!(MediaDir::default().id, None);
        assert_eq!(MediaFile::default().id, None);
    }
}
