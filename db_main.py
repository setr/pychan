# project specific
import config as cfg
from db_meta import db
import db_cud

#sqlalchemy
import sqlalchemy
from sqlalchemy.sql import func, label
from sqlalchemy import Table, Column, Integer, String, Text, Boolean, DateTime, MetaData, ForeignKey, UniqueConstraint
from sqlalchemy import select, text, desc, bindparam, asc, and_

from werkzeug import escape

import dateutil.relativedelta as du

# python batteries
import re
import os
import bcrypt
import time
import datetime
from contextlib import contextmanager

# This file contains the entry points to db work from the flask application
# All functions here create new connections, and consume engines
# All functions must be decorated with with_db(slave|engine)
# which will inject the relevant engine for use by the function.
# None of these functions should ever be called by another db function.

# None of the functions here should interact with the database directly
# They serve only to handle all the business logic between calls.

#engine, slave= db.engine, db.slave
#metatadata= db.metadata
#boards, backrefs, threads, posts, mods, banlist = db.boards, db.backrefs, db.threads, db.posts, db.mods, db.banlist
master, slave= db.engine, db.slave
metatadata= db.metadata
boards = db.boards
backrefs = db.backrefs
threads = db.threads
posts = db.posts
files = db.files
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

def with_db(target):
    """ Simple decorator to inject target db as the engine """
    def wrap(fn):
        def wrapped(*args, **kwargs):
            return fn(*args, engine=target, **kwargs)
        return wrapped
    return wrap
    
@with_db(master)
def delete_post(postid, password, ismod=False, engine=None):
    """ Validates that the user can delete the post, then deletes it
        If the post is the op, the whole thread will be deleted as well.

        Args:
            postid (int): id of post to be deleted
            password (str): plaintext password for the user (auto-gen'd), should have been stored in the cookie
            ismod (bool): is this a validated mod?
        Returns:
            error: None if worked, error-string if failed
    """
    candel = False 
    done = False
    #password = password.encode('utf-8')
    if not ismod:
        query = select([posts.c.password]).where(posts.c.id == postid)
        hashed = engine.execute(query).fetchone()['password']
        #candel = bcrypt.hashpw(password, hashed) == hashed
        # we aren't actually hashing post-passwords
        candel = password == hashed
        print (postid)
        print ( password )
        print ( hashed )
        print ( candel )
    else:
        candel = True

    if candel:
        with connection(engine) as conn:
            threadid = _fetch_threadid(postid)
            if threadid: # if it had returned, its was the op for a thread
                db_cud.delete_thread(conn, threadid)
            else:
                db_cud.delete_post(conn, postid)
        return None
    else:
        return "incorrect password"
@with_db(master)
def create_post(thread, filedatas, body, parsed, password, name='', email='', subject='', sage=False, engine=None):
    """ Submits a new thread, without value checking. 
        Args:
            thread (int): thread_id
            name (str): poster's name
            email (str): 
            files(list(dict)): list of file data
                filename (str): name of file on disk (path implied by config'd dir) with filetype
                filetype (str): pdf, jpeg, etc
                spoilered (bool): is it spoilered?
            post (str): unparsed body text
            password (str): plaintext password for post; hashed with bcrypt before storing.
        Returns:
            int: thread_id; None if it failed
            int: post_id
    """
    with connection(engine) as conn:
        pid = db_cud.create_post(conn, thread, filedatas, body, parsed, password, name, email, subject, sage)
    return pid


@with_db(slave)
def fetch_board_data(title, engine=None):
    """ Gets board data, based on board-title 
        Args:
            title (str): board title ('v')
        Returns:
            ResultProxy: { id, title, subtitle, slogan, active }
    """
    q = select([boards]).where(boards.c.title == title)
    return engine.execute(q).fetchone()

@with_db(slave)
def fetch_thread(threadid, engine=None):
    """ gets all the posts for a single thread
        Args:
            threadid (int): id of thread
        Returns:
            list: the original post, followed by every other post in order of id
                each post is dicts
    """
    op_id = select([threads.c.op_id]).where(threads.c.id == threadid).as_scalar()
    posts_query = select([posts]).where(posts.c.thread_id == threadid).\
                  order_by(asc(posts.c.id))

    posts_result = engine.execute(posts_query).fetchall() 
    post_list = inject(posts_result)
    for p in post_list:
        p['h_time'] = _rel_timestamp(p['timestamp'])
    return post_list

