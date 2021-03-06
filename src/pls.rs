// Rust's world is harsh.
// The environment is not kind.
// Bears and wolves will chase and kill you.
// Falling from a height will kill you.
// Being exposed to radiation for an extended period will kill you.
// Starving will kill you.
// Being cold will kill you.
// Other players can find you, kill you, and take your stuff.
// Fortunately for you, you can kill others and take their stuff.
use nom::{
    bytes::complete::tag,
    character::complete::{
        alpha1,
        alphanumeric1,
        digit1,
        line_ending,
        not_line_ending,
    },
    multi::fold_many1,
    sequence::{
        pair,
        separated_pair,
        terminated,
    },
    IResult,
};
use std::collections::HashMap;

#[derive(Clone, Debug, Default)]
pub struct Playlist {
    has_header: bool,
    number_of_entries: u32,
    version: String,
    entries: HashMap<u32, Entry>,
}

impl Playlist {
    pub fn files(&self) -> Vec<String> {
        let mut result = Vec::new();
        for i in (1..=self.number_of_entries).rev() {
            let entry = self.entries.get(&i).unwrap();
            result.push(entry.file.to_string());
        }
        result
    }
}

#[derive(Clone, Debug, Default)]
struct Entry {
    file: String,
    title: String,
    length: i32,
}

pub fn parse(input: &str) -> std::result::Result<Playlist, String> {
    let mut playlist = Playlist::default();

    // Confirm .pls filetype
    let (input, _) = header(input).map_err(|e| e.to_string())?;
    playlist.has_header = true;

    // Accumulate lines
    match fold_many1(line, playlist, fold_line)(input) {
        Ok(result) => Ok(result.1),
        Err(err) => Err(err.to_string())
    }
}

fn header(input: &str) -> IResult<&str, &str> {
    tag("[playlist]\n")(input)
}

fn line(input: &str) -> IResult<&str, &str> {
    terminated(not_line_ending, line_ending)(input)
}

// --------------- HACK -----------------------------------------
fn not_line_ending_(input: &str) -> IResult<&str, &str> {
    // Needed to put this in separate function to avoid
    // some weird error with the type system.
    not_line_ending(input)
}
fn alpha1_(input: &str) -> IResult<&str, &str> {
    alpha1(input)
}
fn digit1_(input: &str) -> IResult<&str, &str> {
    digit1(input)
}
// --------------- /HACK ----------------------------------------

fn fold_line(mut playlist: Playlist, input: &str) -> Playlist {
    let split_line = separated_pair(
        alphanumeric1, tag("="), not_line_ending_
    )(input);

    match split_line {
        Ok((input, (left, right))) => {
            assert!(input == "");
            let result = pair(alpha1_, digit1_)(left);
            if result.is_ok() {
                // Part of an entry
                let (_, (field, entry_num)) = result.unwrap();
                let entry_num = entry_num.parse::<u32>().unwrap();
                if !playlist.entries.contains_key(&entry_num) {
                    let entry = Entry::default();
                    playlist.entries.insert(entry_num, entry);
                }
                let mut entry = playlist
                    .entries
                    .get_mut(&entry_num)
                    .unwrap();
                match field {
                    "File" => entry.file = right.to_string(),
                    "Title" => entry.title = right.to_string(),
                    "Length" => {
                        entry.length = right.parse::<i32>().unwrap();
                    },
                    _ => {}
                }
            } else {
                // Check for meta tag
                let result = alpha1_(left);
                if result.is_ok() {
                    match result.unwrap().1 {
                        "numberofentries" => {
                            playlist.number_of_entries = right
                                .parse::<u32>()
                                .unwrap();
                        },
                        "Version" => {
                            playlist.version = right.to_string();
                        },
                        _ => {}
                    }
                }
            }
        },
        Err(err) => tracing::warn!("ERRRRRR:{:?}", err),
    }

    playlist
}

#[cfg(test)]
mod tests {
    use crate::pls::parse;

    static PLS: &str = "\
[playlist]
numberofentries=4
File1=http://ice6.somafm.com/christmas-128-mp3
Title1=SomaFM: Christmas Lounge (#1): Chilled holiday grooves and classic winter lounge tracks. (Kid and Parent safe!)
Length1=-1
File2=http://ice4.somafm.com/christmas-128-mp3
Title2=SomaFM: Christmas Lounge (#2): Chilled holiday grooves and classic winter lounge tracks. (Kid and Parent safe!)
Length2=-1
File3=http://ice2.somafm.com/christmas-128-mp3
Title3=SomaFM: Christmas Lounge (#3): Chilled holiday grooves and classic winter lounge tracks. (Kid and Parent safe!)
Length3=-1
File4=http://ice1.somafm.com/christmas-128-mp3
Title4=SomaFM: Christmas Lounge (#4): Chilled holiday grooves and classic winter lounge tracks. (Kid and Parent safe!)
Length4=-1
Version=2
";

    #[test]
    fn parse_file() {
        let playlist = parse(PLS);
        assert!(playlist.is_ok());
        let playlist = playlist.unwrap();
        assert_eq!(playlist.files().len(), 4);
        assert_eq!(playlist.number_of_entries, 4);
        assert_eq!(playlist.version, "2");
    }

}
