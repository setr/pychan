import db_main as db
import config as cfg
import gen_helpers as gh
from flask import Flask, request, render_template
from flask import url_for, flash, redirect, session
from flask import send_from_directory, Markup 
from pprint import pprint
import random, string
import os
import datetime

from functools import wraps
import hashlib

app = Flask(__name__)

imgpath = 'src/imgs/'
thumbpath = 'src/thumb/'

ALLOWED_EXTENSIONS = cfg.imagemagick_formats + cfg.ffmpeg_formats
#ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webm'])
app.config['UPLOAD_FOLDER'] = 'static/' + imgpath
app.config['THUMB_FOLDER'] = 'static/' + thumbpath
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['minsec_between_posts'] = 30
app.jinja_env.line_statement_prefix = '#' # enables jinja2 line mode
app.jinja_env.line_comment_prefix = '##' # enables jinja2 line mode

app.secret_key = 'Bd\xf2\x14\xbbi\x01Gq\xc6\x87\x10BVc\x9c\xa4\x08\xdbk%\xfa*\xe3' # os.urandom(24)

app.add_template_global(cfg, 'cfg') # makes our config available to all jinja templates 
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
        update-myposts: at min once every two days, replace myposts with a 
            list of postids that still exist in the db.
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
        session['myposts'] = db.fetch_updated_myposts(session['myposts'])
    return None

def checktime(fn):
    """ Decorator to make sure its been more than n time since last post """
    @wraps(fn)
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
    @wraps(fn)
    def go(*args, **kwargs):
        if 'mod' in session:
            return fn(*args, **kwargs)
        else:
            return general_error('You must be an admin to see this page'), # proper would be 401 Unauthorized
    return go

def if_board_exists(fn):
    """ Decorator
    Only allow request to continue if the board in question actually exists
    The function must be consuming a variable called board
    """
    @wraps(fn)
    def go(*args, **kwargs):
        boarddata = db.fetch_board_data(kwargs['board'])
        if not boarddata:
            return general_error('board does not exist')
        else:
            return fn(*args, **kwargs)
    return go

@app.route('/<board>/upload', methods=['POST'])
@if_board_exists
def newthread(board):
    if 'image' not in request.files or request.files['image'].filename == '':
        return general_error('New threads must have an image')
    return _upload(board)

@app.route('/<board>/<int:threadid>/upload', methods=['POST'])
@if_board_exists
def newpost(board, threadid):
    if db.is_locked(threadid):
        return general_error('Thread is locked')
    return _upload(board, threadid)

@app.route('/<board>/delete', methods=['POST'])
@if_board_exists
def delpost(board):
    fakeid = request.form.get('postid')
    password = request.form.get('password')
    url = request.form.get('url')

    ismod = 'mod' in session
    if db._is_thread(board, postid):
        files = db.fetch_files_thread(postid)
    else:
        files = db.fetch_files(postid)
    
    error = db.delete_post(board, postid, password, ismod)
    if error:
        return general_error(error)

    for f in files:
        try:
            main = f['filename'] + '.' + f['filetype']
            thumb = f['filename'] + '.jpg'
            mainfile = os.path.join(app.config['UPLOAD_FOLDER'], main)
            thumbfile = os.path.join(app.config['THUMB_FOLDER'], thumb)
            os.remove(mainfile)
            os.remove(thumbfile)
        except OSError:
            pass
    
    return redirect(url)

