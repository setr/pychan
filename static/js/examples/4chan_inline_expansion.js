/**
 * Image expansion
 */
var ImageExpansion = {
  activeVideos: [],
  timeout: null
};

ImageExpansion.expand = function(thumb) {
  var img, href, ext;
  
  if (Config.imageHover) {
    ImageHover.hide();
  }
  
  href = thumb.parentNode.getAttribute('href');
  
  if (ext = href.match(/\.(?:webm|pdf)$/)) {
    if (ext[0] == '.webm') {
      return ImageExpansion.expandWebm(thumb);
    }
    return false;
  }
  
  thumb.setAttribute('data-expanding', '1');
  
  img = document.createElement('img');
  img.alt = 'Image';
  img.setAttribute('src', href);
  img.className = 'expanded-thumb';
  img.style.display = 'none';
  img.onerror = this.onError;
  
  thumb.parentNode.insertBefore(img, thumb.nextElementSibling);
  
  if (UA.hasCORS) {
    thumb.style.opacity = '0.75';
    this.timeout = this.checkLoadStart(img, thumb);
  }
  else {
    this.onLoadStart(img, thumb);
  }
  
  return true;
};

ImageExpansion.contract = function(img) {
  var cnt, p;
  
  clearTimeout(this.timeout);
  
  p = img.parentNode;
  cnt = p.parentNode.parentNode;
  
  $.removeClass(p.parentNode, 'image-expanded');
  
  if (Config.centeredThreads) {
    $.removeClass(cnt.parentNode, 'centre-exp');
    cnt.parentNode.style.marginLeft = '';
  }
  
  if (!Main.tid && Config.threadHiding) {
    $.removeClass(p, 'image-expanded-anti');
  }
  
  p.firstChild.style.display = '';
  
  p.removeChild(img);
  
  if (cnt.offsetTop < window.pageYOffset) {
    cnt.scrollIntoView();
  }
};

ImageExpansion.toggle = function(t) {
  if (t.hasAttribute('data-md5')) {
    if (!t.hasAttribute('data-expanding')) {
      return ImageExpansion.expand(t);
    }
  }
  else {
    ImageExpansion.contract(t);
  }
  
  return true;
};

ImageExpansion.expandWebm = function(thumb) {
  var el, link, fileText, left, href, maxWidth, self;
  
  if (Main.hasMobileLayout && /iPhone|iPad|iPod/.test(navigator.userAgent)) {
    return false;
  }
  
  self = ImageExpansion;
  
  if (el = document.getElementById('image-hover')) {
    document.body.removeChild(el);
  }
  
  link = thumb.parentNode;
  
  href = link.getAttribute('href');
  
  left = link.getBoundingClientRect().left;
  maxWidth = document.documentElement.clientWidth - left - 25;
  
  el = document.createElement('video');
  el.muted = !Config.unmuteWebm;
  el.controls = true;
  el.loop = true;
  el.autoplay = true;
  el.className = 'expandedWebm';
  el.onloadedmetadata = ImageExpansion.fitWebm;
  el.onplay = ImageExpansion.onWebmPlay;
  
  link.style.display = 'none';
  link.parentNode.appendChild(el);
  
  el.src = href;
  
  if (Config.unmuteWebm) {
    el.volume = 0.5;
  }
  
  if (Main.hasMobileLayout) {
    el = document.createElement('div');
    el.className = 'collapseWebm';
    el.innerHTML = '<span class="button">Close</span>';
    link.parentNode.appendChild(el);
  }
  else {
    fileText = thumb.parentNode.previousElementSibling;
    el = document.createElement('span');
    el.className = 'collapseWebm';
    el.innerHTML = '-[<a href="#">Close</a>]';
    fileText.appendChild(el);
  }
  
  el.firstElementChild.addEventListener('click', self.collapseWebm, false);
  
  return true;
};

ImageExpansion.fitWebm = function() {
  var imgWidth, imgHeight, maxWidth, maxHeight, ratio, left, cntEl,
    centerWidth, ofs;
  
  if (Config.centeredThreads) {
    centerWidth = $.cls('opContainer')[0].offsetWidth;
    cntEl = this.parentNode.parentNode.parentNode;
    $.addClass(cntEl, 'centre-exp');
  }
  
  left = this.getBoundingClientRect().left;
  
  maxWidth = document.documentElement.clientWidth - left - 25;
  maxHeight = document.documentElement.clientHeight;
  
  imgWidth = this.videoWidth;
  imgHeight = this.videoHeight;
  
  if (imgWidth > maxWidth) {
    ratio = maxWidth / imgWidth;
    imgWidth = maxWidth;
    imgHeight = imgHeight * ratio;
  }
  
  if (Config.fitToScreenExpansion && imgHeight > maxHeight) {
    ratio = maxHeight / imgHeight;
    imgHeight = maxHeight;
    imgWidth = imgWidth * ratio;
  }
  
  this.style.maxWidth = (0 | imgWidth) + 'px';
  this.style.maxHeight = (0 | imgHeight) + 'px';
  
  if (Config.centeredThreads) {
    left = this.getBoundingClientRect().left;
    ofs = this.offsetWidth + left * 2;
    if (ofs > centerWidth) {
      left = Math.floor(($.docEl.clientWidth - ofs) / 2);
      
      if (left > 0) {
        cntEl.style.marginLeft = left + 'px';
      }
    }
    else {
      $.removeClass(cntEl, 'centre-exp');
    }
  }
};

