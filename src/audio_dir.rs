use std::ffi::OsString;
use std::fmt;
use std::os::unix::ffi::{OsStrExt, OsStringExt}; // TODO system predicate
use std::path::PathBuf;

use crossterm::style::Colorize;
use mime_guess::{self, Mime};
use sqlx::sqlite::SqlitePool;
use tokio_stream::StreamExt;

/// A directory containing audio files.
#[derive(Clone, Debug, Default)]
pub struct AudioDir {
    pub id: Option<i64>,
    pub last_modified: i64,
    pub location: OsString,
    files: Vec<AudioFile>,
}

/// An audio file.
#[derive(Clone, Debug, Default)]
pub struct AudioFile {
    pub id: Option<i64>,
    pub file_size: Option<i64>,
    pub mime_type: Option<Mime>,
    pub location: OsString,
}

impl Extend<AudioFile> for AudioDir {
    fn extend<T: IntoIterator<Item = AudioFile>>(&mut self, iter: T) {
        for f in iter {
            self.files.push(f);
        }
    }
}

impl From<PathBuf> for AudioFile {
    fn from(p: PathBuf) -> Self {
        Self {
            location: p.as_os_str().to_owned(),
            ..AudioFile::default()
        }
    }
}

impl From<PathBuf> for AudioDir {
    fn from(p: PathBuf) -> Self {
        Self {
            location: p.as_os_str().to_owned(),
            ..AudioDir::default()
        }
    }
}

impl AudioDir {
    pub fn files(&self) -> &Vec<AudioFile> {
        &self.files
    }

    /// Find a list of directories by matching path with a pattern.
    pub async fn get_with_path(pool: &SqlitePool, pattern: &str) -> Vec<AudioDir> {
        let mut dirs = sqlx::query!(
            r#"
            select id, location, last_modified
            from audio_dir
            where location like ?
            "#,
            pattern
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(Some(row)) = dirs.try_next().await {
            result.push(AudioDir {
                id: Some(row.id),
                location: OsString::from_vec(row.location),
                ..AudioDir::default()
            });
        }

        result
    }

    /// Return a list of all audio directories.
    pub async fn get_audio_dirs(pool: &SqlitePool) -> Vec<AudioDir> {
        let mut rows = sqlx::query!(
            r#"
            select id, location, last_modified
            from audio_dir
            "#,
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(Some(row)) = rows.try_next().await {
            result.push(AudioDir {
                id: Some(row.id),
                last_modified: row.last_modified.unwrap(), // TODO!
                location: OsString::from_vec(row.location),
                ..AudioDir::default()
            });
        }

        result
    }

    /// Return a list of all audio files in a particular audio directory.
    pub async fn get_audio_files(pool: &SqlitePool, id: i64) -> Vec<AudioFile> {
        let mut files = sqlx::query!(
            r#"
            select id, location, file_size
            from audio_file
            where audio_dir_id = ?
            "#,
            id
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(file) = files.try_next().await {
            match file {
                Some(row) => result.push(AudioFile {
                    id: Some(row.id),
                    location: OsString::from_vec(row.location),
                    file_size: row.file_size,
                    ..AudioFile::default()
                }),
                None => break,
            }
        }

        result
    }

    /// Save all records to database.
    pub async fn db_insert(&mut self, pool: &SqlitePool) -> Result<(), sqlx::Error> {
        let transaction = pool.begin().await?;
        // Create AudioDir record for self
        let location = self.location.as_bytes();
        let insert_id = sqlx::query!(
            r#"
            insert into audio_dir(location, last_modified)
            values(?1, ?2)
            "#,
            location,
            self.last_modified,
        )
        .execute(pool)
        .await?
        .last_insert_rowid();
        self.id = Some(insert_id);

        for audio_file in &mut self.files[..] {
            let mime_type = audio_file
                .mime_type
                .as_ref()
                .map(|m| m.essence_str().to_string());
            let location = audio_file.location.as_bytes();

            let audio_file_id = sqlx::query!(
                r#"
                insert into audio_file(location, mime_type, file_size, audio_dir_id)
                values(?1, ?2, ?3, ?4);
                "#,
                location,
                mime_type,
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

impl fmt::Display for AudioFile {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}:{}",
            match &self.mime_type {
                Some(m) => m.to_string().green(),
                None => "-/-".to_string().green(),
            },
            self.location.to_string_lossy().magenta()
        )
    }
}

impl fmt::Display for AudioDir {
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
        assert_eq!(AudioDir::default().id, None);
        assert_eq!(AudioFile::default().id, None);
    }
}
