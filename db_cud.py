import config as cfg
from db_meta import db
import sqlalchemy
from sqlalchemy.sql import func
from sqlalchemy import select, update, text, desc, bindparam, asc, and_ 
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

def create_post(conn, boardid, threadid, filedatas, body, password, name='', email='', subject='',  sage=False, ip=''):
    """ Submits a new post, without value validation
    However, it does check if the post should be forced-sage
        Either due to exceeding thread post limit
        or because a mod has killed the thread (thread.alive = false)
    
        Args:
            boardid (int): board_id
            thread (int): thread id
            filename (str): filename, on disk (path is implied by config'd dir)
            body (str): unparsed body text
            password (str): plaintext password for post; hashed with bcrypt before storing.
            name (Optional[str]): poster's name
            email (Optional[str]): email (Should this still even be a field?)
            sage (Optional[bool])): sage post?
        Returns:
            int: post_id
            int: fake_id
    """
    postdata = {
        'thread_id':threadid,
        'name':name,
        'email':email,
        'subject':subject,
        'body':body,
        'password':password,
        'ip_address': ip,
        'sage':sage}
    postquery = posts.insert()
    filesquery = files.insert()

    password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    postcount = select([func.count(posts.c.id)]).\
                    where(posts.c.thread_id == threadid)
    talive =  select([threads.c.alive]).\
                where(threads.c.id == threadid)
    update_fpid = update(boards).\
                    where(boards.c.id == boardid).\
                  values( cur_pid = boards.c.cur_pid + 1 )
    get_fpid = select([boards.c.cur_pid]).\
                 where( boards.c.id == boardid)
    with transaction(conn):
        # in order to have a post-id index local to the board
        # we have to maintain it ourselves. So the fake_id for the post, that shown to the user
        # increment the board's fpid by 1
        conn.execute( update_fpid )
        # then get the new fake_id, and use it for the post
        fake_id = conn.execute( get_fpid ).fetchone()['cur_pid']
        postdata['fake_id'] = fake_id
        #boardid = conn.execute(select([boards.c.id]).\
        #            where(boards.c.title == boardname)).fetchone()['id']
        #threadlist = select([threads.c.id]).where(
        #                threads.c.board_id == boardid)
        #board_countq = select([func.count(posts)]).where(
        #                posts.c.thread_id.in_( threadlist ))
        #board_count = conn.execute( board_countq ).fetchone()[0]

        count = conn.execute(postcount).fetchone()[0]
        isalive = conn.execute(talive).fetchone()[0]

        fsage = (count > cfg.thread_max_posts) or (not isalive)
        if fsage: #forced saged
            postdata['sage'] = fsage

        post_id = conn.execute(postquery, postdata).inserted_primary_key[0]
        if filedatas: # list of empty dictionary
            for f in filedatas:
                f['post_id'] = post_id
            conn.execute(filesquery, filedatas)
    return post_id, postdata['fake_id']

def cleanup_threads(boardid, conn=None):
    """ runs through and deletes any thread that has fallen off the board 
    Since this can only occur with the creation of a new thread, this check
    should only have to be made then. 
        Args:
            boardid (int): board_id
            conn (connection): connection being used in the transaction
        Returns:
            bool: succeeded or not"""

    # subquery gets the latest N threads, that aren't on 
    # anything after that has fallen off the board
    query ="""
        SELECT threads.id FROM threads WHERE threads.id not in (
            SELECT threads.id FROM threads
            JOIN posts
            ON threads.id = posts.thread_id
            WHERE 
                board_id = :boardid
            AND posts.id = (
                SELECT max(id) FROM posts p1 WHERE threads.id = p1.thread_id
                                                        AND p1.sage = :false
                                                        AND threads.op_id != p1.id)
            GROUP BY threads.id
            ORDER BY posts.id DESC
            LIMIT :thread_max)
    """
 
    thread_max = cfg.index_max_pages * cfg.index_threads_per_page
    data = {'boardid' : boardid,
            'thread_max' : thread_max,
            'false' : str(sqlalchemy.false())}
            #'true' : str(sqlalchemy.true())}

    success = False
    with transaction(conn):
        threadids = conn.execute(query, data).fetchall()
        threadids = [tid[0] for tid in threadids]
        for tid in threadids:
            delete_thread(conn, tid)
        success = True
    return success

# for use by mods
def mark_thread_dead(conn, op_id):
    with transaction(conn):
        conn.execute(threads.update().where(threads.c.op_id == op_id).values(alive = False))
    return True
    
def create_thread(conn, boardid, filedatas, body, password, name, email, subject, ip):
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
            int: fakeid; id shown to user, local to the board
    """
    # get the board id
    # make a new thread
    # make a new post
    # thread op = new post
    # delete any threads that fell off the board
    with transaction(conn):
        true = str(sqlalchemy.true())
        threadid = conn.execute(threads.insert().values(
                     board_id= boardid, 
                     alive=true,
                     sticky=true)).inserted_primary_key[0]
        postid,fakeid = create_post(conn, boardid,
                    threadid, filedatas, 
                    body, 
                    password, name, 
                    email, subject, 
                    sage=False,
                    ip=ip)
        conn.execute(threads.update().\
                where(threads.c.id == threadid).\
                values(op_id= postid))
        #cleanup_threads(conn, boardid)
    return threadid, postid, fakeid

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
                                    active=active,
                                    cur_pid=0)
    with transaction(conn):
        boardid = conn.execute(query).inserted_primary_key[0]
    return boardid


def create_backrefs(conn, backreflist):
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

def mark_dirtyclean(conn, postid, isdirty):
    with transaction(conn):
        query = posts.update().where(posts.c.id == postid).values(dirty= isdirty)
        conn.execute(query)
    
def delete_thread(conn, threadid):
    """ wipe out a whole thread """

    # delete the thread itself
    d_threadq = threads.delete().where(threads.c.id == threadid) 
    # delete all posts for the thread
    #d_postq = posts.delete().where(posts.c.thread_id == threadid) 
    # get all posts in thread
    postsq = select([posts.c.id]).where(posts.c.thread_id == threadid)
    with transaction(conn):
        conn.execute(d_threadq) 
        postlist = conn.execute(postsq).fetchall()
        postlist = [ p[0] for p in postlist]
        map(lambda postid: delete_post(conn, postid), postlist)

def delete_post(conn, postid):
    """ the actual post deletion
        TODO: THIS NEEDS TO DELETE FILES TOO"""
    d_backrefsq = backrefs.delete().where(backrefs.c.head == postid)
    d_postq = posts.delete().where(posts.c.id == postid)
    d_imgq = files.delete().where(files.c.post_id == postid)
    with transaction(conn):
        conn.execute( d_backrefsq )
        conn.execute( d_postq )
        conn.execute( d_imgq )
