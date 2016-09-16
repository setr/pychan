# pychan
simple static-chan using python3 and sqlite

Eventually it should feature:

* Image/Webm/PDF support
* Multi-image posting, per config option
* Inline expansion, Image Hover
* Standard chan things (anonymous posting, tripcodes, board-falloff, etc)
* Board-Specific Configuration
* basic CLI/Web-based administration 
* Support for Master/Slave DB configuration
* Sphinx-Generated Documentation
* Meguca-Compatible CSS
* Simple sideline script for installing alongside meguca
* Most importantly, a generally simple (or simplified) install and management process
* and of course, the codebase needs to be easy enough to build on, though its getting kind of messy already.

All Web handling is done through Flask/Werkzeug, and uses SQLAlchemy(core) for general SQL-DB independence. Though the most likely usecase **should** be SQLite. A pretty standard python web setup. Basic configs *will* be supplied for an Nginx webserver hosting this + meguca alongside each other.

Images are handled using ImageMagick. PDF-Thumbnailing is handled through Ghostscript (currently interfaced through imagemagick). Webms do not get thumbnailed, at least for now. If they are to be, it'll likely be through ffmpeg.

Currently there are no optional requirements. You **must** have imagemagick compiled with support for JPG, PNG, GIF, as well as ghostscript for PDF (and imagemagick needs to know where ghostscript lives.) I believe for most os's, this is the standard install of imagemagick.

I'm also making subprocess module calls (without shell=True) to run imagemagick. I'm not sure what python does with the strings outside of shell escaping, but I think it's safe to assume sh is a dependency.

Otherwise, at least for now, the only dependencies are python3, sqlite and any modules in the requirements.txt file.

So in total,

* ImageMagick
* Ghostscript
* Python3
* Sqlite3 (or any other SQL-DB supported by SqlAlchemy)
* FFMPEG (probably; not yet though)


```bash
virtualenv -p python3 testchan
source testchan/bin/activate.sh
pip3 install -r requirements.txt
export FLASK_APP=testchan.py
export FLASK_DEBUG=1
sqlite3 db1.sqlite
# python3 db_main.py # run this to generate some posts for testing
flask run
```

then go to localhost:5000


##TODO
### GENERAL FIXES
- [x] Thread/Index distinction isn't complete
       - May want to use template inheritance
       - Thread currently has [ 1 2 3 4 5 ] page numbers, where it should be options like [ expand all images ]
       - I believe this is mostly complete now, but using an annoying number of if-else clauses. not sustainable.
- [x] Index has [ New Reply ] buttons on each thread, that spawn a new thread on writing
       - Either this needs to reply to the thread, and then redirect to it
       - Or it needs to not exist, and only a [ New Thread ] button **Currently This**
- [x] Index needs to 404 if you try to go to a page that cannot exist (exceeds index_max_pages)
       - An empty page if pagenum is valid, but there simply aren't that many threads in existence (which it currently does)
- [x] [ New Thread ] runs on [ New Reply ] JS. Pretty sure I don't like this.
- [x] Deleting a post currently does not delete associated file(s), if any

### Styling
- [ ] Meguca header
       - [ ] the header itself + icons     
       - [ ] Meguca header options
       - [ ] banner image
- [ ] CSS theme switching
- [ ] Test Meguca CSS beyond ashita
- [ ] Need to make thread distinction more clear on index pages

### Client-Side Viewing
- [x] Hide posts (JS)
- [x] Hide threads (JS)
- [ ] Reverse Image search links
- [x] Delete Post option (with auto-gen'd pass check)
       - [x] with cookies
              - password field lives in the bottom right
              - stores password in client-cookie, plaintext
              - autogenerates if it doesn't exist
              - updates to user-supplied password if field is modified when post is submitted
       - [x] without
              - user-supplied password must be submitted every time, for deletion to work.
              - 'idc' becomes the default password if nothing is supplied. I may change this to a randomly generated value later.
- [ ] Nested inline reply-posts 
- [ ] Hover reply posts
- [ ] Hover menu-items

### REPLY FORM
- [x] Auto-resize textarea for inject-reply input: https://github.com/ro31337/jquery.ns-autogrow (JS)
       - if width, height isn't set on the text-area, this thing sets it to 0 which is fucking retarded 
- [ ] Primary input form  (JINJA)
- [ ] Actual POSTing of reply data (JINJA/PYTHON)
       - [x] body + file can POST 
       - [ ] additional fields can POST (name, sage, spoiler, etc)
              - [x] name
              - [x] email
              - [ ] sage
              - [ ] spoiler
              - [x] thread-title
- [x] New Thread vs New Reply distinction (JS)

### IMAGES
- [x] Filename on server => hash.filetype
- [x] Fail on duplicate file upload
- [ ] Generate and link to thumbnails
       - [x] image thumbnail
       - [x] webm thumbnail
       - [ ] spoiler thumbnail
       - [x] webms fail to load the second time they're expanded. I'm pretty sure this is flask's fault. **works fine on nginx**
       - [ ] PDFs usually have a generic thumbnail. It would be much more useful if I could read out the first page, convert it to an image, and generate a thumbnail off that.
              - I don't know why, but PDF thumbnail generation fails on server. Works fine on localhost, and when called using the Flask-server. 
- [ ] Full image on hover (JS)
       - Shouldn't apply to webms (it's annoying)
       - Shouldn't apply to PDFs