#@checktime
def _upload(board, threadid=None):
    """ handles the entire post upload process, and validation
        Args:
            board (str): board title for the new post
            threadid (Optional[id]): the id of the parent thread. None if this is a new thread.
        Returns:
            Redirects to the (new) thread
    """
    # read file and form data
    image     = request.files['image']
    subject   = request.form.get('subject'   , default= ''    , type= str).strip()
    email     = request.form.get('email'     , default= ''    , type= str).strip()
    post      = request.form.get('body'      , default= ''    , type= str).strip()
    sage      = request.form.get('sage'      , default= False , type= bool)
    spoilered = request.form.get('spoilered' , default= False , type= bool)
    name      = request.form.get('name',
                     default= '',
                     type= str).strip()
    password  = request.form.get('password',
                    default= "idc",
                    type= str)

    if (not post or post.isspace()) and not image:
        return general_error('Cannot have an empty post') 
    if not gh._validate_post(post):
        return general_error('Spam/Robot detected')
    if threadid and not db._is_thread(board, threadid):
        return general_error('Specified thread does not exist')

    # and now we start saving the post
    isop = False if threadid else True
    # in the future, for handling multiple images, this would be looping through all the images
    files = list()
    if image:
        f, e = os.path.splitext(image.filename)
        ext = e[1:] # get rid of the . in the extension
        allowed = ext in ALLOWED_EXTENSIONS
        if not allowed:
            return general_error('File not allowed')
        basename = gh.hashfile(image) # returns hex
        basename = str(int(basename[:16], 16)) # more or less like 4chan
        newname = "%s.%s" % (basename, ext) 
        # files is whats actually being passed to the db
        mainpath  = os.path.join(app.config['UPLOAD_FOLDER'], newname)
        thumbpath = os.path.join(app.config['THUMB_FOLDER'], '%s.%s' % (basename, 'jpg'))

        if os.path.isfile(mainpath):
            return general_error('File already exists')
            err = 'File already exists'
        newbasename = gh._save_image(image, ext, mainpath, thumbpath, isop) # saves file, thumbnail to disk
        filedict = {
        'filename'  : basename,
        'filetype'  : ext,
        'spoilered' : spoilered}
        files.append(filedict)

    # drop it into the DB
    #parsed_body, reflist = db.parse_post(board, post)
    if isop: 
        threadid, pid, fpid = db.create_thread(board, files, post, password, name, email, subject)
    else:
        pid, fpid = db.create_post(board, threadid, files, post, password, name, email, subject, sage)

    # Special case: posts may >>pid posts that do not actually exist yet. 
    # If they reference the pid we _just_ created, then we'll have to 
    # reparse those old posts.
    db.mark_dirtyclean(pid, True) # assume dirty unless proven clean
    db.reparse_dirty_posts(board, pid, fpid)

    return redirect(url_for('thread', board=board, thread=threadid, _anchor=fpid))


@app.route('/', methods=['GET'])
def root():
    return redirect(url_for('index', board='v')) # TODO: Make a boardlist page.

@app.route('/<board>', methods=['GET'])
@app.route('/<board>/', methods=['GET'])
@app.route('/<board>/index.html', methods=['GET'])
@if_board_exists
def index(board):
    page = request.args.get('page', 0)
    try:
        page = int(page) # sqlalchemy autoconverts pagenum to int, but its probably based on auto-detection
    except TypeError:    # so we'll need to make sure it's actually an int; ie ?page=TOMFOOLERY
        page = 0
    if page > cfg.index_max_pages:
        return e404(None)
    
    boarddata = db.fetch_board_data(board)
    if not boarddata:
        return general_error('board does not exist')

    threads = db.fetch_page(board, page)
    hidden_counts = [ db.count_hidden(thread[0]['thread_id']) for thread in threads ]
    return render_template('board_index.html',
            threads=threads,
            board=boarddata,
            counts=hidden_counts)

@app.route('/<board>/<thread>/', methods=['GET'])
@if_board_exists
def thread(board, thread):
    if not db._is_thread(board, thread):
        return general_error('Specified thread does not exist')
    thread_data = db.fetch_thread(board, thread)
    board_data = db.fetch_board_data(board)
    return render_template('thread.html',
            thread=thread_data,
            board=board_data)

def general_error(error):
    return render_template('error.html', error_message=error)

@app.errorhandler(404)
def e404(e):
    return render_template('404.html'), 404

