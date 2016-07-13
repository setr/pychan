import sqlalchemy
from sqlalchemy.sql import func
from sqlalchemy import Table, Column, Integer, String, Text, Boolean, DateTime, MetaData, ForeignKey, UniqueConstraint
from sqlalchemy import select, text, desc, bindparam, asc
import os
import bcrypt
import time

# defined by _create_db, _fetch_metadata, or
db = "sqlite:///db1.sqlite"
engine= slave= None
metatadata= None
boards= backrefs= threads= posts= mods= banlist= None # tables

#config options
# todo: move to its own file
threads_page= 10  # n threads per index page
posts_page= 5     # latest n posts for thread; displayed on index pages
thread_max_posts = 500 # threads with more than n posts can no longer be bumped
post_maxlen = 2000 # 4chan max post length, on /v/ at least

def with_slave(fn):
    """ Simple decorator to switch to a slave DB for reads
        Returns to master DB at the end of the function
        Master should handle writes, and reads immediately following a write
        Only pure reads should use the slave.
    """
    def go(*args, **kwargs):
        global engine
        old = engine
        engine = slave
        try:
            return fn(*args, **kwargs)
        finally:
            engine = old
    return go

def _create_db(db):
    global engine, slave
    global metatadata
    global boards, threads, posts, mods, banlist, backrefs

    engine = sqlalchemy.create_engine(db, echo=True)
    slave = engine
    metadata = MetaData()

    cascade = {'onupdate': 'cascade', 'ondelete': 'cascade'}
    # unless otherwise commented, all string max-length values are picked with no real justification
    boards = Table('boards', metadata,
            Column('id', Integer, primary_key=True),
            Column('title', Text, nullable=False, index=True, unique=True),
            Column('subtitle', Text, nullable=False),
            Column('slogan', Text),
            Column('active', Boolean))
    threads = Table('threads', metadata,
            Column('id', Integer, primary_key=True),
            Column('board_id', Integer, ForeignKey("boards.id", **cascade)),
            Column('op_id', Integer), #ForeignKey("posts.id", **cascade)),
            Column('alive', Boolean, default=True), # if it exceeds
            Column('sticky', Boolean, default=True),
            UniqueConstraint('board_id', 'op_id'))
    posts = Table('posts', metadata,
            Column('id', Integer, primary_key=True), #sqlite_autoincrement=True),
            Column('thread_id', Integer, ForeignKey("threads.id", **cascade)),
            Column('sage', Boolean),
            Column('name', String(30)),
            Column('email', String(30)),
            Column('subject', String(50)),
            Column('filename', String(255)), # max length of linux filenames
            Column('body', String(post_maxlen), nullable=False), 
            Column('password', String(60), nullable=False), # bcrypt output
            Column('timestamp', DateTime, default=func.current_timestamp()))
    backrefs = Table('backrefs', metadata,
            Column('id', Integer, primary_key=True),
            Column('head', Integer, ForeignKey("posts.id", **cascade)), # post being pointed to
            Column('tail', Integer, ForeignKey("posts.id", **cascade)), # post doing the pointing
            UniqueConstraint('head', 'tail'))
    mods = Table('mods', metadata,
            Column('id', Integer, primary_key=True),
            Column('username', String(30), nullable=False),
            Column('password', String(60), nullable=False), # bcrypt output
            Column('active', Boolean, default=True))
    banlist = Table('banlist', metadata,
            Column('id', Integer, primary_key=True),
            Column('ip_address', String(39)), # ipv6 max length, in standard notation
            Column('reason', String(2000), nullable=False),
            Column('mod_id', Integer, ForeignKey("mods.id")),
            Column('board_id', Integer, ForeignKey("boards.id"), nullable=True)) # if None, it's global ban.
    metadata.drop_all(engine)
    metadata.create_all(engine)
    
def _create_testdb():
    """ Builds an in-memory sqlite db """
    _create_db('sqlite:///:memory:')

def fetch_board_data(title):
    """ Gets board data, based on board-title 
        Args:
            title (str): board title ('v')
        Returns:
            ResultProxy: { id, title, subtitle, slogan, active }
    """
    q = select([boards]).where(boards.c.title == title)
    return engine.execute(q).fetchone()

