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

Otherwise, at least for now, the only dependencies are python3, sqlite and any modules requirements.txt file.

```
virtualenv -p python3 testchan
source testchan/bin/activate.sh
pip3 install -r requirements.txt
export FLASK_APP=testchan.py
export FLASK_DEBUG=1
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
- [ ] [ New Thread ] runs on [ New Reply ] JS. Pretty sure I don't like this.
- [ ] Deleting a post currently does not delete associated file(s), if any

### Client-Side Viewing
- [ ] Hide posts (JS)
- [ ] Hide threads (JS)
- [ ] Reverse Image search links
- [ ] Delete Post option (with auto-gen'd pass check)
       - Should probably add the ability to set your own pass, if you refuse allow cookies
       - But then you'll have to set the pass on every post you write, and enter it on delete, since obviously I can no longer store the password anywhere to autofill it for you. Dunno if anyone will ever use that functionality.
- [ ] Nested inline reply-posts 
- [ ] Hover reply posts

### REPLY FORM
- [x] Auto-resize textarea for inject-reply input: https://github.com/ro31337/jquery.ns-autogrow (JS)
       - if width, height isn't set on the text-area, this thing sets it to 0 which is fucking retarded 
- [ ] Primary input form  (JINJA)
- [ ] Actual POSTing of reply data (JINJA/PYTHON)
       - [x] body + file can POST 
       - [ ] additional fields can POST (name, sage, spoiler, etc)
- [x] New Thread vs New Reply distinction (JINJA)

### IMAGES
- [x] Filename on server => hash.filetype
- [ ] Fail on duplicate file upload
- [ ] Generate and link to thumbnails
       - Need to look into this. Might be complex for getting them out of webms
       - PDFs usually have a generic thumbnail. It would be much more useful if I could read out the first page, convert it to an image, and generate a thumbnail off that.
- [ ] Full image on hover (JS)
       - Shouldn't apply to webms (it's annoying)
       - Shouldn't apply to PDFs
- [ ] Inline expansion (JS)
       - [ ] Image Inlined
       - [ ] Webm Inlined
       - [ ] PDF should not inline. Just target="_blank"
- [ ] Spoiler

### BODY TEXT
- [x] Either move styling injection to client-side (JS)
       -  Or save the parsed body-text to the db (PYTHON)
       -  Moved it to server side, storing both parsed and original text. Parses once on create, and if that thread future-referenced (replied to a post that does not yet exist), it reparses the post when that thread does exist.
       -  Can also probably add a cli function to reparse all posts, if you change up the regex or something.
- [ ] \>>0123021 (you) (JS)
       - [ ] Move post-ownership from session cookie to unsigned cookie, so JS can unpack (PYTHON)
            - It turns out session objects are read-only client-side, which is sufficient
            - Currently this is implemented, but from python's parsing
       - [ ] Detect ownership and inject ::after

### CONVENIENCE
- [ ] Auto-update threads (JS/AJAX)

### MODS
- [x] Login check on specific page
- [x] Store login success in session cookie
- [ ] An actual login page
- [ ] Administration page (clear bans, clear cache, etc)
- [ ] Banlist page
- [ ] Database access functions
- [ ] Limited Bans (ie 1 day, or on one board)
- [ ] Mod-options for index page

### CODEBASE
- [x] A proper config file (PYTHON)
       - completed in the form of a python class. May use configparser to have an ascii-based config, but probably not worth the effort
- [ ] Move flask routing and helper functions into seperate files
- [x] DB needs to be split into an entry point file and helper functions
       - with the helper functions always consuming engine transaction objects
       - and the entry points always spawning them
- [ ] Give files proper names (ie not testchan)
- [ ] Write some actual fucking unit tests

### MAYBE
- [ ] Converter script from meguca-css to ours
- [ ] Add multi-image support (this seems like it'll be annoying to add) (SQL/PYTHON)
       - I believe most of the support for this is now complete, with everything now assuming theres a list of files
       - However, I have no real idea how to add multi-image support on the frontend side, without declaring #id1 #id2 #id3 boxes, and then looking through all of them. Which is do-able, but seems pretty stupid. Ideally, it should just reach flask as a list of files to operate on. 
- [ ] Floating reply box (JS)
- [ ] Thread Watcher (JS/AJAX)
- [ ] Report
       - Currently nothing in DB to support that
       - But it's probably just an additional table