@with_db(slave)
def is_locked(threadid, engine=None):
    q = select([threads.c.locked]).where(threads.c.id == threadid)
    return engine.execute(q).fetchone()[0]

def _rel_timestamp(timestamp):
    """ returns a human readable time-delta between timestamp and current time,
    with only the biggest time unit
    ie 40 hr difference => 1 day
        Args:
            timestamp (datetime): original tim
        Returns:
            str: "1 minute"; "20 minutes"; "3 hours"; "0 seconds"
    """
    # normalize just forces integer values for time-units
    now = datetime.datetime.utcnow()
    delta = du.relativedelta(now , timestamp).normalized()
    attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
    ts = '{} {} ago'
    for a in attrs:
        num = getattr(delta, a)
        if num:
            ts = ts.format(num, a if num > 1 else a[:-1]) # a = minutes, a[-1] = minute
            break
    else: # no break was encountered in for loop
        ts = ts.format(0, 'seconds')
    return ts

def parse_post(post, post_id=None):
    """ injects all our html formatters and adds any backrefs found to the db
    should only be used on post creation, or if the post was future-referencing
        Args:
            post (str): the full content of the post
            post_id (int): If this an update, then we need the post being updated.
        Returns:
            str: the post with all our new html injected; HTML-safe
            list: all post ids being referred to, for backref creation
    """
    # we need to parse out the pids
    # then form the html for it

    # werkzeug escape: Replace special characters "&", "<", ">" and (") to HTML-safe sequences.
    # the regex themselves
        # if an html special character is in the regex, then don't escape() the regex.
        # instead, you'll have to use the html sequences in the regex.
        # searching after the post was escaped.
    f_ref = escape('>>(\d+)(\s)?')   # >>123123
    f_spoil = escape('><(.*)><')     # >< SPOILERED ><
    f_imply = escape('>.+')          # >implying

    f_ref=   re.compile(f_ref)
    f_spoil= re.compile(f_spoil, re.DOTALL) 
    f_imply= re.compile(f_imply, re.MULTILINE) 

    # what they turn into
    backref = '<a href="{tid}#{pid}" class="history">>>{pid}</a>{space}'
    spoiler = '<del class> {} </del>'
    implying = '<em> {} </em>'

    addrefs = list()
    def r_ref(match):
        pid = int(match.group(1))
        # preserves following whitespace; particularly \n
        space = match.group(2) if match.group(2) else ""
        tid = _fetch_thread_of_post(pid)
        addrefs.append(pid) # we still want to create the backref even if the post doesn't exist
                            # so you can do future-referencing. Just don't link it yet.
        if tid: # if no tid, then the post must not exist.
            return backref.format(tid=tid, pid=pid, space=space)
        else:
            return ">>{}{}".format(pid, space) # so it doesn't get read by other regex's
    r_imply = lambda match: implying.format(match.group(0))
    r_spoil = lambda match: spoiler.format(match.group(1))

    post = escape(post) # escape the thing, before we do any regexing on it
    post = '\n'.join([re.sub('\s+', ' ', l.strip()) for l in post.splitlines()])
    post = re.sub(f_ref, r_ref, post)      # post-references must occur before imply (>>num)
    post = re.sub(f_spoil, r_spoil, post)  # spoiler must occur before imply (>< text ><)
    post = re.sub(f_imply, r_imply, post)  # since is looking for a subset  (>text)
    post = re.sub('\n', '\n<br>\n', post)
    if post_id:
        update_post_parsed(post, post_id) # store the parsed version in the db
        create_backrefs((post_id, addrefs)) # add our new references to the db
    # and we finally return an HTML-safe version of the post, with our stylings injected.
    return post, addrefs

@with_db(master)
def update_post_parsed(post, post_id, engine=None):
    with connection(engine) as conn:
        db_cud.update_post_parsed(conn, post, post_id)

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

@with_db(slave)
def fetch_files(postid, engine=None):
    q = select([files.c.filename, files.c.filetype, files.c.spoilered]).where(files.c.post_id == postid).order_by(files.c.post_id)
    return engine.execute(q).fetchall()

