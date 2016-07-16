import db2 as db
from config import cfg
import datetime
from flask import Flask, render_template, request
from flask import url_for, flash, redirect, session
from flask import send_from_directory, Markup 
from pprint import pprint
import random, string
import os

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
        session['lastclear'] = now
        for i, pid in enumerate(session['myposts']):
            if not _is_post(pid):
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
    image     = request.files['image']
    subject   = request.form.get('title', default= '', type= str).strip()
    email     = request.form.get('email', default= '', type= str).strip()
    name      = request.form.get('name' , default= '', type= str).strip()
    post      = request.form.get('body' , default= '', type= str).strip()
    sage      = request.form.get('sage' , default= '', type= str).strip()
    spoilered = request.form.get('spoilered', default= False, type= bool)

    files = dict()
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
            # files is whats actually being passed to the db
            files['filename'] = image.filename
            files['filetype'] = filetype
            files['spoilered'] = spoilered
    # so it's a valid upload in all regards
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
        image.save(filepath)
    parsed_body, reflist = db.parse_post(post) #  we should probaby save the parsed body instead of unparsed
    if threadid: 
        pid = db.create_post(threadid, [files], post, parsed_body, password, name, email, subject, sage)
    else:
        threadid, pid = db.create_thread(board, [files], post, parsed_body, password, name, email, subject)
    if reflist:
        db.create_backrefs((pid,reflist))
    db._check_backref_preexistence(pid) # check if this post was future-referenced, and reparse if neccessary
    session['myposts'].append(pid)
    session.modified = True # necessary to actually save the session change
    return redirect(url_for('thread', board=board, thread=threadid))

@app.route('/<board>/<thread>/', methods=['GET'])
def thread(board, thread):
    if not db._is_thread(thread):
        return general_error('Specified thread does not exist')
    threads = [db.fetch_thread(thread)] # turned into a list, because the template operates on lists of threads
    board = db.fetch_board_data(board)
    return render_template('page.html', threads=threads, board=board, isindex=False, counts=None)


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
    if page > cfg.index_max_pages:
        return e404(None)
    threads = db.fetch_page(board, page)

    board = db.fetch_board_data(board)
    counts = [ db.count_hidden(thread[0]['thread_id']) for thread in threads ]
    return render_template('page.html', threads=threads, board=board, isindex=True, counts=counts)

def general_error(error):
    return render_template('error.html', error_message=error)

@app.errorhandler(404)
def e404(e):
    return render_template('404.html'), 404

