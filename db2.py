# project specific
from config import cfg
from db_meta import db
import db_cud

#sqlalchemy
import sqlalchemy
from sqlalchemy.sql import func
from sqlalchemy import Table, Column, Integer, String, Text, Boolean, DateTime, MetaData, ForeignKey, UniqueConstraint
from sqlalchemy import select, text, desc, bindparam, asc, and_

# python batteries
import os
import bcrypt
import time
import datetime
from contextlib import contextmanager

# This file contains the entry points to db work from the flask application
# All functions here create new connections, and consume engines
# All functions must be decorated with either with_[slave|engine]
# which will inject the relevant engine for use by the function.
# None of these functions should ever be called by another db function.

# None of the functions here should interact with the database directly
# They serve only to handle all the business logic between calls.

#engine, slave= db.engine, db.slave
#metatadata= db.metadata
#boards, backrefs, threads, posts, mods, banlist = db.boards, db.backrefs, db.threads, db.posts, db.mods, db.banlist
engine, slave= db.engine, db.slave
metatadata= db.metadata
boards = db.boards
backrefs = db.backrefs
threads = db.threads
posts = db.posts
mods = db.mods
banlist = db.banlist

@contextmanager
def connection(engine):
    """ spawns, and closes, a new connection """
    try:
        conn = engine.connect()
        yield conn
    except: 
        raise  # atm, this does no exception handling
    finally:   
        conn.close()

def with_slave(fn):
    """ Simple decorator to inject slave db as the engine """
    def go(*args, **kwargs):
        return fn(*args, **kwargs, engine=db.slave)
    return go

def with_master(fn):
    """ Simple decorator to inject master db as the engine """
    def go(*args, **kwargs):
        return fn(*args, **kwargs, engine=db.engine)
    return go
    
@with_master
def delete_post(postid, password, ismod=False, engine=None):
    """ Validates that the user can delete the post, then deletes it
        If the post is the op, the whole thread will be deleted as well.

        Args:
            postid (int): id of post to be deleted
            password (str): plaintext password for the user (auto-gen'd), should have been stored in the cookie
            ismod (bool): is this a validated mod?
    """
    candel = False
    done = False
    password = password.encode('utf-8')
    if not ismod:
        query = select([posts.c.password]).where(postid == bindparam('postid'))
        hashed = engine.execute(query, postid=postid).fetchone()['password']
        candel = bcrypt.hashpw(password, hashed) == hashed

    if ismod or candel:
        with connection(engine) as conn:
            threadid = _fetch_threadid(post_id)
            if threadid: # if it had returned, its was the op for a thread
                db_cud.delete_thread(conn, threadid)
            else:
                db_cud.delete_post(conn, postid)

@with_master
def create_post(thread, filename, body, password, name='', email='', subject='', sage=False, engine=None):
    with connection(engine) as conn:
        pid = db_cud.create_post(conn, thread, filename, body, password, name, email, subject, sage)
    return pid


@with_slave
def fetch_board_data(title, engine=None):
    """ Gets board data, based on board-title 
        Args:
            title (str): board title ('v')
        Returns:
            ResultProxy: { id, title, subtitle, slogan, active }
    """
    q = select([boards]).where(boards.c.title == title)
    return engine.execute(q).fetchone()

@with_slave
def fetch_thread(threadid, engine=None):
    """ gets all the posts for a single thread
        Args:
            threadid (int): id of thread
        Returns:
            list: the original post, followed by every other post in order of id
                each post is dicts
    """
    op_query = select([posts]).where(text('posts.id = (select op_id from threads where threads.id = :threadid)'))
    posts_query = select([posts]).where(text(""" 
                            posts.thread_id = :threadid 
                            AND posts.id != (SELECT op_id from threads where threads.id =:threadid)""")).\
                  order_by(asc(posts.c.id))

    op_result = engine.execute(op_query, threadid=threadid).fetchone()
    posts_result = engine.execute(posts_query, threadid=threadid).fetchall() 
    posts_result.insert(0, op_result)
    done = list()
    for p in posts_result:
        p = dict(p.items()) # so I can inject stuff into it
        p['tails'] = fetch_backrefs(p['id'])
        done.append(p)
    return done

