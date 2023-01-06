use std::collections::HashMap;

use pest::Parser;

#[derive(Clone, Debug, Default)]
pub struct Playlist {
    _has_header: bool,
    number_of_entries: u32,
    version: String,
    entries: HashMap<u32, Entry>,
}

impl Playlist {
    /// Return a list of just the urls from the entries.
    pub fn files(&self) -> Vec<String> {
        let mut result = Vec::new();
        for i in 1..=self.number_of_entries {
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

#[allow(clippy::upper_case_acronyms)]
#[derive(Parser)]
#[grammar = "pls.pest"]
pub struct PlsParser;

pub fn parse(input: &str) -> std::result::Result<Playlist, String> {
    let file = PlsParser::parse(Rule::file, input).unwrap().next().unwrap();
    let mut playlist = Playlist::default();

    // TODO comment so I can remember how this works
    for row in file.into_inner() {
        if row.as_rule() == Rule::row {
            for keyval in row.into_inner() {
                match keyval.as_rule() {
                    Rule::version => {
                        playlist.version = keyval.into_inner().as_str().to_string();
                    }
                    Rule::num_entries => {
                        playlist.number_of_entries =
                            keyval.into_inner().as_str().parse::<u32>().unwrap();
                    }
                    Rule::entry_part => {
                        let mut kv_iter = keyval.into_inner();

                        if let Some(key) = kv_iter.next() {
                            let inner_key = key.into_inner().next().unwrap();
                            let key_type = inner_key.as_rule();

                            let index = inner_key.into_inner().as_str().parse::<u32>().unwrap();

                            let entry =
                                playlist.entries.entry(index).or_insert_with(Entry::default);

                            if let Some(val) = kv_iter.next() {
                                let val = val.into_inner().as_str();
                                match key_type {
                                    Rule::file_idx => entry.file = val.to_string(),
                                    Rule::title_idx => entry.title = val.to_string(),
                                    Rule::length_idx => {
                                        entry.length = val.parse::<i32>().unwrap()
                                    }
                                    _ => {}
                                }
                            }
                        }
                    }
                    _ => {}
                }
            }
        }
    }

    Ok(playlist)
}

#[cfg(test)]
mod tests {
    use crate::playlist::parse;

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
        let file2 = &playlist.files()[1];
        println!("{:?}", &playlist.files());
        assert_eq!(file2, "http://ice4.somafm.com/christmas-128-mp3");
        let file2 = playlist.entries.get(&2).unwrap();
        assert_eq!(file2.file, "http://ice4.somafm.com/christmas-128-mp3");
        assert!(file2.title.as_str().starts_with("SomaFM"));
        assert_eq!(file2.length, -1);
    }
}
