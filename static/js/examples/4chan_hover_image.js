/**
 * Image hover
 */
var ImageHover = {};

ImageHover.show = function(thumb) {
  var el, href, ext;
  
  if (thumb.nodeName !== 'A') {
    href = thumb.parentNode.getAttribute('href');
  }
  else {
    href = thumb.getAttribute('href');
  }
  
  if (ext = href.match(/\.(?:webm|pdf)$/)) {
    if (ext[0] == '.webm') {
       ImageHover.showWebm(thumb);
    }
    return;
  }
  
  el = document.createElement('img');
  el.id = 'image-hover';
  el.alt = 'Image';
  el.onerror = ImageHover.onLoadError;
  el.src = href;
  
  if (Config.imageHoverBg) {
    el.style.backgroundColor = 'inherit';
  }
  
  document.body.appendChild(el);
  
  if (UA.hasCORS) {
    el.style.display = 'none';
    this.timeout = ImageHover.checkLoadStart(el, thumb);
  }
  else {
    el.style.left = thumb.getBoundingClientRect().right + 10 + 'px';
  }
};

ImageHover.hide = function() {
  var img;
  
  clearTimeout(this.timeout);
  
  if (img = $.id('image-hover')) {
    if (img.play) {
      img.pause();
      Tip.hide();
    }
    document.body.removeChild(img);
  }
};

ImageHover.showWebm = function(thumb) {
  var el, bounds, limit;
  
  el = document.createElement('video');
  el.id = 'image-hover';
  
  if (Config.imageHoverBg) {
    el.style.backgroundColor = 'inherit';
  }
  
  if (thumb.nodeName !== 'A') {
    el.src = thumb.parentNode.getAttribute('href');
  }
  else {
    el.src = thumb.getAttribute('href');
  }
  
  el.loop = true;
  el.muted = !Config.unmuteWebm;
  el.autoplay = true;
  el.onerror = ImageHover.onLoadError;
  el.onloadedmetadata = function() { ImageHover.showWebMDuration(this, thumb); };
  
  bounds = thumb.getBoundingClientRect();
  limit = window.innerWidth - bounds.right - 20;
  
  el.style.maxWidth = limit + 'px';
  el.style.top = window.pageYOffset + 'px';
  
  document.body.appendChild(el);
  
  if (Config.unmuteWebm) {
    el.volume = 0.5;
  }
};

ImageHover.showWebMDuration = function(el, thumb) {
  if (!el.parentNode) {
    return;
  }
  
  var sound, ms = $.prettySeconds(el.duration);
  
  if (el.mozHasAudio === true
    || el.webkitAudioDecodedByteCount > 0
    || (el.audioTracks && el.audioTracks.length)) {
    sound = ' (audio)';
  }
  else {
    sound = '';
  }
  
  Tip.show(thumb, ms[0] + ':' + ('0' + ms[1]).slice(-2) + sound);
};

ImageHover.onLoadError = function() {
  Feedback.error('File no longer exists (404).', 2000);
};

ImageHover.onLoadStart = function(img, thumb) {
  var bounds, limit;
  
  bounds = thumb.getBoundingClientRect();
  limit = window.innerWidth - bounds.right - 20;
  
  if (img.naturalWidth > limit) {
    img.style.maxWidth = limit + 'px';
  }
  
  img.style.display = '';
  img.style.top = window.pageYOffset + 'px';
};

ImageHover.checkLoadStart = function(img, thumb) {
  if (img.naturalWidth) {
    ImageHover.onLoadStart(img, thumb);
  }
  else {
    return setTimeout(ImageHover.checkLoadStart, 15, img, thumb);
  }
};