- [x] Inline expansion (JS)
       - [x] Image Inlined
       - [x] Webm Inlined
       - [x] PDF should not inline. Just target="_blank"
- [ ] Spoiler
       - thumbnail points to spoiler.jpg, and the flag in the db is there. No button to set it when posting though.
 

### BODY TEXT
- [x] Either move styling injection to client-side (JS) or save the parsed body-text to the db (PYTHON)
       -  Moved it to server side, storing both parsed and original text. Parses once on create, and if that thread future-referenced (replied to a post that does not yet exist), it reparses the post when that thread does exist.
       -  Can also probably add a cli function to reparse all posts, if you change up the regex or something.
- [ ] \>>0123021 (you) (JS)
       - [x] Move post-ownership from session cookie to unsigned cookie, so JS can unpack (PYTHON)
            - It turns out session objects are read-only client-side, which is sufficient
            - Currently this is implemented, but from python's parsing
            - I think this is going to either need board-specific cookies or something
       - [ ] Detect ownership and inject ::after

### User Functionality
- [ ] Auto-update threads (JS/AJAX)
- [x] sage
- [ ] tripcode
- [ ] gimmicks? (dice rolls and whatnot)
- [x] spoiler text
- [x] reply-links
- [x] replied-by links
- [x] >implying
- [ ] Youtube embed (JS)
       - probably want this to be in the image section

### MODS
- [x] Login check on specific pages
- [x] Store login success in session cookie
- [ ] An actual login page
- [ ] Administration page (clear bans, clear cache, etc)
- [ ] Banlist page
- [ ] Database access functions
- [ ] Limited Bans (ie 1 day, or on one board)
- [ ] Mod-options for index page

### CONFIGS
- [x] A proper config file (PYTHON)
       - completed in the form of a python class. May use configparser to have an ascii-based config, but probably not worth the effort
- [ ] Need board-specific configs (currently its global to the whole site)
    - Probably something like a nested dictionary
    - globals are at the top, and then you set specific ones, with the L1 dict being the boardname (ie 'v')
- [ ] Missing options I can think of now
    - [ ] Media support On/Off

### CODEBASE
- [ ] Move flask routing and helper functions into seperate files
- [x] DB needs to be split into an entry point file and helper functions
       - with the helper functions always consuming engine transaction objects
       - and the entry points always spawning them
- [ ] Give files proper names (ie not testchan)
- [ ] Write some actual fucking unit tests
- [x] _upload is getting way too complex; break it up and simplify conditional-routing

### DOCS
- [ ] Most of the functions have Napolean-Sphinx compatatible docstrings, but we still need to start generating them

### MAYBE
- [ ] Converter script from meguca-css to ours
       - in the form of loading meguca-css, then pasting ours on top
       - pychan-modified css in mycss.css
- [ ] Add multi-image support (this seems like it'll be annoying to add) (SQL/PYTHON)
       - I believe most of the support for this is now complete, with everything now assuming theres a list of files
       - However, I have no real idea how to add multi-image support on the frontend side, without declaring #id1 #id2 #id3 boxes, and then looking through all of them. Which is do-able, but seems pretty stupid. Ideally, it should just reach flask as a generic list of files to operate on. 
- [ ] Floating reply box (JS)
- [ ] Thread Watcher (JS/AJAX)
- [ ] Report
       - Currently nothing in DB to support that
       - But it's probably just an additional table. Just need to email right people or display it or something
