import sqlite3
import os
import bcrypt
import time

conn = sqlite3.connect('datastore.sqlite')
slaveconn = sqlite3.connect('datastore.sqlite')
masterconn = sqlite3.connect('datastore.sqlite')

#tables
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

#CREATE TABLE boards(
#        board_id INTEGER PRIMARY KEY
#        board_title TEXT
#        board_subtitle TEXT
#        board_slogan TEXT
#        active TEXT
#);
#CREATE TABLE thread(
#        thread_id INTEGER PRIMARY KEY
#        board_id INTEGER REFERENCES boards(board_id) ON UPDATE CASCADE ON DELETE CASCADE
#        op_id INTEGER REFERENCES posts(post_ID) ON UPDATE CASCADE ON DELETE CASCADE
#);
#CREATE TABLE posts(
#        post_id INTEGER PRIMARY KEY AUTOINCREMENT
#        thread_id INTEGER REFERENCES thread(thread_id) ON UPDATE CASCADE ON DELETE CASCADE
#        name TEXT
#        email TEXT
#        subject TEXT
#        filename TEXT
#        body TEXT
#        pass TEXT -- for deleting posts
#);
#CREATE TABLE mods(
#        mod_id INTEGER PRIMARY KEY
#        username TEXT
#        password TEXT
#        active TEXT
#);
#CREATE TABLE banlist(
#        ban_id INTEGER PRIMARY KEY
#        ip_addr TEXT
#        reason TEXT
#        mod_id INTEGER REFERENCES mods(mod_id)
#        board_id INTEGER REFERENCES boards(board_id)
#);

        





def with_slave(fn):
    """ Decorator
    for the duration of the function, the connection points to the slave
    Slave should only be used for reads
    Master should recieve all writes, as well as any reads immediately following a write
    Currently, there is no replication so both master/slave point to the same db.
    """
    def go(*arg, **kw):
        global conn
        global slaveconn
        oldconn = conn
        conn = slaveconn
        try:
            return fn(*arg, **kw)
        finally:
            conn = oldconn
    return go

def _insert_row(query, data=None):
    """ Inserts a single row
        Args:
            query (str): sql query with '?' for parameter substitution
            data (tuple): tuple of str-convertable parameters
        Returns:
            int: id of the row created
    """
    with conn:
        c = conn.cursor()
        c.execute(query, data) if data else c.execute(query)
        rowid = c.lastrowid
    return rowid

def _delete_row(query, data=None):
    try:
        with conn:
            c = conn.cursor()
            c.execute(query, data) if data else c.execute(query)
            rowid = c.lastrowid
        return True
    except SQL.Error:
        return False


def _fetch_one(query, data=None):
    """ Returns a single row
        Args:
            query (str): sql query with '?' for parameter substitution
            data (tuple): tuple of str-convertable parameters
        Returns:
            tuple: row of data
    """
    with conn:
        c = conn.cursor()
        c.execute(query, data) if data else c.execute(query)
        row = c.fetchone()
    return row

def _fetch_all(query, data=None):
    """ Inserts a list of tuples
        Args:
            query (str): sql query with '?' for parameter substitution
            data (tuple): tuple of str-convertable parameters
        Returns:
            list of tuples: table of data
    """
    with conn:
        c = conn.cursor()
        c.execute(query, data) if data else c.execute(query)
        rows = c.fetchall()
    return rows

def new_post(thread, name, email, subject, filename, post, password):
    """ Submits a new post, without value checking. 
        Args:
            thread (int): thread id. New threads omit this value, as a new one will be generated.
            name (str): poster's name
            email (str): 
            filename (str): filename, on disk (path is implied by config'd dir)
            post (str): unparsed body text
            password (str): plaintext password for post; hashed with bcrypt before storing.
        Returns:
            int: post_id or thread_id 
    """
    password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    query = 'INSERT INTO posts(thread_id, name, email, subject, filename, body, password) VALUES (?,?,?,?,?,?,?)'
    data = (thread, name, email, subject, filename, post, password)
    return _insert_row(query, data)

def new_thread(board, name, email, subject, filename, post, password):
    """ Submits a new thread, without value checking. 
        Args:
            board (int): board id
            name (str): poster's name
            email (str): 
            filename (str): filename, on disk (path is implied by config'd dir)
            post (str): unparsed body text
            password (str): plaintext password for post; hashed with bcrypt before storing.
        Returns:
            int: thread_id
    """
    boardid = _fetch_one('SELECT board_id FROM boards WHERE boards.title = ?', (board,))[0]
    threadid = _insert_row('INSERT INTO threads(board_id) VALUES (?)', (boardid,))
    postid = new_post(threadid, name, email, subject, filename, post, password)
    _insert_row('UPDATE threads SET op_id = ? WHERE thread_id = ?', (postid, threadid))
    return threadid

