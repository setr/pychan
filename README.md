# pychan
simple static-chan using python3 and sqlite

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
### REPLY FORM
Auto-resize textarea for inject-reply input: https://github.com/ro31337/jquery.ns-autogrow (JS)
    *This code seems to work well, but we'll need to add a max-width property because otherwise
    *it only has the options
        *Don't move horizontally at all
        *Move horizontally to infinite length
    *Which is fucking retarded
    ``` $('#trans').autogrow({max-width=900})```

Primary input form  (JINJA)
Actual POSTing of reply data (JINJA/PYTHON)
New Thread vs New Reply distinction (JINJA)

### IMAGES
Generate and link to thumbnails
Full image on hover (JS)
Inline expansion (JS)
Webm vs Image Inline Expansion (JS)
PDF should simply new-link (JS)

### BODY TEXT
Either move styling injection to client-side (JS)
Or save the parsed body-text to the db (PYTHON)

Move post-ownership from session cookie to unsigned cookie, so JS can unpack (PYTHON)
>>0123021 (you) (JS)

### CONVENIENCE
Auto-update threads (JS/AJAX)

### NON-FEATURES
A proper config file (PYTHON)
Move flask routing and helper functions into seperate files
Should probably split the DB functions into two files as well
Give files proper names (ie not testchan)

### MAYBE
Converter script from meguca-css to ours
add multi-image support (this seems like it'll be annoying to add) (SQL/PYTHON)
Floating reply box (JS)
Thread Watcher (JS/AJAX)
