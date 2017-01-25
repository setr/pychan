import db_main as db
import config as cfg
import gen_helpers as gh
import errors as err

from flask import Flask, request, render_template
from flask import url_for, redirect, session
from flask_s3 import FlaskS3

import random
import string
import datetime

from functools import wraps

app = Flask(__name__)

# s3 options
app.config['FLASKS3_ACTIVE'] = cfg.aws
app.config['FLASKS3_BUCKET_NAME'] = cfg.S3_BUCKET
app.config['FLASKS3_BUCKET_DOMAIN'] = cfg.S3_BUCKET_DOMAIN
# app.config['AWS_ACCESS_KEY_ID'] = cfg.S3_ACCESS_KEY
# app.config['AWS_SECRET_ACCESS_KEY'] = cfg.S3_SECRET_KEY
s3 = FlaskS3(app)


app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.jinja_env.line_statement_prefix = '#'  # enables jinja2 line mode
app.jinja_env.line_comment_prefix = '##'  # enables jinja2 line mode

app.secret_key = 'Bd\xf2\x14\xbbi\x01Gq\xc6\x87\x10BVc\x9c\xa4\x08\xdbk%\xfa*\xe3'  # os.urandom(24)

# makes our config available to all jinja templates
app.add_template_global(cfg, 'cfg')
# @app.before_first_request
# def load_tables():
#     """ collects all the metadata as soon as the app boots up
#     well, only acts when the first request comes in but whatever"""
#     db._fetch_metadata(database)


@app.before_request
def assign_session_params():
    """ Makes sure the user has basic needs satisfied
        password: password to sign off posts with
        myposts: list of pids posted by the user
        update-myposts: at min once every two days, replace myposts with a
            list of postids that still exist in the db.
    """
    if 'password' not in session:
        allowed = string.ascii_letters + string.digits
        session['password'] = ''.join(random.choice(allowed) for i in range(24))
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
            mintime = cfg.minsec_between_posts
            if delta < datetime.timedelta(seconds=mintime):
                raise err.DNE('Please wait at least %s seconds before posting again' % (mintime,))
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
            raise err.Forbidden('You must be an admin to see this page') # proper would be 401 Unauthorized
    return go


def if_board_exists(fn):
    """ Decorator
    Only allow request to continue if the board in question actually exists
    The function must be consuming a variable called board
    It also injects the boardid into the argument
    """
    @wraps(fn)
    def go(*args, **kwargs):
        boardid = db.get_boardid(kwargs['boardname'])
        if not boardid:
            raise err.DNE('board does not exist')
        else:
            return fn(*args, boardid=boardid, **kwargs)
    return go


@app.route('/<boardname>/upload', methods=['POST'])
@if_board_exists
def newthread(boardname, boardid=None):
    threadid = request.form.get('threadid')
    if threadid:
        return redirect(url_for('newpost', boardname=boardname, thread=threadid, boardid=boardid))

    if 'image' not in request.files or request.files['image'].filename == '':
        raise err.BadInput('New threads must have an image')
    return _upload(boardname, boardid=boardid)


@app.route('/<boardname>/<int:threadid>/upload', methods=['POST'])
@if_board_exists
def newpost(boardname, threadid, boardid=None):
    if db.is_locked(threadid):
        raise err.PermDenied('Thread is locked')
    return _upload(boardname, threadid=threadid, boardid=boardid)


@app.route('/<boardname>/delete', methods=['POST'])
@if_board_exists
def delpost(boardname, boardid=None):

    # we're actually getting the global postid from the form this time
    postid = request.form.get('postid')
    password = request.form.get('password')
    url = request.form.get('url')

    ismod = 'mod' in session
    if db.is_thread(boardid, postid):
        files = db.fetch_files_thread(postid)
    else:
        files = db.fetch_files(postid)
    error = db.delete_post(postid, password, ismod)
    if error:
        raise err.PermDenied(error)

    for f in files:
        if not db.file_is_referenced(f['filename'], f['filetype']):
            try:
                gh.delete_file(f['filename'], f['filetype'])
            except OSError:
                # we searched aws, but the file was local, or vice versa, most likely.
                message = "The file could not be found"
                return render_template('error.html', error_message=message)
    return redirect(url)