def new_board(board_title, board_subtitle, board_slogan):
    """ Creates a new board (multiple new tables)
        Args:
            board_title (str): ie /v/ (just 'v')
            board_subtitle (str): ie vidya
            board_slogan (str): ie /v/ has come too.
        Returns:
            id, str: board
    """
    query = 'INSERT INTO boards(title, subtitle, slogan, active) VALUES (?, ?, ?, ?)'
    data = (board_title, board_subtitle, board_slogan, True)
    boardid = _insert_row(query, data)

@with_slave
def get_all_boards():
    """ returns all boards as a list of tuples [(boardid, boardname)]
        Returns:
            list of tuples: [(boardid, boardname)]
    """
    query = 'SELECT board_id, title FROM boards WHERE boards.active = 1 ORDER BY title'
    return _fetch_all(query)
    #return [(i[0], i[1]) for i in _fetch_all(query)]

@with_slave
def get_page(pgnum, board):
    """ Generates the latest index
    Get the threads pgnum*10 to (pgnum+1)*10 threads, ordered by the latest post in the thread
    Get the last 5 posts for those threads
        Args:
            pgnum (int): page number
            board (id): board id
        Returns:
            Array: [ (op_post, post1, post2, ..)
                        (op_post, post1, post2, ..)
                        (etc)]
    """
    # gets the last 10 threads with the latest posts, and their op_ids
    query = """
        SELECT threads.thread_id, op_id FROM threads 
        JOIN posts 
        ON threads.thread_id = posts.thread_id 
        WHERE board_id = (
            SELECT board_id from boards where boards.title = ?)
        AND timestamp = (
            SELECT max(timestamp) FROM posts p1 WHERE threads.thread_id = p1.thread_id) 
        GROUP BY threads.thread_id ORDER BY posts.timestamp DESC LIMIT 10 OFFSET ?;
        """
    print("board=%s pgnum=%s" % (board, pgnum))
    threads = _fetch_all(query, (board, pgnum*10))
    print(threads)
    final = list()
    for thread_id, post_id in threads:
        op = _fetch_one("SELECT * FROM posts WHERE post_id = ?", (post_id,))
        posts = _fetch_all("SELECT * FROM posts WHERE thread_id = ? and post_id != ?", (thread_id, post_id))
        posts.insert(0,op)
        final.append(posts)
    return final

def delete_post(postid, password, ismod=False):
    """ validates that the user can delete the post, then deletes it
        Args:
            postid (int): obv
            password (str): plaintext password for the user (auto-gen'd), should have been stored in the cookie
            ismod (bool): is this a validated mod?
        Returns:
            bool: True if password was correct, or user was a mod; False otherwise.
    """
    candel = False
    if not ismod:
        query = "SELECT password FROM posts WHERE postid = ?"
        hashed = _fetch_one(query, (postid,))
        candel = bcrypt.hashpw(password, hashed) == hashed

    if candel or ismod:
        query = "DELETE FROM posts WHERE postid = ?"
        _delete_row(query, (postid,))
        return True
    return False
        
def validate_mod(username, password):
    hashed = _fetch_one("SELECT password FROM mods WHERE username = ?", (password,))
    return bcrypt.hashpw(password, hashed) == hashed



def testrun():
    def inmem():
        global conn, slaveconn, masterconn
        conn = slaveconn = masterconn = sqlite3.connect(':memory:')
        with conn:
            conn.executescript("""
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
                    password TEXT -- for deleting posts
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
        """)

    #inmem()
    def makedata():
        v = new_board('v', 'vidya', 'vidyagames')
        a = new_board('a', 'anything', 'anything at all')
        vt1 = new_thread('v', '', '', '', '', 'vp1', 'vp1')
        vt2 = new_thread('v', '', '', '', '', 'vp2', 'vp2')
        vt3 = new_thread('v', '', '', '', '', 'vp3', 'vp3')
        vt4 = new_thread('v', '', '', '', '', 'vp4', 'vp4')
        vt5 = new_thread('v', '', '', '', '', 'vp5', 'vp5')
        for t in [vt1,vt2,vt3,vt4,vt5]:
            for i in range(5):
                new_post(t, '', '', '', '', 'vp%s'%i, 'vp%s'%i)
                time.sleep(1)
    makedata()

if __name__ == '__main__':
    #testrun()
    get_page(0, 'v')
