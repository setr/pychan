from config import cfg
from db_meta import db
import sqlalchemy
from sqlalchemy.sql import func
from sqlalchemy import select, text, desc, bindparam, asc, and_
import os
import bcrypt
import time
import datetime
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection

# this file handles all CUD operations
# every function here consumes a connection
# and operates using transactions (regardless of complexity and strict-dependencies of sql interaction)
#  life is just easier with a consistent assumption, and I'm 
#  assuming there won't be any real overhead penalities.

# Also, sqlalchemy will handle the nested transcation logic for us
# and this means that we can have functions calling each other freely

# NOTE: NO FUNCTION IN THIS FILE WILL CLOSE THE CONNECTION

engine, slave= db.engine, db.slave
metatadata= db.metadata
boards = db.boards
backrefs = db.backrefs
threads = db.threads
posts = db.posts
files = db.files
mods = db.mods
banlist = db.banlist
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """ forces sqlite to enforce foreign key relationships """
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

@contextmanager
def transaction(conn):
    try:
        trans = conn.begin()
        yield
    except sqlalchemy.exc.TimeoutError:
        trans.rollback()
    else:
        trans.commit()

def create_post(conn, thread, filedatas, body, parsed, password, name='', email='', subject='',  sage=False):
    """ Submits a new post, without value validation
    However, it does check if the post should be forced-sage
        Either due to exceeding thread post limit
        or because a mod has killed the thread (thread.alive = false)
    
        Args:
            thread (int): thread id
            filename (str): filename, on disk (path is implied by config'd dir)
            body (str): unparsed body text
            password (str): plaintext password for post; hashed with bcrypt before storing.
            name (Optional[str]): poster's name
            email (Optional[str]): email (Should this still even be a field?)
            sage (Optional[bool])): sage post?
        Returns:
            int: post_id
    """
    postdata = {
        'thread_id':thread,
        'name':name,
        'email':email,
        'subject':subject,
        'body':body,
        'parsed':parsed,
        'password':password,
        'sage':sage}
    postquery = posts.insert()
    filesquery = files.insert()

    password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    postcount = select([func.count(posts.c.id)]).where(posts.c.thread_id == thread)
    talive =  select([threads.c.alive]).where(threads.c.id == thread)

    with transaction(conn):
        count = conn.execute(postcount).fetchone()[0]
        isalive = conn.execute(talive).fetchone()[0]

        fsage = (count > cfg.thread_max_posts) or (not isalive)
        if fsage: #forced saged
            postdata['sage'] = fsage

        post_id = conn.execute(postquery, postdata).inserted_primary_key[0]
        if filedatas[0]: # list of empty dictionary
            for f in filedatas:
                f['post_id'] = post_id
            conn.execute(filesquery, filedatas)
    return post_id

def cleanup_threads(boardname, conn=None):
    """ runs through and deletes any thread that has fallen off the board 
    Since this can only occur with the creation of a new thread, this check
    should only have to be made then. 
        Args:
            boardname (str): name of the board
            conn (connection): connection being used in the transaction
        Returns:
            bool: succeeded or not"""

    # subquery gets the latest N threads, that aren't on 
    # anything after that has fallen off the board
    query ="""
        DELETE FROM threads WHERE threads.id not in (
            SELECT threads.id FROM threads
            JOIN posts
            ON threads.id = posts.thread_id
            WHERE board_id = (
                SELECT board_id from boards where boards.title = :board_title)
            AND posts.id = (
                SELECT max(id) FROM posts p1 WHERE threads.id = p1.thread_id
                                                        AND p1.sage = :false
                                                        AND threads.op_id != p1.id)
            GROUP BY threads.id
            ORDER BY posts.id DESC
            LIMIT :thread_max)
    """
    # for any post, if the parent thread is gone, then obviously the post should go with it
    pquery =""" 
        DELETE FROM posts WHERE posts.thread_id in (select threads.id from threads)
        """
 
    thread_max = cfg.index_max_pages * cfg.index_threads_per_page
    data = {'board_title' : boardname,
            'thread_max' : thread_max,
            'false' : str(sqlalchemy.false())}
            #'true' : str(sqlalchemy.true())}

    success = False
    with transaction(conn):
        conn.execute(query, data)
        conn.execute(pquery)
        success = True
    return success

