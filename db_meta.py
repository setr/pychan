import config as cfg
import sqlalchemy
from sqlalchemy import Table, Column, Integer, String, Text, Boolean, DateTime, MetaData, ForeignKey, UniqueConstraint
import datetime

class DB():
    engine   = None
    slave    = None
    metadata = None
    boards   = None
    backrefs = None
    threads  = None
    posts    = None
    mods     = None
    banlist  = None

    def __init__(self, maindb, slavedb=None, debug=False):
        self.engine   = sqlalchemy.create_engine(maindb, echo= debug)
        self.slave    = sqlalchemy.create_engine(slavedb) if slavedb else self.engine
        self.metadata = MetaData()

    def fetch_metadata(self):
        """ reads the schema to get metadata information, instead of using whats defined here """
        self.metadata.reflect(bind = self.engine)
        self.boards   = self.metadata.tables['boards']
        self.threads  = self.metadata.tables['threads']
        self.posts    = self.metadata.tables['posts']
        self.mods     = self.metadata.tables['mods']
        self.banlist  = self.metadata.tables['banlist']
        self.backrefs = self.metadata.tables['backrefs']

    def reset_db(self):
        """ drop all tables, create all tables. """
        self.metadata.drop_all(self.engine)
        self.metadata.create_all(self.engine)

    def create_db(self):
        """ create the full schema """
        cascade = {'onupdate': 'cascade', 'ondelete': 'cascade'}
        # unless otherwise commented, all string max-length values are picked with no real justification
        self.boards = Table('boards' , self.metadata,
                Column('id'          , Integer       , primary_key=True) ,
                Column('title'       , Text          , nullable=False, index=True, unique=True),
                Column('subtitle'    , Text          , nullable=False),
                Column('slogan'      , Text),
                Column('cur_pid'     , Integer       , nullable=False), # latest post_id for display purposes (posts.fake_id will use this + 1). autoincremented with new posts.
                Column('active'      , Boolean       , default=True))

        self.threads = Table('threads', self.metadata,
                Column('id'                 , Integer   , primary_key=True),
                Column('board_id'           , Integer   , ForeignKey("boards.id" , **cascade)),
                Column('op_id'              , Integer), #ForeignKey("posts.id" , **cascade)),
                Column('alive'              , Boolean   , default=True), # is it on autosage?
                Column('locked'             , Boolean   , default=False), # Mod-Locked?
                Column('sticky'             , Boolean   , default=True),
                UniqueConstraint('board_id' , 'op_id'))

        self.posts = Table('posts', self.metadata,
                Column('id'        , Integer,        primary_key=True), #sqlite_autoincrement=True) ,
                Column('fake_id'   , Integer), 
                Column('thread_id' , Integer,        ForeignKey("threads.id", **cascade)),
                Column('sage'      , Boolean),       
                Column('name'      , String(30)),
                Column('email'     , String(30)),
                Column('subject'   , String(50)),
                Column('body'      , String(cfg.post_max_length),  nullable=False),
                Column('parsed'    , Text),
                Column('ip_address', String(45)), # ipv4-mapped-ipv6 max length
                Column('dirty'     , Boolean,        default=True), # a dirty post references a non-existent post #
                Column('password'  , String(60),     nullable=False), # bcrypt output
                Column('timestamp' , DateTime,       default=datetime.datetime.utcnow))

        self.files = Table('files', self.metadata,
                Column('id', Integer, primary_key=True),
                Column('post_id', Integer, ForeignKey("posts.id", **cascade)),
                Column('filename', String(20), nullable=False), # size of the hash we're saving with
                Column('filetype', String(4), nullable=False),  # .pdf, .jpeg, etc
                Column('spoilered', Boolean, nullable=False),
                Column('filesize', String(20), nullable=False),   # 330 KB
                Column('resolution', String(20), nullable=False), # 250x457
                Column('clocktime', Integer, default=0))          # 6s

        self.backrefs = Table('backrefs', self.metadata,
                Column('id'   , Integer , primary_key=True)     ,
                Column('head' , Integer), # post being pointed to; 
                                          # doesn't need to currently exist (future-pointing)
                Column('tail' , Integer , ForeignKey("posts.id" , **cascade)) , # post doing the pointing
                UniqueConstraint('head' , 'tail'))
        self.mods = Table('mods', self.metadata,
                Column('id'       , Integer    , primary_key=True) ,
                Column('username' , String(30) , nullable=False)   ,
                Column('password' , String(60) , nullable=False)   , # bcrypt output
                Column('active'   , Boolean    , default=True))
        self.banlist = Table('banlist', self.metadata,
                Column('id'         , Integer      , primary_key=True),
                Column('ip_address' , String(45))  , # ipv4-mapped-ipv6 max length
                Column('reason'     , String(2000) , nullable=False),
                Column('mod_id'     , Integer      , ForeignKey("mods.id")),
                Column('board_id'   , Integer      , ForeignKey("boards.id"), nullable=True)) # if None , it's global ban
    def create_test_db(self):
        """ creates an in-memory sqlite db for testing """
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:")
        self.slave = self.engine
        self.metadata = Metadata()
        self.create_db()
        self.reset_db()


db = DB(cfg.master, cfg.slave, cfg.debug)
db.create_db()
