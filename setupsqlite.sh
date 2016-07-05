#!/usr/bin/env bash


db () { sqlite3 datastore.sqlite "$1"; }
rm datastore.sqlite

#board_id  | board_title | board_subtitle | board_slogan
#thread_id | board_id | op_id
#post_id   | thread_id | name | email | subject | filename | post_text
#
#mod_id | username | password
#mod_id | board_id
#
#board_id 1:N thread_id
#thread_id 1:1 op_id
#post_id N:1 thread_id
#mod_id N:N board_id

read -d '' createtable <<'_EOF_'
CREATE TABLE boards(
        board_id INTEGER PRIMARY KEY,
        title TEXT,
        subtitle TEXT,
        slogan TEXT,
        active TEXT
);
CREATE TABLE threads(
        thread_id INTEGER PRIMARY KEY,
        board_id INTEGER REFERENCES boards(board_id) ON UPDATE CASCADE ON DELETE CASCADE,
        op_id INTEGER REFERENCES posts(post_ID) ON UPDATE CASCADE ON DELETE CASCADE
);
CREATE TABLE posts(
        post_id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id INTEGER REFERENCES threads(thread_id) ON UPDATE CASCADE ON DELETE CASCADE,
        name TEXT,
        email TEXT,
        subject TEXT,
        filename TEXT,
        body TEXT,
        password TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE mods(
        mod_id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        active TEXT
);
CREATE TABLE banlist(
        ban_id INTEGER PRIMARY KEY,
        ip_addr TEXT,
        reason TEXT,
        mod_id INTEGER REFERENCES mods(mod_id),
        board_id INTEGER REFERENCES boards(board_id)
);
_EOF_
db "$createtable"
db "PRAGMA foreign_keys = ON;"

# get latest threads
#select threads.thread_id, board_id, op_id, post_id, timestamp from threads JOIN posts on threads.thread_id = posts.thread_id where board_id = 1 and timestamp = (select max(timestamp) from posts p1 where threads.thread_id = p1.thread_id) group by threads.thread_id;


