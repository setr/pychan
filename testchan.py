import db2 as db
import datetime
from flask import Flask, render_template, request
from flask import url_for, flash, redirect, session
from flask import send_from_directory, Markup 
from werkzeug import secure_filename, escape
from pprint import pprint
import random, string
import re
import os
import dateutil.relativedelta as du

import hashlib

app = Flask(__name__)

imgpath = 'src/imgs/'
thumbpath = 'src/thumb/'

ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webm'])
app.config['UPLOAD_FOLDER'] = 'static/' + imgpath
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['minsec_between_posts'] = 30
app.jinja_env.line_statement_prefix = '#' # enables jinja2 line mode
app.jinja_env.line_comment_prefix = '##' # enables jinja2 line mode

database = 'sqlite:///db1.sqlite'


app.secret_key = 'Bd\xf2\x14\xbbi\x01Gq\xc6\x87\x10BVc\x9c\xa4\x08\xdbk%\xfa*\xe3' # os.urandom(24)

#@app.before_first_request
#def load_tables():
#    """ collects all the metadata as soon as the app boots up
#    well, only acts when the first request comes in but whatever"""
#    db._fetch_metadata(database)

@app.before_request
def assign_session_params():
    """ Makes sure the user has basic needs satisfied
        password: password to sign off posts with
        myposts: list of pids posted by the user
        clear-myposts: At max once every 2 days, clear out the posts 
            assigned to their session if the post no longer exists
    """
    if 'password' not in session:
        allowed= string.ascii_letters + string.digits
        session['password']= ''.join(random.choice(allowed) for i in range(24))
    if 'myposts' not in session:
        session['myposts'] = list()

    now = datetime.datetime.utcnow()
    if 'lastclear' not in session:
        session['lastclear'] = now
    delta = now - session['lastclear']
    if delta > datetime.timedelta(days=2): 
        for i, pid in enumerate(session['myposts']):
            if _is_post(pid):
                del session['myposts'][i] # clears out the posts cookies 
    return None

def checktime(fn):
    """ Decorator to make sure its been more than n time since last post """
    def go(*args, **kwargs):
        now = datetime.datetime.utcnow()
        if 'lastpost' not in session:
            session['lastpost'] = now
        else:
            delta = now - session['lastpost']
            mintime = app.config['minsec_between_posts']
            if delta < datetime.timedelta(seconds=mintime):
                return general_error('Please wait at least %s seconds before posting again' % (mintime,))
            else:
                session['lastpost'] = now
        return fn(*args, **kwargs)
    return go


def adminonly(fn):
    """ Decorator
    Checks if the user is currently a mod
    If not, redirect to modpage
    """
    def go(*args, **kwargs):
        if 'mod' in session:
            return fn(*args, **kwargs)
        else:
            return general_error('You must be an admin to see this page') # proper would be 401
    return go

def hashfile(afile, blocksize=65536):
    hasher = hashlib.sha256()
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    afile.seek(0,0) # reset the file pointer
    return hasher.hexdigest()


def _validate_post(post):
    """ Does all our robot/spam checking
        Args:
            post (str): the full content of the post
        Returns:
            bool: True if acceptable
    """
    return True

def _parse_post(post):
    """ injects all our html formatters and adds any backrefs found to the db
    However, I'm not sure we should be doing this on the server side
    especially as currently, we're not actually saving the converted text
    reparsing everything on every refresh..
        Args:
            post (str): the full content of the post
        Returns:
            str: the post with all our new html injected 
            list: all post ids being referred to, for backref creation
    """
    # we need to parse out the pids
    # then form the html for it
    f_ref=   re.compile('&gt;&gt;(\d+)(\s)') # >>123123
    f_spoil= re.compile('&gt;&lt;(.*)&gt;&lt;', re.DOTALL) # >< SPOILERED >< 
    f_imply= re.compile('^&gt;.+', re.MULTILINE) # >implying
    backref = '<a href="{tid}#{pid}" class="history">>>{pid}</a>{you}{space}'
    spoiler = '<del class> {} </del>'
    implying = '<em> {} </em>'
    
    mypids = session['myposts']
    addrefs = list()
    def r_ref(match): 
        pid = int(match.group(1))
        space = match.group(2) # preserves following whitespace; particularly \n
        tid = db._fetch_thread_of_post(pid)
        if tid:
            addrefs.append(pid)
            you = " (You) " if pid in mypids else ""
            return backref.format(tid=tid, pid=pid, space=space, you=you)
        else:
            return ">>{}{}".format(pid, space) # so it doesn't get read by any other filters
    r_imply = lambda match: implying.format(match.group(0))
    r_spoil = lambda match: spoiler.format(match.group(1))

    # currently, we're escaping the text, then regex substituting on to it
    # and using unescaped markup for substitutions, so it gets injected correctly
    # which is why the regex is hunting for &gt;&lt; instead of >< 

    post = escape(post) # HTML escaping, from werkzeug
    post = '\n'.join([re.sub('\s+', ' ', l.strip()) for l in post.splitlines()])
    post = re.sub(f_ref, r_ref, post)      # post-references must occur before imply (>>num)
    post = re.sub(f_spoil, r_spoil, post)  # spoiler must occur before imply (>< text ><)
    post = re.sub(f_imply, r_imply, post)  # since is looking for a subset  (>text)
    post = re.sub('\n', '\n<br>\n', post)

    return post, addrefs


