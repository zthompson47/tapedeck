use std::ffi::OsString;
use std::fmt;
use std::os::unix::ffi::{OsStrExt, OsStringExt}; // TODO system predicate
use std::path::PathBuf;

use crossterm::style::Colorize;
use mime_guess::{self, Mime};
use sqlx::sqlite::SqlitePool;
use tokio_stream::StreamExt;

/// A directory containing media files.
#[derive(Clone, Debug, Default)]
pub struct MediaDir {
    pub id: Option<i64>,
    pub last_modified: i64,
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
                Self::Checksum(m) => format!("checksum/{}", m.to_str().unwrap_or("-").to_string()),
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
    pub async fn directory(&self, pool: &SqlitePool) -> Option<MediaDir> {
        match &self.directory {
            MaybeFetched::Id(id) => {
                let directory = sqlx::query!(
                    r#"
                    select id, location, last_modified
                    from media_dir
                    where id = ?
                    "#,
                    id
                )
                .fetch_one(pool)
                .await
                .unwrap();
                Some(MediaDir {
                    id: Some(directory.id),
                    last_modified: directory.last_modified.unwrap(),
                    location: OsString::from_vec(directory.location),
                    files: Vec::new(),
                })
            }
            MaybeFetched::Record(r) => Some(r.to_owned()),
            MaybeFetched::None => None,
        }
    }
}

impl MediaDir {
    pub fn files(&self) -> &Vec<MediaFile> {
        &self.files
    }

    /// Find a list of directories by matching path with a pattern.
    pub async fn get_with_path(pool: &SqlitePool, pattern: &str) -> Vec<MediaDir> {
        let mut dirs = sqlx::query!(
            r#"
            select id, location, last_modified
            from media_dir
            where location like ?
            "#,
            pattern
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(Some(row)) = dirs.try_next().await {
            result.push(MediaDir {
                id: Some(row.id),
                location: OsString::from_vec(row.location),
                ..MediaDir::default()
            });
        }

        result
    }

    /// Return a list of all audio directories.
    pub async fn get_audio_dirs(pool: &SqlitePool) -> Vec<MediaDir> {
        let mut rows = sqlx::query!(
            r#"
            select id, location, last_modified
            from media_dir
            "#,
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(Some(row)) = rows.try_next().await {
            result.push(MediaDir {
                id: Some(row.id),
                last_modified: row.last_modified.unwrap(), // TODO!
                location: OsString::from_vec(row.location),
                ..MediaDir::default()
            });
        }

        result
    }

    pub async fn _audio_files(&self, pool: &SqlitePool) -> Option<Vec<MediaFile>> {
        if let Some(id) = self.id {
            Some(Self::get_audio_files(pool, id).await)
        } else {
            None
        }
    }

    /// Return a list of all audio files in a particular audio directory.
    pub async fn get_audio_files(pool: &SqlitePool, id: i64) -> Vec<MediaFile> {
        let mut files = sqlx::query!(
            r#"
            select id, location, file_size
            from media_file
            where media_dir_id = ?
            "#,
            id
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(file) = files.try_next().await {
            match file {
                Some(row) => result.push(MediaFile {
                    id: Some(row.id),
                    location: OsString::from_vec(row.location),
                    file_size: row.file_size,
                    directory: MaybeFetched::Id(id),
                    ..MediaFile::default()
                }),
                None => break,
            }
        }

        result
    }

    pub async fn text_files(&self, pool: &SqlitePool) -> Option<Vec<MediaFile>> {
        if let Some(id) = self.id {
            Some(Self::get_text_files(pool, id).await)
        } else {
            None
        }
    }

    pub async fn get_text_files(pool: &SqlitePool, id: i64) -> Vec<MediaFile> {
        let mut files = sqlx::query!(
            r#"
            select id, location, file_size
            from media_file
            where media_dir_id = ?
            and media_type like 'text/%'
            "#,
            id
        )
        .fetch(pool);
        let mut result = Vec::new();

        while let Ok(file) = files.try_next().await {
            match file {
                Some(row) => result.push(MediaFile {
                    id: Some(row.id),
                    location: OsString::from_vec(row.location),
                    file_size: row.file_size,
                    ..MediaFile::default()
                }),
                None => break,
            }
        }

        result
    }

    /// Save all records to database.
    pub async fn db_insert(&mut self, pool: &SqlitePool) -> Result<(), sqlx::Error> {
        let transaction = pool.begin().await?;

        // Create MediaDir record
        let location = self.location.as_bytes();
        let insert_id = sqlx::query!(
            r#"
            insert into media_dir(location, last_modified)
            values(?1, ?2)
            "#,
            location,
            self.last_modified,
        )
        .execute(pool)
        .await?
        .last_insert_rowid();

        self.id = Some(insert_id);

        // Create MediaFile records
        for audio_file in &mut self.files[..] {
            let location = audio_file.location.as_bytes();
            let media_type = audio_file.media_type.to_string();

            let audio_file_id = sqlx::query!(
                r#"
                insert into media_file(location, media_type, file_size, media_dir_id)
                values(?1, ?2, ?3, ?4);
                "#,
                location,
                media_type,
                audio_file.file_size,
                self.id,
            )
            .execute(pool)
            .await?
            .last_insert_rowid();

            audio_file.id = Some(audio_file_id);
        }

        transaction.commit().await
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
                writeln!(f, " {}", file)?;
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
