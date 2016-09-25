# project specific
import config as cfg
from db_meta import db
import db_cud

#sqlalchemy
import sqlalchemy
from sqlalchemy.sql import func, label
from sqlalchemy import select, text, desc, bindparam, asc, and_, exists

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
    """ Validates that the user can delete the post, then deletes it.
        If the post is the op, the whole thread will be deleted as well.

        Args:
            postid (int): id of post to be deleted (the local-postid shown to the user)
            password (str): plaintext password for the post
            ismod (bool): is this a validated mod?
        Returns:
            error: None if worked, error-string if failed
    """
    candel = False 
    done = False
    #password = password.encode('utf-8')
    #postid = _get_realpostid(board, postid)
    if not ismod:
        query = select([posts.c.password]).where(posts.c.id == postid)
        hashed = engine.execute(query).fetchone()['password']
        #candel = bcrypt.hashpw(password, hashed) == hashed
        # we aren't actually hashing post-passwords
        candel = password == hashed
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
def create_post(boardid, thread, filedatas, body, password, name='', email='', subject='', sage=False, engine=None):
    """ Submits a new thread, without value checking. 
        Args:
            boardid (int): board_id
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
        pid, fpid = db_cud.create_post(conn, boardid,
                                        thread, filedatas, 
                                        body,
                                        password, name, 
                                        email, subject, 
                                        sage)
    return pid, fpid


@with_db(slave)
def fetch_boarddata(boardid, engine=None):
    """ Gets board data, based on board-title 
        Args:
            boardid (int): board_id
        Returns:
            ResultProxy: { id, title, subtitle, slogan, active }
    """
    q = select([boards]).where(boards.c.id == boardid)
    return engine.execute(q).fetchone()

@with_db(slave)
def fetch_thread(boardid, threadid, engine=None):
    """ gets all the posts for a single thread
        Args:
            boardid (id): board_id
            threadid (int): id of thread
        Returns:
            list: the original post, followed by every other post in order of id
                each post is dicts
    """
    op_id = select([threads.c.op_id]).where(threads.c.id == threadid).as_scalar()
    posts_query = select([posts]).where(posts.c.thread_id == threadid).\
                  order_by(asc(posts.c.id))

    posts_result = engine.execute(posts_query).fetchall() 
    post_list = inject_backrefs(boardid, posts_result)
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

def parse_post(boardname, boardid, body, post_id, fpid):
    """ injects all our html formatters and adds any backrefs found to the db
    should only be used on post creation, or if the post was future-referencing
    if the post future-references, it marks the post as dirty (for future reparsing)
        Args:
            boardname (str): name of the board title
            post (str): the full content of the post
            post_id (int): the global pid of the post being parsed
            fpid (int): the board-local id (fake_id) of the post being parsed (shown to the user)
        Returns:
            str: the post with all our new html injected; HTML-safe
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
    backref = '<a href="/{board}/{tid}#{pid}" class="history">>>{pid}</a>{space}'
    spoiler = '<del class> {} </del>'
    implying = '<em> {} </em>'

    addrefs = list()
    isdirty = False
    def r_ref(match):
        fake_pid = int(match.group(1)) # the referenced postid; this pid is _fake_; it's number is contextually specific to the board
        pid = _get_realpostid(boardid, fake_pid) # so we need to first get the global pid, for backreferencing
        # preserves following whitespace; particularly \n
        space = match.group(2) if match.group(2) else ""
        if pid: # if no real_pid, the post doesn't exist.
            tid = _fetch_thread_of_post(pid)
            addrefs.append(pid)
            return backref.format(board=boardname, tid=tid, pid=fake_pid, space=space)
        else:
            # if the post does not exist currently
            # and is not a post from the future
            # it must be from the past, and thus never linkable.
            if fake_pid < fpid: 
                isdirty = True
            return ">>{}{}".format(fake_pid, space) # so it doesn't get read by other regex's
    r_imply = lambda match: implying.format(match.group(0))
    r_spoil = lambda match: spoiler.format(match.group(1))

    body = escape(body) # escape the thing, before we do any regexing on it
    body = '\n'.join([re.sub('\s+', ' ', l.strip()) for l in body.splitlines()])
    body = re.sub(f_ref   , r_ref      , body)      # post-references must occur before imply (>>num)
    body = re.sub(f_spoil , r_spoil    , body)  # spoiler must occur before imply (>< text ><)
    body = re.sub(f_imply , r_imply    , body)  # since its looking for a subset  (>text)
    body = re.sub('\n'    , '\n<br>\n' , body)
    
    mark_dirtyclean(post_id, isdirty)
    ## TODO: don't update parsed if we didn't make any substitutions (nothing changed)
    ## though we only use parsed for output.. so we need to check if this is the first time
    ## parsing this post before we make that check
    update_post_parsed(body, post_id) # store the parsed version in the db
    create_backrefs((post_id, addrefs)) # add our new references to the db
    # and we finally return an HTML-safe version of the post, with our stylings injected.
    return body 

