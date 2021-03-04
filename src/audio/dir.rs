use std::ffi::OsString;
use std::fmt;
use std::path::PathBuf;
use std::collections::HashMap;

use crossterm::style::Colorize;
use mime_guess::{self, Mime};
use sqlx::sqlite::SqlitePool;

#[derive(Debug, Default)]
pub struct AudioDir {
    pub id: Option<i64>,
    pub path: PathBuf,
    pub files: Vec<AudioFile>,
    pub extra: HashMap<OsString, Vec<PathBuf>>,
}

impl AudioDir {
    pub async fn db_insert(&mut self, pool: &SqlitePool) -> Result<(), sqlx::Error> {
        let transaction = pool.begin().await?;

        let dir_path = self.path.to_str();
        let insert_id = sqlx::query!(
            r#"
            INSERT INTO audio_dir(path)
            VALUES(?1)
        "#,
            dir_path
        )
        .execute(pool)
        .await?
        .last_insert_rowid();
        self.id = Some(insert_id);

        for audio_file in &self.files[..] {
            let path = audio_file.path.to_str();
            let mime_type = audio_file.mime_type.essence_str();
            let audio_file_id = sqlx::query!(
                r#"
                INSERT INTO audio_file(path, mime_type)
                VALUES(?1, ?2);
            "#,
                path,
                mime_type,
            )
            .execute(pool)
            .await?
            .last_insert_rowid();

            sqlx::query!(
                r#"
                INSERT INTO audio_dir_audio_file(audio_dir_id, audio_file_id)
                VALUES ($1, $2);
            "#,
                self.id,
                audio_file_id,
            )
            .execute(pool)
            .await?;
        }

        for (extension, files) in &self.extra {
            for extra_file in files {
                let path = extra_file.to_str();
                let extension = extension.to_str();
                let extra_file_id = sqlx::query!(
                    r#"
                    INSERT INTO extra_file(path, mime_type)
                    VALUES(?1, ?2);
                "#,
                    path,
                    extension,
                )
                .execute(pool)
                .await?
                .last_insert_rowid();

                sqlx::query!(
                    r#"
                    INSERT INTO audio_dir_extra_file(audio_dir_id, extra_file_id)
                    VALUES ($1, $2);
                "#,
                    self.id,
                    extra_file_id,
                )
                .execute(pool)
                .await?;
            }
        }

        transaction.commit().await
    }
}

#[derive(Clone, Debug)]
pub struct AudioFile {
    pub id: Option<i64>,
    pub path: PathBuf,
    pub mime_type: Mime,
}

impl fmt::Display for AudioFile {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}:{}",
            self.mime_type.to_string().green(),
            self.path.file_name().unwrap().to_str().unwrap()
        )
    }
}

#[derive(Debug)]
pub struct ExtraFile {
    pub id: Option<i64>,
    pub path: PathBuf,
    pub mime_type: Mime,
}
