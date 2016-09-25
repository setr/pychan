import subprocess
import hashlib
import config as cfg
import os
import errors as err

import tinys3

# for AWS s3
import boto3
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
            os.remove(mainfile)
            os.remove(thumbfile)
        except OSError: ##TODO
            raise

def save_image(afile):
    ALLOWED_EXTENSIONS = cfg.imagemagick_formats + cfg.ffmpeg_formats

    f, e = os.path.splitext(afile.filename)
    ext = e[1:] # get rid of the . in the extension
    allowed = ext in ALLOWED_EXTENSIONS
    if not allowed:
        raise err.BadMedia('File not allowed')
    basename = hashfile(afile) # returns hex
    basename = str(int(basename[:16], 16)) # more or less like 4chan; 16char name
    newname = "%s.%s" % (basename, ext)
    # files is whats actually being passed to the db

    mainpath  = os.path.join(cfg.imgpath, newname)
    thumbpath = os.path.join(cfg.thumbpath, '%s.%s' % (basename, 'jpg'))
    if os.path.isfile(mainpath):
        raise err.BadInput('File already exists')

    if cfg.aws: # TODO lambda function will generate the thumbnail 
        s3 = boto3.resource('s3')
        s3.Object(cfg.S3_BUCKET, mainpath).put(Body=afile)
        # TODO stop doing this shit 
        # for now, we're being stupid as shit
        # locally saving the file, generating the thumbnail, uploading the thumb
        # and finally deleting both the local file and thumb 
        _local_save(afile, ext, mainpath, thumbpath, isop) # saves file, thumbnail to disk
        s3.Object(cfg.S3_BUCKET, mainpath).put(Body=open(thumbpath, 'rb'))
        try:
            os.remove(mainfile)
            os.remove(thumbfile)
        except OSError:
            pass
    else:
        _local_save(afile, ext, mainpath, thumbpath, isop) # saves file, thumbnail to disk

    return basename, ext

    
def _local_save(afile, ext, mainpath, thumbpath, isop):
    afile.save(mainpath) # first save the full image, unchanged

    h,w = (cfg.op_thumb_max_height, cfg.op_thumb_max_width) if isop \
     else (cfg.post_thumb_max_height, cfg.post_thumb_max_width)

    command = []
    if ext in cfg.imagemagick_formats:
        size = '{w}x{h}>' .format(w=w, h=h) # the > stops small images from being enlarged in imagemagick
        mainpath = mainpath + '[0]' # [0] gets page0 from the file. 
                                    # First frame of static image = the image.
        if ext == 'pdf':
            command = ['/usr/bin/convert'      , mainpath ,
            #command = ['convert'      , mainpath ,
                        '-thumbnail'  , size     ,
                        '-background' , 'white'  ,
                        '-alpha'      , 'remove' ,
                        thumbpath]
        else:
            command = ['/usr/bin/convert'      , mainpath ,
            #command = ['convert'     , mainpath ,
                        '-thumbnail' , size     ,
                        '-format'    , 'jpg'    ,
                        thumbpath]
    elif ext in cfg.ffmpeg_formats:
        # don't upscale
        # take the min scaling factor
        scale='scale=iw*min(1\\,min({w}/iw\\,{h}/ih)):-1'.format(w=w, h=h)
        command = ['/usr/bin/ffmpeg',
        #command = ['ffmpeg',
                '-i'       , mainpath ,
                '-vframes' , '1'      ,
                '-vf'      , scale    ,
                thumbpath]
    # there should be no other valid exts
    # we're assumming success
    subprocess.run(command)
