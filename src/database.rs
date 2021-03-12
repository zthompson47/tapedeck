use std::{env, path::PathBuf};

use sqlx::{
    migrate::Migrator,
    sqlite::{SqliteConnectOptions, SqlitePool},
    ConnectOptions, Error, Pool, Sqlite, SqliteConnection,
};

pub static MIGRATOR: Migrator = sqlx::migrate!();

pub async fn get_db_connection(name: &str) -> Result<SqliteConnection, Error> {
    SqliteConnectOptions::new()
        .filename(get_db_url(name).unwrap())
        .connect()
        .await
}

pub async fn get_db_pool(name: &str) -> Result<Pool<Sqlite>, Error> {
    SqlitePool::connect(&get_db_url(name).unwrap()).await
}

pub fn get_db_url(name: &str) -> Result<String, ()> {
    match env::var("DATABASE_URL") {
        Ok(url) => Ok(url),
        Err(_) => match env::var("HOME") {
            Ok(dir) => {
                let mut path = PathBuf::from(dir)
                    .join(".local")
                    .join("share")
                    .join(name)
                    .join(name);
                path.set_extension("db");
                Ok(path.to_str().unwrap().to_string())
            }
            Err(_) => Ok("tmp".to_string()),
        },
    }
}
