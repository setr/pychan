import subprocess
import hashlib
import config as cfg
import os
import errors as err
import json

import tinys3

# for AWS s3
import boto3
import botocore
boto3.setup_default_session(profile_name='pychan')

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

def delete_file(fname, fext):
    main = f['filename'] + '.' + f['filetype']
    thumb = f['filename'] + '.jpg'
    mainpath = os.path.join(cfg.imgpath , main)
    thumbpath = os.path.join(cfg.thumbpath, thumb)

    if aws:
        s3.Object(cfg.S3_BUCKET, mainpath).delete()
        s3.Object(cfg.S3_BUCKET, thumbpath).delete()
    else: # the file is stored locally, so we'll have to delete it there
        try:
            os.remove(mainpath)
            os.remove(thumbpath)
        except OSError: ##TODO
            raise

def save_image(afile, isop):
    ALLOWED_EXTENSIONS = cfg.imagemagick_formats + cfg.ffmpeg_formats

    f, e = os.path.splitext(afile.filename)
    ext = e[1:] # get rid of the . in the extension
    if not ext.lower() in ALLOWED_EXTENSIONS:
        raise err.BadMedia('File not allowed')

    basename = hashfile(afile) # returns hex
    basename = str(int(basename[:16], 16)) # more or less like 4chan; 16char name
    newname = "%s.%s" % (basename, ext)

    mainpath  = os.path.join(cfg.imgpath, newname)
    thumbpath = os.path.join(cfg.thumbpath, '%s.%s' % (basename, 'jpg'))
    # no need to save the file if it already exists.
    
    def s3_file_exists(s3, mainpath): # boto3 has no exists() func for whatever reason
        exists = True
        try:
            s3.Object(cfg.S3_BUCKET, mainpath).last_modified 
        except botocore.exceptions.ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                exists = False
        return exists

    if cfg.aws: # TODO lambda function will generate the thumbnail 
        s3 = boto3.resource('s3')
        if s3_file_exists(s3, mainpath) and not cfg.allow_same_image:
            raise err.BadInput('File already exists')
        # TODO stop doing this shit 
        # for now, we're being stupid as shit
        # locally saving the file, generating the thumbnail, uploading the thumb
        # and finally deleting both the local file and thumb 
        resolution = _local_save(afile, ext, mainpath, thumbpath, isop) # saves file, thumbnail to disk
        filesize = os.stat(mainpath).st_size 

        s3.Object(cfg.S3_BUCKET, mainpath).put(Body=open(mainpath, 'rb'))
        s3.Object(cfg.S3_BUCKET, thumbpath).put(Body=open(thumbpath, 'rb'))
        try:
            os.remove(mainpath)
            os.remove(thumbpath)
        except OSError:
            raise
    else:
        if os.path.isfile(mainpath) and not cfg.allow_same_image:
            raise err.BadInput('File already exists')
        resolution = _local_save(afile, ext, mainpath, thumbpath, isop) # saves file, thumbnail to disk
        filesize = os.stat(mainpath).st_size 
    filesize = human_filesize(filesize)
   
    return basename, ext, filesize, resolution

def human_filesize(size):
    from math import log2
    _suffixes = ['B', 'KB', 'MB', 'GB']
    order = int(log2(size) / 10) if size else 0
    return '{:.4g} {}'.format(size / (1 << (order * 10)), _suffixes[order])


    
def _local_save(afile, ext, mainpath, thumbpath, isop):
    afile.save(mainpath) # first save the full image, unchanged

    h,w = (cfg.op_thumb_max_height, cfg.op_thumb_max_width) if isop \
     else (cfg.post_thumb_max_height, cfg.post_thumb_max_width)

    if ext.lower() in cfg.imagemagick_formats:
        size = '{w}x{h}>' .format(w=w, h=h) # the > stops small images from being enlarged in imagemagick
        mainpath = mainpath + '[0]' # [0] gets page0 from the file. 
                                    # First frame of static image = the image.
        # for god knows what reason, thumbpath/mainpath need to be switched
        # for pdf vs img thumbnailing. weirdly, non-switched command works on cli just fine.
        if ext == 'pdf':
            save_command = ['/usr/bin/convert', mainpath,
            #command = ['convert'      , mainpath ,
                        '-thumbnail'  , size     ,
                        '-background' , 'white'  ,
                        '-alpha'      , 'remove' ,
                        thumbpath]
        else:
            save_command = ['/usr/bin/convert'      , mainpath ,
            #command = ['convert'     , mainpath ,
                        '-thumbnail' , size     ,
                        '-format'    , 'jpg'    ,
                        thumbpath]
        metadata_command = ['/usr/bin/identify',
                            '-format', '%[w]x%[h]',
                            mainpath]
        resolution = subprocess.check_output(metadata_command)
    elif ext.lower() in cfg.ffmpeg_formats:
        # don't upscale
        # take the min scaling factor
        scale='scale=iw*min(1\\,min({w}/iw\\,{h}/ih)):-1'.format(w=w, h=h)
        save_command = ['/usr/bin/ffmpeg',
        #command = ['ffmpeg',
                '-i'       , mainpath ,
                '-vframes' , '1'      ,
                '-vf'      , scale    ,
                thumbpath]
        metadata_command = ['/usr/bin/ffprobe',
                            '-v', 'error', 
                            '-show_entries', 'stream=width,height',
                            '-of', 'json',
                            mainpath]
        meta = subprocess.check_output(metadata_command)
        meta = json.decode(meta)
        width, height = meta['streams']['width'], meta['streams']['height']
        resolution = '{}x{}'.format(width, height)

    # there should be no other valid exts
    # we're assumming success
    subprocess.check_call(save_command)
    return resolution
