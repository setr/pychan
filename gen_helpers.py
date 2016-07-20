import subprocess
import hashlib

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



def _save_image(image, ext, mainpath, thumbpath, isop):
    image.save(mainpath) # first save the full image, unchanged

    h,w = (cfg.op_thumb_max_height, cfg.op_thumb_max_width) if isop \
     else (cfg.post_thumb_max_height, cfg.post_thumb_max_width)

    command = []
    if ext in cfg.imagemagick_formats:
        size = '{w}x{h}>' .format(w=w, h=h) # the > stops small images from being enlarged in imagemagick
        mainpath = mainpath + '[0]' # [0] gets page0 from the file. 
                                    # First frame of static image = the image.
        if ext == 'pdf':
                command = ['convert'      , mainpath ,
                            '-thumbnail'  , size     ,
                            '-background' , 'white'  ,
                            '-alpha'      , 'remove' ,
                            thumbpath]
        else:
            command = ['convert'     , mainpath ,
                        '-thumbnail' , size     ,
                        '-format'    , 'jpg'    ,
                        thumbpath]
    elif ext in cfg.ffmpeg_formats:
        # don't upscale
        # take the min scaling factor
        scale='scale=iw*min(1\\,min({w}/iw\\,{h}/ih)):-1'.format(w=w, h=h)
        command = ['ffmpeg',
                '-i'       , mainpath ,
                '-vframes' , '1'      ,
                '-vf'      , scale    ,
                thumbpath]
    # there should be no other valid exts
    subprocess.run(command)