@with_db(slave)
def count_hidden(thread_id, engine=None):
    """ Given a thread_id, get the number of posts/files not displayed on the index pages
    posts_in_thread - posts_shown - op (op is always shown; =1)
        Args:
            thread_id (int): id of thread in question
        Returns:
            tuple: 
                Number of posts omitted
                Number of files omitted
    """ 

    # the query got this complex primarily due to the assumption that there may be multiple files
    # per post. So we can't simply do count(id) - excess from posts where thread_id = :thread_id
    # as that'll get us one file per post.

    excess = cfg.index_posts_per_thread + 1  # posts in thread - posts displayed - op_post (1)
    limit_clause = select([ func.count(posts.c.id) - excess ]).\
            where( posts.c.thread_id == thread_id ).as_scalar()
    op_id = select([ threads.c.op_id ]).where( threads.c.id == thread_id ).as_scalar()

    relevant_posts = select([ posts.c.id.label('pid') ]).\
            where(and_( posts.c.id != op_id,
                        posts.c.thread_id == thread_id)).\
            limit( limit_clause )
    relevant_posts = relevant_posts.apply_labels()

    post_count = func.count(relevant_posts)
    file_count = select([ func.count(files.c.id) ]).\
                    select_from( files.join(relevant_posts) )
    final = select([post_count, file_count])
    return engine.execute(final).fetchone()


def inject(posts_result):
    """ For handling any injection of stuff the post lists require.
    list of backrefs
    list of files
        Returns:
            list: list of posts converted to normal dicts,
                with the additional fields:
                'tails': any post ids referring to this one
                'files': dict of file result proxies
    """
    done = list()
    for p in posts_result:
        p = dict(p.items())
        p['tails'] = fetch_backrefs(p['id'])
        p['files'] = fetch_files(p['id'])
        done.append(p)
    return done


@with_db(slave)
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
    offset = pgnum * cfg.index_threads_per_page # threads to display

    board_id = select([boards.c.id]).where(boards.c.title == board).as_scalar()
    latest_postid = select([func.max(posts.c.id)]).\
                        where(and_(
                            posts.c.thread_id == text('threads.id'),
                            posts.c.sage == False)).as_scalar().\
                    correlate(None)
    latest_threads_query =  select([threads.c.id, threads.c.op_id]).\
            select_from( threads.join(posts)).\
            where(and_(
                threads.c.board_id == board_id,
                posts.c.id == latest_postid)).\
            group_by(threads.c.id).\
            order_by(desc(posts.c.id)).\
            limit( 10 ).\
            offset( offset )
    thread_data = engine.execute(latest_threads_query)


    pagedata = list()
    for thread in thread_data:
        latest_posts = select([posts]).where(posts.c.thread_id == thread['id']).\
                                    order_by(desc(posts.c.id)).\
                                    limit( cfg.index_posts_per_thread)

        posts_query = select([latest_posts]).order_by(asc("id"))
        op_query = select([posts]).where(posts.c.id == thread['op_id'])

        op_result = engine.execute(op_query).fetchone()
        posts_result = engine.execute(posts_query).fetchall() 
        posts_result.insert(0, op_result)
        post_list = inject(posts_result)
        for p in post_list:
            p['h_time'] = _rel_timestamp(p['timestamp'])
        pagedata.append(post_list)
    return pagedata 

@with_db(master)
def create_backrefs_for_thread(backreflist, engine=None):
    """ Adds backrefs for each post, for an entire thread
        Args:
            tail (int): the id of the new post
            heads (heads): a list of all post-ids being pointed to
    """
    with connection(engine) as conn:
        db_cud.create_backrefs_for_thread(conn, backreflist)
@with_db(master)
def create_backrefs(backrefs, engine=None):
    """
        Args:
            backrefs (tuple): (
                1. postid referring to others,
                2. [ list of postid being referred to ]
    """
    with connection(engine) as conn:
        db_cud.create_backrefs(conn, backrefs)

@with_db(slave)
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
@with_db(master)
def mark_thread_autosage(threadid, engine=None):
    with connection(engine) as conn:
        db_cud.mark_thread_dead(conn, threadid)
    engine.execute(threads.update().where(threads.c.id == threadid).values(alive = False))
    return True
    
@with_db(master)
def create_thread(boardname, filedatas, body, parsed, password, name='', email='', subject='', engine=None):
    """ Submits a new thread, without value checking. 
        Args:
            board (str): board name
            name (str): poster's name
            email (str): 
            files(list(dict)): list of file data
                filename (str): name of file on disk (path implied by config'd dir) with filetype
                filetype (str): pdf, jpeg, etc
                spoilered (bool): is it spoilered?
            post (str): unparsed body text
            password (str): plaintext password for post; hashed with bcrypt before storing.
        Returns:
            int: thread_id; None if it failed
            int: post_id
    """
    with connection(engine) as conn:
        threadid, postid = db_cud.create_thread(conn, 
                                boardname, filedatas, 
                                body, parsed,
                                password, name,
                                email, subject)
    return threadid, postid