def _fetch_metadata(db):
    """ Reads the database for table structure
    I'm not sure how well this will actually pan out
        We're only using Strings, Integers, Booleans and DateTime datatypes, 
        so it shouldn't have any real trouble. But Booleans/DateTime objects
        are often quite problematic... """
    global engine, slave
    global metatadata
    global boards, threads, posts, mods, banlist, backrefs
    engine = sqlalchemy.create_engine(db , strategy='threadlocal')
    slave = engine

    metadata = MetaData()
    metadata.reflect(bind=engine)
    boards = metadata.tables['boards']
    threads = metadata.tables['threads']
    posts = metadata.tables['posts']
    mods = metadata.tables['mods']
    banlist = metadata.tables['banlist']
    backrefs = metadata.tables['backrefs']

@with_slave
def fetch_thread(threadid):
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
def fetch_page(board, pgnum=0):
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
        ORDER BY threads.alive DESC, posts.timestamp DESC 
        LIMIT 10 OFFSET :offset;
        """
    offset = pgnum * threads_page
    stmt = text(latest_threads_query).columns(threads.c.id, threads.c.op_id)
    thread_data = engine.execute(stmt, board_title=board, 
                                    offset=offset, 
                                    false=str(sqlalchemy.false())).fetchall()
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
                        'post_page':posts_page}
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

def create_post(thread, filename, body, password, name='', email='', subject='',  sage=False):
    """ Submits a new post, without value checking. 
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
    password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    query = posts.insert().values(thread_id=thread,
                                    name=name,
                                    email=email,
                                    subject=subject,
                                    filename=filename,
                                    body=body,
                                    password=password,
                                    sage=sage)
    post_id = engine.execute(query).inserted_primary_key[0]
    return post_id

def thread_add_backref(backreflist):
    """ Adds the entire thread at once """
    conn = engine.connect()
    query = backrefs.insert()
    for b in backreflist:
        tail = b[0]
        heads = b[1]
        data = [{ "head": head,
                    "tail": tail}
                    for head in heads]
        try:
            conn.execute(query, data)
        except sqlalchemy.exc.IntegrityError:
            pass
    conn.close()

def create_backrefs(tail, heads):
    """ Adds backrefs for each post
        Args:
            tail (int): the id of the new post
            heads (heads): a list of all post-ids being pointed to
    """
    data = [{ "head": head,
                "tail": tail}
                for head in heads]
    query = backrefs.insert()
    engine.executemany(query, data)

def fetch_backrefs(postid):
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

def create_thread(boardname, filename, body, password, name='', email='', subject=''):
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
    # get the board id
    # make a new thread
    # make a new post
    # thread op = new post
    #try:
    boardid = engine.execute(select([boards.c.id]).where(boards.c.title == boardname)).fetchone()['id']
    threadid = engine.execute(threads.insert().values(board_id= boardid)).inserted_primary_key[0]
    postid = create_post(threadid, filename, body, password, name, email, subject)
    engine.execute(threads.update().where(threads.c.id == threadid).values(op_id= postid))
    #except:
    #    return None # for now... does not say why it failed
    return threadid, postid

def create_board(board_title, board_subtitle, board_slogan):
    """ Creates a new board (multiple new tables)
        Args:
            board_title (str): ie /v/ (just 'v')
            board_subtitle (str): ie vidya
            board_slogan (str): ie /v/ has come too.
        Returns:
            id, str: board
    """
    query = boards.insert().values(title=board_title,
                                    subtitle=board_subtitle,
                                    slogan=board_slogan,
                                    active=True)
    boardid = engine.execute(query).inserted_primary_key[0]
    return boardid

@with_slave
def fetch_all_boards():
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

def _is_post(postid):
    q = select([posts.c.id]).where(posts.c.id == bindparam('postid'))
    pid = engine.execute(q, postid=postid).fetchone()
    return True if pid else None

