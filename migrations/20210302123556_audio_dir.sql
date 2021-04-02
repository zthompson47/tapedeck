create table media_dir(
    id integer primary key not null,
    last_modified integer,
    location blob unique not null
);
create table media_file(
    id integer primary key not null,
    media_dir_id integer not null,
    file_size integer,
    media_type text,
    location blob unique not null,
    foreign key(media_dir_id) references media_dir(id)
);