ImageExpansion.onWebmPlay = function() {
  var self = ImageExpansion;
  
  if (!self.activeVideos.length) {
    document.addEventListener('scroll', self.onScroll, false);
  }
  
  self.activeVideos.push(this);
};

ImageExpansion.collapseWebm = function(e) {
  var cnt, el, el2;
  
  e.preventDefault();
  
  this.removeEventListener('click', ImageExpansion.collapseWebm, false);
  
  cnt = this.parentNode;
  
  if (Main.hasMobileLayout) {
    el = cnt.previousElementSibling;
  }
  else {
    el = cnt.parentNode.parentNode.getElementsByClassName('expandedWebm')[0];
  }
  
  el.pause();
  
  if (Config.centeredThreads) {
    el2 = el.parentNode.parentNode.parentNode;
    $.removeClass(el2, 'centre-exp');
    el2.style.marginLeft = '';
  }
  
  el.previousElementSibling.style.display = '';
  el.parentNode.removeChild(el);
  cnt.parentNode.removeChild(cnt);
};

ImageExpansion.onScroll = function() {
  clearTimeout(ImageExpansion.timeout);
  ImageExpansion.timeout = setTimeout(ImageExpansion.pauseVideos, 500);
};

ImageExpansion.pauseVideos = function() {
  var self, i, el, pos, min, max, nodes;
  
  self = ImageExpansion;
  
  nodes = [];
  min = window.pageYOffset;
  max = window.pageYOffset + $.docEl.clientHeight;
  
  for (i = 0; el = self.activeVideos[i]; ++i) {
    pos = el.getBoundingClientRect();
    if (pos.top + window.pageYOffset > max || pos.bottom + window.pageYOffset < min) {
      el.pause();
    }
    else if (!el.paused){
      nodes.push(el);
    }
  }
  
  if (!nodes.length) {
    document.removeEventListener('scroll', self.onScroll, false);
  }
  
  self.activeVideos = nodes;
};

ImageExpansion.onError = function(e) {
  var thumb, img;
  
  Feedback.error('File no longer exists (404).', 2000);
  
  img = e.target;
  thumb = $.qs('img[data-expanding]', img.parentNode);
  
  img.parentNode.removeChild(img);
  thumb.style.opacity = '';
  thumb.removeAttribute('data-expanding');
};

ImageExpansion.onLoadStart = function(img, thumb) {
  var imgWidth, imgHeight, maxWidth, maxHeight, ratio, left, fileEl, cntEl,
    centerWidth, ofs, el;
  
  thumb.removeAttribute('data-expanding');
  
  fileEl = thumb.parentNode.parentNode;
  
  if (Config.centeredThreads) {
    cntEl = fileEl.parentNode.parentNode;
    centerWidth = $.cls('opContainer')[0].offsetWidth;
    $.addClass(cntEl, 'centre-exp');
  }
  
  left = thumb.getBoundingClientRect().left;
  
  maxWidth = $.docEl.clientWidth - left - 25;
  maxHeight = $.docEl.clientHeight;
  
  imgWidth = img.naturalWidth;
  imgHeight = img.naturalHeight;
  
  if (imgWidth > maxWidth) {
    ratio = maxWidth / imgWidth;
    imgWidth = maxWidth;
    imgHeight = imgHeight * ratio;
  }
  
  if (Config.fitToScreenExpansion && imgHeight > maxHeight) {
    ratio = maxHeight / imgHeight;
    imgHeight = maxHeight;
    imgWidth = imgWidth * ratio;
  }
  
  img.style.maxWidth = imgWidth + 'px';
  img.style.maxHeight = imgHeight + 'px';
  
  $.addClass(fileEl, 'image-expanded');
  
  if (!Main.tid && Config.threadHiding) {
    $.addClass(thumb.parentNode, 'image-expanded-anti');
  }
  
  img.style.display = '';
  thumb.style.display = 'none';
  
  if (Config.centeredThreads) {
    left = img.getBoundingClientRect().left;
    ofs = img.offsetWidth + left * 2;
    if (ofs > centerWidth) {
      left = Math.floor(($.docEl.clientWidth - ofs) / 2);
      
      if (left > 0) {
        cntEl.style.marginLeft = left + 'px';
      }
    }
    else {
      $.removeClass(cntEl, 'centre-exp');
    }
  }
  else if (Main.hasMobileLayout) {
    cntEl = thumb.parentNode.lastElementChild;
    if (!cntEl.firstElementChild) {
      fileEl = document.createElement('div');
      fileEl.className = 'mFileName';
      if (el = thumb.parentNode.parentNode.getElementsByClassName('fileText')[0]) {
        el = el.firstElementChild;
        fileEl.innerHTML = el.getAttribute('title') || el.innerHTML;
      }
      cntEl.insertBefore(fileEl, cntEl.firstChild);
    }
  }
};

ImageExpansion.checkLoadStart = function(img, thumb) {
  if (img.naturalWidth) {
    ImageExpansion.onLoadStart(img, thumb);
    thumb.style.opacity = '';
  }
  else {
    return setTimeout(ImageExpansion.checkLoadStart, 15, img, thumb);
  }
};