@with_db(master)
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

@with_db(slave)
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

@with_db(slave)
def is_post(postid, engine=None):
    q = select([posts.c.id]).where(posts.c.id == postid)
    pid = engine.execute(q).fetchone()
    return True if pid else False

@with_db(slave)
def fetch_updated_myposts(postids, engine=None):
    """ returns a list of the postids that still actually exist in the db. """
    #postids = tuple(postids) # in_ does not consume lists
    
    q = select([posts.c.id]).where(posts.c.id.in_(postids))
    results = engine.execute(q).fetchall()
    return [ r[0] for r in results ]

@with_db(slave)
def _fetch_thread_of_post(postid, engine=None):
    q = select([posts.c.thread_id]).where(posts.c.id == bindparam('postid'))
    pid = engine.execute(q, postid=postid).fetchone()
    return pid['thread_id'] if pid else None

@with_db(slave)
def _fetch_threadid(opid, engine=None):
    """ given the op_id, gets the associated thread_id """
    q = select([threads.c.id]).where(threads.c.op_id == bindparam('opid'))
    tid = engine.execute(q, opid=opid).fetchone()
    return tid['id'] if tid else None

@with_db(slave)
def _is_thread(threadid, engine=None):
    """ given the threadid, see if the thread exists"""
    q = select([threads.c.id]).where(threads.c.id == bindparam('threadid'))
    tid = engine.execute(q, threadid=threadid).fetchone()
    return True if tid else False

@with_db(slave)
def validate_mod(username, password, engine=None):
    password = password.encode('utf-8')
    hashed = engine.execute(select([mods.c.username]).\
                where(username=bindparam('username')), username=username)['password']
    return bcrypt.hashpw(password, hashed) == hashed

@with_db(slave)
def _check_backref_preexistence(post_id, engine=None):
    """ checks if the post already has references to it. 
    If it does, those posts will be reparsed to inject <a> tags.
        Args:
            post_id: id of the post being created
    """
    dirty = select([backrefs.c.tail]).\
         where(backrefs.c.head == post_id).\
         order_by(asc(backrefs.c.id)).apply_labels()
    dirty_postids = [d[0] for d in engine.execute(dirty).fetchall()]
    for pid in dirty_postids:
        body = engine.execute(select([posts.c.body]).where(posts.c.id == pid)).fetchone()[0]
        parse_post(body, pid)

def makedata():
    import general_helpers as gh
    v = create_board('v', 'vidya', 'vidyagames')
    a = create_board('a', 'anything', 'anything at all')
    img1 = [{'filename':'img1', 
            'filetype': 'png',
            'spoilered': False}]
    img2 = [{'filename':'img2', 
            'filetype': 'png',
            'spoilered': False}]
    vt1, vp1 = create_thread('v', img2, 'op', parse_post('op')[0], 'vp1')
    vt2, vp2 = create_thread('v', img2, 'op', parse_post('op')[0], 'vp2')
    vt3, vp3 = create_thread('v', img2, 'op', parse_post('op')[0], 'vp3')
    vt4, vp4 = create_thread('v', img2, 'op', parse_post('op')[0], 'vp4')
    vt5, vp5 = create_thread('v', img2, 'op', parse_post('op')[0], 'vp4')
    for t in [vt1,vt2,vt3,vt4,vt5]:
        for i in range(5):
            p1 = '>>%s \n post %s TESTING TESTING TESTING TESTING\n >fuk \n\n >< spoil \n spoil2 \n ><'%(i+10, i)
            p2 = '>>%s \n post %s TYPE2 \n >fuk\n>sdfsdf\ndsfjsdoi>sdofkdspk \n\n >< spoil \n spoil2 \n ><'%(i, i)
            p1p, addrefs1 = parse_post(p1)
            p2p, addrefs2 = parse_post(p2)
            pid1= create_post(t, img1, p1, p1p, 'vp%s'%i, 'anonymous', 'email', 'subject')
            pid2= create_post(t, img1, p2, p2p, 'vp%s'%i, 'anonymous', 'email', 'subject')
            create_backrefs((pid1, addrefs1))
            create_backrefs((pid2, addrefs2))
        create_post(vt1, {}, '',  'saged', 'saged', 'saged', 'saged', 'saged', True)

if __name__ == '__main__':
    #db.create_db()
    db.reset_db()
    makedata()
