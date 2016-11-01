# this will be imported into all other modules
# and ofc, its python, so you use whatever logic you want
# but all modules will be assuming you haven't removed any
# variable from existence.

# They will also assume values are reasonable. ie, not -1 
# for index_posts_per_thread.

# I don't care to handle that kind of nonsense. And I don't plan
# to make this complex enough that you would struggle
# to handle it yourself.

debug = False 
# Master/Slave URIs, if replicating the DB.
# Master should handle writes, and any reads immediately following a write
# Only pure reads should use the slave.
master = "sqlite:////var/www/pychan.sqlite3"
slave  = None # if None, slave == master aka there is only one db.

# board configs
# currently, granularity is site-level. no board-specific configs.
# index_max_pages * index_threads_per_page = max threads for the board
index_threads_per_page = 10   # n threads per index page
index_posts_per_thread = 5    # latest m posts for thread; displayed on index pages
index_max_pages        = 10   # max number of pages the board-index will support
thread_max_posts       = 500  # threads with more than n posts can no longer be bumped
post_max_length        = 2000 # 4chan max post length, on /v/ at least

# should we allow multiple posts to use the same image? 
# if False, throw an error on re-upload. 
# if True: Posts share the same image-file, and the file is only deleted if all
# posts that reference it are deleted.
allow_same_image = True       

# thumbnail settings (in px)
op_thumb_max_height   = 250 
op_thumb_max_width    = 250
post_thumb_max_height = 125
post_thumb_max_width  = 125

# expanded settings
# these settings refuse to actually be applied, so they don't do anything atm
op_exp_max_height   = 500
op_exp_max_width    = 500
post_exp_max_height = 300
post_exp_max_width  = 300

## SPAM
detect_bot_on = False     # turn on spambot detection
minsec_between_posts = 30 # how many seconds between two posts?

imagemagick_formats = ['jpg', 'png', 'gif', 'jpeg', 'pdf'] # allowed image types; must be supported by imagemagick
ffmpeg_formats      = ['webm']                             # allowed video types; must be supported by ffmpeg

# ( short title, long title ) ==>  /short/ - long
# this is also used for initial board generation
boards = [ ('g', 'stem'),
           ('m', 'art & architecture') ]
# ( linkurl, name )
# this isn't autogenerated, to handle psuedoboards and such
# prints to the header in the same order as here.
boardlinks = [  ('a', 'http://hawk.eva.hk/a/'),
                ('g', 'http://hawk.eva.hk/g/'),
                ('m', 'http://hawk.eva.hk/m/') ]

# AWS Settings
aws = False # local img storage if False: S3 values won't be used.
S3_BUCKET = 'pychan' # s3 bucket; not used if aws = False
S3_BUCKET_DOMAIN = 's3.us-west-2.amazonaws.com'
S3_ACCESS_KEY = ''
S3_SECRET_KEY = ''

imgpath = 'static/src/imgs/'   ## where the full-size image is stored
thumbpath = 'static/src/thumb/' ## thumbnails (always jpg's)

themes = [
        'tea.css',
        'ashita.css'
        ]