@with_db(master)
def update_post_parsed(post, post_id, engine=None):
    """ adds the parsed body of the post to the post id
        Args:
            post (str): the parsed/escaped body of the post
            post_id (int): global id of the post
    """
    with connection(engine) as conn:
        db_cud.update_post_parsed(conn, post, post_id)

@with_db(master)
def mark_dirtyclean(postid, isdirty, engine=None):
    """ sets the dirty flag.
        Args:
            postid (int): global id of the post
            isdirty (bool): should be reparsed in the future, or not
    """
    with connection(engine) as conn:
        db_cud.mark_dirtyclean(conn, postid, isdirty)

def fetch_backrefs(postid, engine):
    """ Gets the list of all posts pointing to a given post
        Args:
            postid (int): global id of the post in question
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
    """ fetches all the files associated with a post
        Args:
            postid (int): global id of the post
        Returns:
            List(ResultProxy): [{filename, filetype, spoilered}]
    """
    q = select([files.c.filename, files.c.filetype, files.c.spoilered]).where(files.c.post_id == postid).order_by(files.c.post_id)
    return engine.execute(q).fetchall()

@with_db(master)
def file_is_referenced(filename, filetype, engine=None):
    """ we only want to delete a file if it has no other posts using it
        ie no other file row with this filename
        Args:
            postid (filename): name of the file (hash)
        Returns:
            Boolean: True if file is being used by an existing post
    """
    q = select([ files ]).where(and_(
                            files.c.filename == filename,
                            files.c.filetype == filetype))
    q = select([ exists(q) ])
    return engine.execute(q).fetchone()[0]

@with_db(slave)
def fetch_files_thread(postid, engine=None):
    """ fetchs all files for the given global postid """
    postids = select([posts.c.id]).where(posts.c.thread_id == postid)
    q = select(
            [files.c.filename, 
                files.c.filetype, 
                files.c.spoilered]).where(
        files.c.post_id.in_( postids )).order_by(files.c.post_id)
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

    #limit_clause = select([ func.count(posts.c.id) - excess ]).\
    #        where( posts.c.thread_id == thread_id ).as_scalar()
    limit_clause = select ([func.count(posts.c.id)]).\
                    where (posts.c.thread_id == thread_id)
    limit = engine.execute(limit_clause).fetchone()[0]
    limit = limit - excess
    limit = 0 if limit < 0 else limit # no negative limits

    op_id = select([ threads.c.op_id ]).where( threads.c.id == thread_id ).as_scalar()

    relevant_posts = select([ posts.c.id.label('pid') ]).\
            where(and_( posts.c.id != op_id,
                        posts.c.thread_id == thread_id)).\
            limit( limit )
    relevant_posts = relevant_posts.apply_labels()

    post_count = func.count(relevant_posts)

    file_count = select([ func.count(files.c.id) ]).\
                    select_from( files.join(relevant_posts) )
    final = select([post_count, file_count])
    return engine.execute(final).fetchone()


def inject_backrefs(boardid, posts_result):
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
        p['tails'] = [ {'tail': get_fakeid(boardid, t[0])[0],
                        'thread_id': t[1]} for t in p['tails']]

        p['files'] = fetch_files(p['id'])
        done.append(p)
    return done


@with_db(slave)
def fetch_page(boardid, pgnum=0, engine=None):
    """ Generates the latest index
    Get threads (pgnum * thread_count) to ((pgnum+1) * thread_count) threads, ordered by the latest post in the thread
    Get the last 5 posts for those threads
        Args:
            boardid (int): board_id
            pgnum (Optional[int]): page number (default: 0)
        Returns:
            Array: [ (op_post, post1, post2, ..)
                        (op_post, post1, post2, ..)
                        (etc)]
    """
    # gets the last n threads with the latest posts, and their op_ids
    # ignoring saged posts
    offset = pgnum * cfg.index_threads_per_page # threads to display

    latest_postid = select([func.max(posts.c.id)]).\
                        where(and_(
                            posts.c.thread_id == text('threads.id'),
                            posts.c.sage == False)).as_scalar().\
                    correlate(None)
    latest_threads_query =  select([threads.c.id, threads.c.op_id]).\
            select_from( threads.join(posts)).\
            where(and_(
                threads.c.board_id == boardid,
                posts.c.id == latest_postid)).\
            group_by(threads.c.id).\
            order_by(desc(posts.c.id)).\
            limit( cfg.index_threads_per_page ).\
            offset( offset )
    thread_data = engine.execute(latest_threads_query)


    pagedata = list()
    for thread in thread_data:
        latest_posts = select([posts]).where(
                                        and_(
                                            posts.c.thread_id == thread['id'],
                                            posts.c.id != thread['op_id'])).\
                                    order_by(desc(posts.c.id)).\
                                    limit( cfg.index_posts_per_thread)

        op_query = select([posts]).where(posts.c.id == thread['op_id'])
        posts_query = select([latest_posts]).order_by(asc("id"))

        op_result = engine.execute(op_query).fetchone()
        posts_result = engine.execute(posts_query).fetchall() 
        posts_result.insert(0, op_result)
        post_list = inject_backrefs(boardid, posts_result)
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
        db_cud.create_backrefs(conn, [backrefs])

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
def create_thread(boardid, filedatas, body, password, name='', email='', subject='', engine=None):
    """ Submits a new thread, without value checking. 
        Args:
            boardid (id): board_id
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
        threadid, postid, fpid = db_cud.create_thread(conn, 
                                    boardid, filedatas, 
                                    body, 
                                    password, name,
                                    email, subject)
    return threadid, postid, fpid

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
    q = select([posts.c.thread_id]).where(posts.c.id == postid)
    pid = engine.execute( q ).fetchone()
    return pid['thread_id'] if pid else None