@with_slave 
def fetch_page(board, pgnum=0, engine=None):
    """ Generates the latest index
    Get threads (pgnum * thread_count) to ((pgnum+1) * thread_count) threads, ordered by the latest post in the thread
    Get the last 5 posts for those threads
        Args:
            board (str): board title
            pgnum (Optional[int]): page number (default: 0)
        Returns:
            Array: [ (op_post, post1, post2, ..)
                        (op_post, post1, post2, ..)
                        (etc)]
    """
    # gets the last 10 threads with the latest posts, and their op_ids
    # ignoring saged posts
    latest_threads_query = """
        SELECT threads.id as id, op_id FROM threads
        JOIN posts
        ON threads.id = posts.thread_id
        WHERE board_id = (
            SELECT board_id from boards where boards.title = :board_title)
        AND posts.id = (
            SELECT max(id) FROM posts p1 WHERE threads.id = p1.thread_id
                                                    AND p1.sage = :false)
        GROUP BY threads.id
        ORDER BY posts.id DESC 
        LIMIT 10 OFFSET :offset;
        """
    offset = pgnum * cfg.index_threads_per_page
    stmt = text(latest_threads_query).columns(threads.c.id, threads.c.op_id)
    thread_data = engine.execute(stmt, board_title=board, 
                                    offset=offset, 
                                    false=str(sqlalchemy.false()),
                                    true=str(sqlalchemy.true())).fetchall()

    op_query = select([posts]).where(text('posts.id = :op_id'))
    latest_posts = select([posts]).where(text('posts.thread_id = :threadid AND posts.id != :op_id')).\
                                order_by(desc(posts.c.id)).\
                                limit(bindparam('post_page'))
    posts_query = select([latest_posts]).order_by(asc("id"))
    pagedata = list()
    for thread in thread_data:
        op_data = {'op_id': thread['op_id']}
        posts_data = {'threadid':thread['id'],
                        'op_id':thread['op_id'],
                        'post_page':cfg.index_posts_per_thread}
        op_result = engine.execute(op_query, op_data).fetchone()
        posts_result = engine.execute(posts_query, posts_data).fetchall() 
        posts_result.insert(0, op_result)
        done = []
        for p in posts_result:
            p = dict(p.items()) # so I can inject stuff into it
            p['tails'] = fetch_backrefs(p['id'])
            done.append(p)
        pagedata.append(done)
    return pagedata 

@with_master
def create_backrefs_for_thread(backreflist, engine=None):
    """ Adds backrefs for each post, for an entire thread
        Args:
            tail (int): the id of the new post
            heads (heads): a list of all post-ids being pointed to
    """
    with connection(engine) as conn:
        db_cud.create_backrefs_for_thread(conn, backreflist)
@with_master
def create_backrefs(backrefs, engine=None):
    """
        Args:
            backrefs (tuple): (
                1. postid referring to others,
                2. [ list of postid being referred to ]
    """
    with connection(engine) as conn:
        db_cud.create_backrefs(conn, backrefs)

@with_slave
def fetch_backrefs(postid, engine):
    """ Gets the list of all posts pointing to a given post
        Args:
            postid (int): id of the post in question
        Returns:
            List(ResultProxy): [{backrefs.tail, posts.thread_id}]
    """
    q = """SELECT backrefs.tail, posts.thread_id FROM backrefs 
            JOIN posts ON backrefs.tail = posts.id
            WHERE backrefs.head = :postid
            ORDER BY backrefs.tail"""
    stmt = text(q).columns(backrefs.c.tail, posts.c.thread_id)
    return engine.execute(q, postid=postid).fetchall()

#TODO: db_cud.mark_thread_dead
@with_master
def mark_thread_autosage(threadid, engine=None):
    with connection(engine) as conn:
        db_cud.mark_thread_dead(conn, threadid)
    engine.execute(threads.update().where(threads.c.id == threadid).values(alive = False))
    return True
    