# @checktime
def _upload(boardname, threadid=None, boardid=None):
    """ handles the entire post upload process, and validation
        Args:
            boardname (str): the name of the board
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
                     default='',
                     type=str).strip()
    password  = request.form.get('password',
                    default="idc",
                    type=str)
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    
    if email == "sage":
        sage = True

    if (not post or post.isspace()) and not image:
        raise err.BadInput('Cannot have an empty post') 
    if not gh._validate_post(post):
        raise err.PermDenied('Spam/Robot detected')
    if threadid and not db.is_thread(boardid, threadid):
        raise err.DNE('Specified thread does not exist')

    # and now we start saving the post
    isop = False if threadid else True
    # TODO for handling multiple images, this would be looping through all the images
    files = list()  # list of files to pass to db
    if image:
        basename, ext, filesize, resolution = gh.save_image(image, isop)

        filedict = {
        'filename'  : basename,
        'filetype'  : ext,
        'spoilered' : spoilered,
        'filesize'  : filesize,
        'resolution': resolution}
        files.append(filedict)

    if isop:
        # ops cannot be made saged by normal usage.
        threadid, pid, fpid = db.create_thread(boardid, files, post, password, name, email, subject, ip=ip)
    else:
        pid, fpid = db.create_post(boardid, threadid, files, post, password, name, email, subject, sage, ip=ip)

    # Special case: posts may >>pid posts that do not actually exist yet. 
    # If they reference the pid we _just_ created, then we'll have to 
    # reparse those old posts.

    # posts are marked dirty by default
    db.reparse_dirty_posts(boardname, boardid)
    return redirect(url_for('thread', boardname=boardname, thread=threadid, _anchor=fpid))


@app.route('/', methods=['GET'])
def root():
    return redirect(url_for('index', boardname='v'))  # TODO: Make a boardlist page.


@app.route('/<boardname>', methods=['GET'])
@app.route('/<boardname>/', methods=['GET'])
@app.route('/<boardname>/index.html', methods=['GET'])
@if_board_exists
def index(boardname, boardid=None):
    page = request.args.get('page', 0)
    try:
        page = int(page)  # sqlalchemy autoconverts pagenum to int, but its probably based on auto-detection
    except TypeError:     # so we'll need to make sure it's actually an int; ie ?page=TOMFOOLERY
        page = 0
    if page > cfg.index_max_pages:
        return err.e404()
    boarddata = db.fetch_boarddata(boardid)
    if not boarddata:
        raise err.DNE('board does not exist')
    threads = db.fetch_page(boardid, page)
    hidden_counts = [ db.count_hidden(thread[0]['thread_id']) for thread in threads ]
    page_count = db.count_pages(boardid)
    return render_template('board_index.html',
            threads=threads,
            board=boarddata,
            counts=hidden_counts,
            page_count=page_count)


@app.route('/<boardname>/<thread>/', methods=['GET'])
@if_board_exists
def thread(boardname, thread, boardid=None):
    if not db.is_thread(boardid, thread):
        raise err.DNE('Specified thread does not exist')
        # return general_error('Specified thread does not exist')
    thread_data = db.fetch_thread(boardid, thread)
    board_data = db.fetch_boarddata(boardid)
    return render_template('thread.html',
            thread=thread_data,
            board=board_data)

@app.errorhandler(err.BadInput)
def handle_permdenied(error):
    return render_template('error.html', error_message=error.message), 415

@app.errorhandler(err.e404)
def handle_permdenied(error):
    return render_template('error.html', error_message=error.message), 404

@app.errorhandler(err.BadMedia)
def handle_permdenied(error):
    return render_template('error.html', error_message=error.message), 415

@app.errorhandler(err.PermDenied)
def handle_permdenied(error):
    return render_template('error.html', error_message=error.message), 550 

@app.errorhandler(err.Forbidden)
def handle_Forbidden(error):
    return render_template('error.html', error_message=error.message), 403

@app.errorhandler(err.DNE)
def handle_DNE(error):
    return render_template('error.html', error_message=error.message), 404