## TODO: I don't know this is still relevant
@with_db(slave)
def _fetch_threadid(opid, engine=None):
    """ given the op_id, gets the associated thread_id """
    q = select([threads.c.id]).where(threads.c.op_id == opid)
    tid = engine.execute( q ).fetchone()
    return tid['id'] if tid else None

@with_db(slave)
def is_thread(boardid, threadid, engine=None):
    """ given the boardid and threadid, see if the thread exists"""
    q = select([threads.c.id]).where(and_(
                                threads.c.id == threadid,
                                threads.c.board_id == boardid))
    tid = engine.execute(q).fetchone()
    return True if tid else False

@with_db(slave)
def validate_mod(username, password, engine=None):
    password = password.encode('utf-8')
    hashed = engine.execute(select([mods.c.username]).\
                where(mods.c.username == username))['password']
    return bcrypt.hashpw(password, hashed) == hashed

@with_db(slave)
def reparse_dirty_posts(boardname, boardid, engine=None):
    """ reparses any posts marked as dirty for the given board; 
           dirty = referencing not-yet-existing posts
        Args:
            boardname (str): name of the board ("v")
            boardid (int): id of the board
    """
    threadlist = select([threads.c.id]).where(threads.c.board_id == boardid)
    dirty = select([posts.c.body, posts.c.id, posts.c.fake_id]).\
                where(and_(
                    posts.c.dirty == True,
                    posts.c.thread_id.in_( threadlist)))

    for body, pid, fpid in engine.execute(dirty).fetchall():
        parse_post(boardname, boardid, body, pid, fpid)

@with_db(master)
def get_fakeid(boardid, pid, engine=None):
    #boardid = select([boards.c.id]).where(boards.c.title == boardname).as_scalar()
    threadlist = select([threads.c.id]).where(threads.c.board_id == boardid)
    fakeid = select([posts.c.fake_id]).\
                where(
                and_(
                    posts.c.id == pid,
                    posts.c.thread_id.in_( threadlist)))
    return engine.execute( fakeid ).fetchone()

@with_db(slave)
def get_boardid(boardname, engine=None):
    """ given boardname, fetch the db's ID for it """
    return engine.execute( 
                select([boards.c.id]).\
                    where( boards.c.title == boardname )).\
                    fetchone()[0]
@with_db(slave)
def _get_realpostid(boardid, fakeid, engine=None):
    """ gets the db postid from the id used on the board itself """
    threadlist = select([threads.c.id]).where(threads.c.board_id == boardid)
    postidq = select([posts.c.id]).\
                where(
                 and_(
                     posts.c.thread_id.in_( threadlist ),
                     posts.c.fake_id == fakeid))
    postid = engine.execute( postidq ).fetchone()
    return postid[0] if postid else None

def makedata():
    import gen_helpers as gh
    vid = create_board('v', 'vidya', 'vidyagames')
    aid = create_board('a', 'anything', 'anything at all')
    img1 = [{'filename':'img1', 
            'filetype': 'png',
            'spoilered': False}]
    img2 = [{'filename':'img2', 
            'filetype': 'png',
            'spoilered': True}]
    vt1, vp1, _ = create_thread(vid, img2, 'op', 'vp1')
    vt2, vp2, _ = create_thread(vid, img2, 'op', 'vp2')
    vt3, vp3, _ = create_thread(vid, img2, 'op', 'vp3')
    vt4, vp4, _ = create_thread(vid, img2, 'op', 'vp4')
    vt5, vp5, _ = create_thread(vid, img2, 'op', 'vp4')
    for t in [vt1,vt2,vt3,vt4,vt5]:
        for i in range(5):
            p1 = '>>%s \n post %s TESTING TESTING TESTING TESTING\n >fuk \n\n >< spoil \n spoil2 \n ><'%(i+10, i)
            p2 = '>>%s \n post %s TYPE2 \n >fuk\n>xcvcxdfsdf\ndsfjsdoi>sdofkdspk \n\n >< spoil \n spoil2 \n ><'%(i, i)
            pid1= create_post(vid, t, img1, p1, 'vp%s'%i, 'anonymous', 'email', 'subject')
            pid2= create_post(vid, t, img1, p2, 'vp%s'%i, 'anonymous', 'email', 'subject')
        create_post(vid, vt1, {}, 'sage in all fields',  'saged', 'saged', 'saged', 'saged', True)
    reparse_dirty_posts('v', vid)

if __name__ == '__main__':
    #db.create_db()
    db.reset_db()
    makedata()

