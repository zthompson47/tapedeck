create table audio_group(
    id integer primary key not null,
    name unique,
    url text unique,
    path blob unique
);
create table audio_dir(
    id integer primary key not null,
    url text unique,
    path blob unique,
    last_modified integer
);
create table audio_file(
    id integer primary key not null,
    url text unique,
    path blob unique,
    file_size integer,
    mime_type text,
    last_modified integer
);
create table extra_file(
    id integer primary key not null,
    url text unique,
    path blob unique,
    file_size integer,
    mime_type text,
    last_modified integer
);
create table audio_group_audio_dir(
    audio_group_id integer not null,
    audio_dir_id integer not null,
    foreign key(audio_group_id) references audio_group(id),
    foreign key(audio_dir_id) references audio_dir(id)
);
create table audio_dir_audio_file(
    audio_dir_id integer not null,
    audio_file_id integer not null,
    foreign key(audio_dir_id) references audio_dir(id),
    foreign key(audio_file_id) references audio_file(id)
);
create table audio_dir_extra_file(
    audio_dir_id integer not null,
    extra_file_id integer not null,
    foreign key(audio_dir_id) references audio_dir(id),
    foreign key(extra_file_id) references extra_file(id)
);