@app.route('/<board>/upload', methods=['POST'])
def newthread(board):
    if 'image' not in request.files:
        return general_error('New threads must have an image')
    return _upload(board)

@app.route('/<board>/<int:thread>/upload', methods=['POST'])
def newpost(board, thread):
    return _upload(board, thread)

#@checktime
def _upload(board, threadid=None):
    """ handles the entire post upload process, and validation
        Args:
            board (str): board title for the new post
            threadid (Optional[id]): the id of the parent thread. None if this is a new thread.
        Returns:
            Redirects to the (new) thread
    """
    def allowed_file(filename):
        a = filename.rsplit('.', 1)[1] if '.' in filename else None
        b = a in ALLOWED_EXTENSIONS
        return a, b

    # read file and form data
    print("starting upload")
    image = request.files['image']
    print(type(image))
    print("got image")
    subject = request.form.get('title', default='', type=str).strip()  
    print(subject)
    email =   request.form.get('email', default='', type=str).strip() 
    print(email)
    name =    request.form.get('name' , default='', type=str).strip() 
    print(name)
    post =    request.form.get('body' , default='', type=str).strip() 
    print(post)
    sage =    request.form.get('sage' , default='', type=str).strip() 
    print(sage)

    if 'password' not in session: # I believe this will occur if cookies are being blocked
        assign_pass()
    password = session['password']
    if not sage:
        sage=False

    if (not post or post.isspace()) and not image:
        return general_error('Cannot have an empty post') 
    if not _validate_post(post):
        return general_error('Spam/Robot detected')
    if threadid and not db._is_thread(threadid):
        return general_error('Specified thread does not exist')
    if image:
        filetype, allowed = allowed_file(image.filename)
        if not allowed:
            return general_error('File not allowed')
        else:
            n = hashfile(image) # returns hex
            n = int(n[:16], 16) # more or less like 4chan
            image.filename= "%s.%s" % (n, filetype)
            image.mainpath = imgpath
            image.thumbpath = thumbpath
    # so it's a valid upload in all regards
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
    image.save(filepath)
    print("BEFORE")
    print("board", board)
    print("thread", threadid)
    if threadid: 
        pid = db.create_post(threadid, image.filename, post, password, name, email, subject, sage)
        session['myposts'].append(pid) # we don't care about owning threads
    else:
        threadid, pid = db.create_thread(board, image.filename, post, password, name, email, subject)
    print("AFTER")
    print("board", board)
    print("thread", threadid)
    return redirect(url_for('thread', board=board, thread=threadid))

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

def parse_threads(threads):
    """ reads the body text for each post, applies styling """
    ts = list()
    reflist = list()
    for thread in threads:
        t = list()
        for post in thread:
            p = dict(post.items())
            p['body'], addlist  = _parse_post(p['body'])
            p['h_time'] = _rel_timestamp(p['timestamp'])
            if addlist:
                reflist.append((p['id'], addlist))
            t.append(p)
        ts.append(t)
    if reflist:
        db.create_backrefs_for_thread(reflist)
    return ts 

@app.route('/<board>/<thread>/', methods=['GET'])
def thread(board, thread):
    if not db._is_thread(thread):
        return general_error('Specified thread does not exist')
    threads = [db.fetch_thread(thread)] # turned into a list, because the template operates on lists of threads
    board = db.fetch_board_data(board)
    threads = parse_threads(threads)
    return render_template('page.html', threads=threads, board=board)


@app.route('/', methods=['GET'])
def root():
    return redirect(url_for('index', board='v'))

@app.route('/<board>', methods=['GET'])
@app.route('/<board>/', methods=['GET'])
@app.route('/<board>/index.html', methods=['GET'])
def index(board):
    page = request.args.get('page', 0)
    try:
        page = int(page) # sqlalchemy autoconverts pagenum to int, but its probably based on auto-detection
    except TypeError:    # so we'll need to make sure it's actually an int; ie ?page=TOMFOOLERY
        page = 0

    threads = db.fetch_page(board, page)
    #if not threads:
    #    return e404()

    board = db.fetch_board_data(board)
    threads = parse_threads(threads)
    return render_template('page.html', threads=threads, board=board)

def general_error(error):
    return render_template('error.html', error_message=error)

@app.errorhandler(404)
def e404():
    return render_template('404.html'), 404