# for use by mods
def mark_thread_dead(conn, threadid):
    with transaction(conn):
        conn.execute(threads.update().where(threads.c.id == threadid).values(alive = False))
    return True
    
def create_thread(conn, boardname, filedatas, body, parsed, password, name, email, subject):
    """ Submits a new thread, without value checking. 
        Args:
            boardname (str): name of the board
            name (str): poster's name
            email (str): 
            filedatas(list(dict)): list of file data
                filename (str): name of file on disk (path implied by config'd dir) with filetype
                filetype (str): pdf, jpeg, etc
                spoilered (bool): is it spoilered?
            post (str): unparsed body text
            password (str): plaintext password for post; hashed with bcrypt before storing.
        Returns:
            int: thread_id; None if it failed
            int: post_id
    """
    # get the board id
    # make a new thread
    # make a new post
    # thread op = new post
    # delete any threads that fell off the board
    with transaction(conn):
        true = str(sqlalchemy.true())
        boardid = conn.execute(select([boards.c.id]).\
                    where(boards.c.title == boardname)).fetchone()['id']
        threadid = conn.execute(threads.insert().values(
                     board_id= boardid, 
                     alive=true,
                     sticky=true)).inserted_primary_key[0]
        postid = create_post(conn, 
                    threadid, filedatas, 
                    body, parsed,
                    password, name, 
                    email, subject)
        conn.execute(threads.update().\
                where(threads.c.id == threadid).\
                values(op_id= postid))
        #cleanup_threads(conn, boardname)
    return threadid, postid

def create_board(conn, title, subtitle, slogan, active=True):
    """ Creates a new board (multiple new tables)
        Args:
            title (str): ie /v/ (just 'v')
            subtitle (str): ie vidya
            slogan (str): ie /v/ has come too.
        Returns:
            id, str: board
    """
    query = boards.insert().values(title=title,
                                    subtitle=subtitle,
                                    slogan=slogan,
                                    active=active)
    with transaction(conn):
        boardid = conn.execute(query).inserted_primary_key[0]
    return boardid

def create_backrefs(conn, brefs):
    query = backrefs.insert().prefix_with("OR REPLACE")
    tail = brefs[0]
    heads = brefs[1]
    data = [{ "head": head,
                "tail": tail}
                for head in heads]
    with transaction(conn):
        conn.execute(query, data)

def create_backrefs_for_thread(conn, backreflist):
    with transaction(conn):
        query = backrefs.insert().prefix_with("OR REPLACE")
        for b in backreflist:
            tail = b[0]
            heads = b[1]
            data = [{ "head": head,
                        "tail": tail}
                        for head in heads]
            conn.execute(query, data)

def update_post_parsed(conn, parsed, postid):
    with transaction(conn):
        query = posts.update().where(posts.c.id == postid).values(parsed=parsed)
        conn.execute(query)
    

def delete_thread(conn, threadid):
    """ wipe out a whole thread """
    # delete the thread itself
    d_threadq = threads.delete().where(threads.c.op_id == bindparam('postid')) 
    # delete all posts for the thread
    d_postq = posts.delete().where(posts.c.thread_id == bindparam('threadid')) 
    with transaction(conn):
        conn.execute(delthreadq, postid=postid) 
        conn.execute(delpostq, threadid=threadid)

def delete_post(conn, postid):
    """ the actual post deletion """
    d_backrefsq = backrefs.delete().where(backrefs.c.head == bindparam('postid'))
    d_postq = posts.delete().where(posts.c.id == bindparam('postid'))
    with transaction(conn):
        conn.execute( d_backrefsq, postid=postid)
        conn.execute( d_postq, postid=postid)
