use std::env;
use std::path::PathBuf;

use sqlx::migrate::Migrator;

pub static MIGRATOR: Migrator = sqlx::migrate!();

pub fn get_database_url(name: &str) -> Result<String, ()> {
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