@with_master
def create_thread(boardname, filename, body, password, name='', email='', subject='', engine=None):
    """ Submits a new thread, without value checking. 
        Args:
            board (int): board name
            name (str): poster's name
            email (str): 
            filename (str): filename, on disk (path is implied by config'd dir)
            post (str): unparsed body text
            password (str): plaintext password for post; hashed with bcrypt before storing.
        Returns:
            int: thread_id; None if it failed
            int: post_id
    """
    with connection(engine) as conn:
        threadid, postid = db_cud.create_thread(conn, boardname,
                                filename, body,
                                password, name,
                                email, subject)
    return threadid, postid

@with_master
def create_board(title, subtitle, slogan, active=True, engine=None):
    """ Creates a new board (multiple new tables)
        Args:
            board_title (str): ie /v/ (just 'v')
            board_subtitle (str): ie vidya
            board_slogan (str): ie /v/ has come too.
        Returns:
            id, str: board
    """
    with connection(engine) as conn: 
        boardid = db_cud.create_board(conn, title, subtitle, slogan, active)
    return boardid

@with_slave
def fetch_all_boards(engine=None):
    """ returns all boards as a list of tuples [(boardid, boardname)]
        Returns:
            list of dicts: [{id, title}
            list of tuples: [(boardid, boardname)]
    """
    query = select([boards.c.id, boards.c.title]).\
                where(boards.c.active == sqlalchemy.true()).\
                order_by(boards.c.title)
    board_list = engine.execute(query).fetchall()
    return board_list

@with_slave
def _is_post(postid, engine=None):
    q = select([posts.c.id]).where(posts.c.id == bindparam('postid'))
    pid = engine.execute(q, postid=postid).fetchone()
    return True if pid else None

@with_slave
def _fetch_thread_of_post(postid, engine=None):
    q = select([posts.c.thread_id]).where(posts.c.id == bindparam('postid'))
    pid = engine.execute(q, postid=postid).fetchone()
    return pid['thread_id'] if pid else None

@with_slave
def _fetch_threadid(opid, engine=None):
    """ given the op_id, gets the associated thread_id """
    q = select([threads.c.id]).where(threads.c.op_id == bindparam('opid'))
    tid = engine.execute(q, opid=opid).fetchone()
    return tid['id'] if tid else None

@with_slave
def _is_thread(threadid, engine=None):
    """ given the threadid, see if the thread exists"""
    q = select([threads.c.id]).where(threads.c.id == bindparam('threadid'))
    tid = engine.execute(q, threadid=threadid).fetchone()
    return True if tid else False

@with_slave
def validate_mod(username, password, engine=None):
    password = password.encode('utf-8')
    hashed = engine.execute(select([mods.c.username]).\
                where(username=bindparam('username')), username=username)['password']
    return bcrypt.hashpw(password, hashed) == hashed

def makedata():
    v = create_board('v', 'vidya', 'vidyagames')
    a = create_board('a', 'anything', 'anything at all')
    vt1, vp1 = create_thread('v', 'img2.png', 'op', 'vp1')
    vt2, vp2 = create_thread('v', 'img2.png', 'op', 'vp2')
    vt3, vp3 = create_thread('v', 'img2.png', 'op', 'vp3')
    vt4, vp4 = create_thread('v', 'img2.png', 'op', 'vp4')
    vt5, vp5 = create_thread('v', 'img2.png', 'op', 'vp4')
    for t in [vt1,vt2,vt3,vt4,vt5]:
        for i in range(5):
            create_post(t, 'img1.png', '>>%s \n post %s TESTING TESTING TESTING TESTING\n >fuk \n\n >< spoil \n spoil2 \n ><'%(i+10, i), 'vp%s'%i, 'anonymous', 'email', 'subject')
            create_post(t, 'img1.png', '>>%s \n post %s TYPE2 \n >fuk\n>sdfsdf\ndsfjsdoi>sdofkdspk \n\n >< spoil \n spoil2 \n ><'%(i, i), 'vp%s'%i, 'anonymous', 'email', 'subject')
        create_post(vt1, '', 'saged', 'saged', 'saged', 'saged', 'saged', True)

if __name__ == '__main__':
    #db.create_db()
    db.reset_db()
    makedata()
