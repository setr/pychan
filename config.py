# this will be imported into all other modules
# and ofc, its python, so you use whatever logic you want
# but all modules will be assuming you haven't removed any
# variable from existence.

# They will also assume values are reasonable. ie, not -1 
# for index_posts_per_thread.

# I don't care to handle that kind of nonsense. And I don't plan
# to make this complex enough that you would struggle
# to handle it yourself.

class Config():
    debug = False 
    # Master/Slave URIs, if replicating the DB.
    # Master should handle writes, and any reads immediately following a write
    # Only pure reads should use the slave.
    master = "sqlite:///db1.sqlite"
    slave  = None # if None, slave == master aka there is only one db.

    # board configs
    # currently, granularity is site-level. no board-specific configs.
    # index_max_pages * index_threads_per_page = max threads for the board
    index_threads_per_page = 10   # n threads per index page
    index_posts_per_thread = 5    # latest n posts for thread; displayed on index pages
    index_max_pages        = 10   # max number of pages the board-index will support
    thread_max_posts       = 500  # threads with more than n posts can no longer be bumped
    post_max_length        = 2000 # 4chan max post length, on /v/ at least

    # thumbnail settings
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

    imagemagick_formats = ['jpg', 'png', 'gif', 'jpeg'] # allowed image types; must be supported by imagemagick
    ffmpeg_formats      = ['webm']                           # allowed video types; must be supported by ffmpeg
    

cfg = Config() # don't touch this you fuck