def _fetch_thread_of_post(postid):
    q = select([posts.c.thread_id]).where(posts.c.id == bindparam('postid'))
    pid = engine.execute(q, postid=postid).fetchone()
    return pid['thread_id'] if pid else None

def _fetch_threadid(opid):
    """ given the op_id, gets the associated thread_id """
    q = select([threads.c.id]).where(threads.c.op_id == bindparam('opid'))
    tid = engine.execute(q, opid=opid).fetchone()
    return tid['id'] if tid else None

def _is_thread(threadid):
    """ given the threadid, see if the thread exists"""
    q = select([threads.c.id]).where(threads.c.id == bindparam('threadid'))
    tid = engine.execute(q, threadid=threadid).fetchone()
    return True if tid else False

def delete_post(postid, password, ismod=False):
    """ Validates that the user can delete the post, then deletes it
        If the post is the op, the whole thread will be deleted as well.
        
        Args:
            postid (int): id of post to be deleted
            password (str): plaintext password for the user (auto-gen'd), should have been stored in the cookie
            ismod (bool): is this a validated mod?
        Returns:
            bool: True if post-delete was attempted; False otherwise.
    """
    candel = False
    done = False
    password = password.encode('utf-8')
    if not ismod:
        #query = "SELECT password FROM posts WHERE postid = ?"
        #hashed = _fetch_one(query, (postid,))
        query = select([posts.c.password]).where(postid == bindparam('postid'))
        hashed = engine.execute(query, postid=postid).fetchone()['password']
        candel = bcrypt.hashpw(password, hashed) == hashed
    if ismod or candel:
        with engine.begin() as conn: # transaction
            threadid = _fetch_threadid(post_id)
            if threadid: # if it returns, its the op for a thread
                q = threads.delete().where(threads.c.op_id == bindparam('postid')) # delete the thread itself
                conn.execute(q, postid=postid) 
                q = posts.delete().where(posts.c.thread_id == bindparam('threadid')) # delete all posts for the thread
                conn.execute(q, threadid=threadid)
            conn.execute( backrefs.delete().where(backrefs.c.head == bindparam('postid')), postid=postid)
            conn.execute( posts.delete().where(posts.c.id == bindparam('postid')), postid=postid)
        done = True
    return done
        
def validate_mod(username, password):
    password = password.encode('utf-8')
    hashed = engine.execute(select([mods.c.username]).\
                where(username=bindparam('username')), username=username)['password']
    #hashed = _fetch_one("SELECT password FROM mods WHERE username = ?", (password,))
    return bcrypt.hashpw(password, hashed) == hashed

def testrun():
    _create_testdb()
    makedata()

def makedata():
    v = create_board('v', 'vidya', 'vidyagames')
    a = create_board('a', 'anything', 'anything at all')
    vt1, vp1 = create_thread('v', 'src/imgs/img2.png', 'op', 'vp1')
    vt2, vp2 = create_thread('v', 'src/imgs/img2.png', 'op', 'vp2')
    vt3, vp3 = create_thread('v', 'src/imgs/img2.png', 'op', 'vp3')
    vt4, vp4 = create_thread('v', 'src/imgs/img2.png', 'op', 'vp4')
    vt5, vp5 = create_thread('v', 'src/imgs/img2.png', 'op', 'vp4')
    for t in [vt1,vt2,vt3,vt4,vt5]:
        for i in range(5):
            create_post(t, 'src/imgs/img1.png', '>>%s \n post %s TESTING TESTING TESTING TESTING\n >fuk \n\n >< spoil \n spoil2 \n ><'%(i+10, i), 'vp%s'%i, 'anonymous', 'email', 'subject')
            create_post(t, 'src/imgs/img1.png', '>>%s \n post %s TYPE2 \n >fuk\n>sdfsdf\ndsfjsdoi>sdofkdspk \n\n >< spoil \n spoil2 \n ><'%(i, i), 'vp%s'%i, 'anonymous', 'email', 'subject')
            time.sleep(1)
    create_post(vt1, '', 'saged', 'saged', 'saged', 'saged', 'saged', True)

if __name__ == '__main__':
    #testrun()
    _create_db(db)
    makedata()
    fetch_page('v')
