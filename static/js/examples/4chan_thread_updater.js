/**
 * Thread updater
 */
var ThreadUpdater = {};

ThreadUpdater.init = function() {
  if (!UA.hasCORS) {
    return;
  }
  
  this.enabled = true;
  
  this.pageTitle = document.title;
  
  this.unreadCount = 0;
  this.auto = this.hadAuto = false;
  
  this.delayId = 0;
  this.delayIdHidden = 4;
  this.delayRange = [ 10, 15, 20, 30, 60, 90, 120, 180, 240, 300 ];
  this.timeLeft = 0;
  this.interval = null;
  
  this.lastModified = '0';
  this.lastReply = null;
  
  this.currentIcon = null;
  this.iconPath = '//s.4cdn.org/image/';
  this.iconNode = $.qs('link[rel="shortcut icon"]', document.head);
  this.iconNode.type = 'image/x-icon';
  this.defaultIcon = this.iconNode.getAttribute('href').replace(this.iconPath, '');
  
  this.deletionQueue = {};
  
  if (Config.updaterSound) {
    this.audioEnabled = false;
    this.audio = document.createElement('audio');
    this.audio.src = '//s.4cdn.org/media/beep.ogg';
  }
  
  this.hidden = 'hidden';
  this.visibilitychange = 'visibilitychange';
  
  this.adRefreshDelay = 1000;
  this.adDebounce = 0;
  this.ads = {};
  
  if (typeof document.hidden === 'undefined') {
    if ('mozHidden' in document) {
      this.hidden = 'mozHidden';
      this.visibilitychange = 'mozvisibilitychange';
    }
    else if ('webkitHidden' in document) {
      this.hidden = 'webkitHidden';
      this.visibilitychange = 'webkitvisibilitychange';
    }
    else if ('msHidden' in document) {
      this.hidden = 'msHidden';
      this.visibilitychange = 'msvisibilitychange';
    }
  }
  
  this.initAds();
  this.initControls();
  
  document.addEventListener('scroll', this.onScroll, false);
  
  if (Config.alwaysAutoUpdate || sessionStorage.getItem('4chan-auto-' + Main.tid)) {
    this.start();
  }
};

ThreadUpdater.buildMobileControl = function(el, bottom) {
  var wrap, cnt, ctrl, cb, label, oldBtn, btn;
  
  bottom = (bottom ? 'Bot' : '');
  
  wrap = document.createElement('div');
  wrap.className = 'btn-row';
  
  // Update button
  oldBtn = el.parentNode;
  
  btn = oldBtn.cloneNode(true);
  btn.innerHTML = '<label data-cmd="update">Update</label>';
  
  wrap.appendChild(btn);
  cnt = el.parentNode.parentNode;
  ctrl = document.createElement('span');
  ctrl.className = 'mobileib button';
  
  // Auto checkbox
  label = document.createElement('label');
  cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.setAttribute('data-cmd', 'auto');
  this['autoNode' + bottom] = cb;
  label.appendChild(cb);
  label.appendChild(document.createTextNode('Auto'));
  ctrl.appendChild(label);
  wrap.appendChild(document.createTextNode(' '));
  wrap.appendChild(ctrl);
  
  // Status label
  label = document.createElement('div');
  label.className = 'mobile-tu-status';
  
  wrap.appendChild(this['statusNode' + bottom] = label);
  
  cnt.appendChild(wrap);
  
  // Remove Update button
  oldBtn.parentNode.removeChild(oldBtn);
  
  if (cnt = $.id('mpostform')) {
    cnt.parentNode.style.marginTop = '';
  }
};

ThreadUpdater.buildDesktopControl = function(bottom) {
  var frag, el, label, navlinks;
  
  bottom = (bottom ? 'Bot' : '');
  
  frag = document.createDocumentFragment();
  
  // Update button
  frag.appendChild(document.createTextNode(' ['));
  el = document.createElement('a');
  el.href = '';
  el.textContent = 'Update';
  el.setAttribute('data-cmd', 'update');
  frag.appendChild(el);
  frag.appendChild(document.createTextNode(']'));
  
  // Auto checkbox
  frag.appendChild(document.createTextNode(' ['));
  label = document.createElement('label');
  el = document.createElement('input');
  el.type = 'checkbox';
  el.title = 'Fetch new replies automatically';
  el.setAttribute('data-cmd', 'auto');
  this['autoNode' + bottom] = el;
  label.appendChild(el);
  label.appendChild(document.createTextNode('Auto'));
  frag.appendChild(label);
  frag.appendChild(document.createTextNode('] '));
  
  if (Config.updaterSound) {
    // Sound checkbox
    frag.appendChild(document.createTextNode(' ['));
    label = document.createElement('label');
    el = document.createElement('input');
    el.type = 'checkbox';
    el.title = 'Play a sound on new replies to your posts';
    el.setAttribute('data-cmd', 'sound');
    this['soundNode' + bottom] = el;
    label.appendChild(el);
    label.appendChild(document.createTextNode('Sound'));
    frag.appendChild(label);
    frag.appendChild(document.createTextNode('] '));
  }
  
  // Status label
  frag.appendChild(
    this['statusNode' + bottom] = document.createElement('span')
  );
  
  if (bottom) {
    navlinks = $.cls('navLinks' + bottom)[0];
  }
  else {
    navlinks = $.cls('navLinks')[1];
  }
  
  if (navlinks) {
    navlinks.appendChild(frag);
  }
};

ThreadUpdater.initControls = function() {
  // Mobile
  if (Main.hasMobileLayout) {
    this.buildMobileControl($.id('refresh_top'));
    this.buildMobileControl($.id('refresh_bottom'), true);
  }
  // Desktop
  else {
    this.buildDesktopControl();
    this.buildDesktopControl(true);
  }
};

ThreadUpdater.start = function() {
  this.auto = this.hadAuto = true;
  this.autoNode.checked = this.autoNodeBot.checked = true;
  this.force = this.updating = false;
  this.lastUpdated = Date.now();
  if (this.hidden) {
    document.addEventListener(this.visibilitychange,
      this.onVisibilityChange, false);
  }
  this.delayId = 0;
  this.timeLeft = this.delayRange[0];
  this.pulse();
  sessionStorage.setItem('4chan-auto-' + Main.tid, 1);
};

ThreadUpdater.stop = function(manual) {
  clearTimeout(this.interval);
  this.auto = this.updating = this.force = false;
  this.autoNode.checked = this.autoNodeBot.checked = false;
  if (this.hidden) {
    document.removeEventListener(this.visibilitychange,
      this.onVisibilityChange, false);
  }
  if (manual) {
    this.setStatus('');
    this.setIcon(null);
  }
  sessionStorage.removeItem('4chan-auto-' + Main.tid);
};

ThreadUpdater.pulse = function() {
  var self = ThreadUpdater;
  
  if (self.timeLeft === 0) {
    self.update();
  }
  else {
    self.setStatus(self.timeLeft--);
    self.interval = setTimeout(self.pulse, 1000);
  }
};

ThreadUpdater.adjustDelay = function(postCount)
{
  if (postCount === 0) {
    if (!this.force) {
      if (this.delayId < this.delayRange.length - 1) {
        ++this.delayId;
      }
    }
  }
  else {
    this.delayId = document[this.hidden] ? this.delayIdHidden : 0;
  }
  this.timeLeft = this.delayRange[this.delayId];
  if (this.auto) {
    this.pulse();
  }
};

ThreadUpdater.onVisibilityChange = function() {
  var self = ThreadUpdater;
  
  if (document[self.hidden] && self.delayId < self.delayIdHidden) {
    self.delayId = self.delayIdHidden;
  }
  else {
    self.delayId = 0;
    self.refreshAds();
  }
  
  self.timeLeft = self.delayRange[0];
  self.lastUpdated = Date.now();
  clearTimeout(self.interval);
  self.pulse();
};

ThreadUpdater.onScroll = function() {
  if (ThreadUpdater.hadAuto &&
      (document.documentElement.scrollHeight
      <= (Math.ceil(window.innerHeight + window.pageYOffset))
      && !document[ThreadUpdater.hidden])) {
    ThreadUpdater.clearUnread();
  }
  
  ThreadUpdater.refreshAds();
};

ThreadUpdater.clearUnread = function() {
  if (!this.dead) {
    this.setIcon(null);
  }
  if (this.lastReply) {
    this.unreadCount = 0;
    document.title = this.pageTitle;
    $.removeClass(this.lastReply, 'newPostsMarker');
    this.lastReply = null;
  }
};

ThreadUpdater.forceUpdate = function() {
  ThreadUpdater.force = true;
  ThreadUpdater.update();
};

ThreadUpdater.toggleAuto = function() {
  if (this.updating) {
    return;
  }
  this.auto ? this.stop(true) : this.start();
};

ThreadUpdater.toggleSound = function() {
  this.soundNode.checked = this.soundNodeBot.checked =
    this.audioEnabled = !this.audioEnabled;
};

ThreadUpdater.update = function() {
  var self;
  
  self = ThreadUpdater;
  
  if (self.updating) {
    return;
  }
  
  clearTimeout(self.interval);
  
  self.updating = true;
  
  self.setStatus('Updating...');
  
  $.get('//a.4cdn.org/' + Main.board + '/thread/' + Main.tid + '.json',
    {
      onload: self.onload,
      onerror: self.onerror
    },
    {
      'If-Modified-Since': self.lastModified
    }
  );
};

ThreadUpdater.initAds = function() {
  var i, id, adIds = [ '_top_ad', '_middle_ad', '_bottom_ad' ];
  
  for (i = 0; id = adIds[i]; ++i) {
    ThreadUpdater.ads[id] = {
      time: 0,
      seenOnce: false,
      isStale: false
    };
  }
};

ThreadUpdater.invalidateAds = function() {
  var id, meta;
  
  for (id in ThreadUpdater.ads) {
    meta = ThreadUpdater.ads[id];
    if (meta.seenOnce) {
      meta.isStale = true;
    }
  }
};

ThreadUpdater.refreshAds = function() {
  var self, now, el, id, ad, meta, hidden, docHeight, offset;
  
  self = ThreadUpdater;
  
  now = Date.now();
  
  if (now - self.adDebounce < 100) {
    return;
  }
  
  self.adDebounce = now;
  
  hidden = document[self.hidden];
  docHeight = document.documentElement.clientHeight;
  
  for (id in self.ads) {
    meta = self.ads[id];
    
    if (hidden) {
      continue;
    }
    
    ad = window[id];
    
    if (!ad) {
      continue;
    }
    
    el = $.id(ad.D);
    
    if (!el) {
      continue;
    }
    
    offset = el.getBoundingClientRect();
    
    if (offset.top < 0 || offset.bottom > docHeight) {
      continue;
    }
    
    meta.seenOnce = true;
    
    if (!meta.isStale || now - meta.time < self.adRefreshDelay) {
      continue;
    }
    
    meta.time = now;
    meta.isStale = false;
    
    ados_refresh(ad, 0, false);
  }
};

ThreadUpdater.markDeletedReplies = function(newposts) {
  var i, j, posthash, oldposts, el;
  
  posthash = {};
  for (i = 0; j = newposts[i]; ++i) {
    posthash['pc' + j.no] = 1;
  }
  
  oldposts = $.cls('replyContainer');
  for (i = 0; j = oldposts[i]; ++i) {
    if (!posthash[j.id] && !$.hasClass(j, 'deleted')) {
      if (this.deletionQueue[j.id]) {
        el = document.createElement('img');
        el.src = Main.icons2.trash;
        el.className = 'trashIcon';
        el.title = 'This post has been deleted';
        $.addClass(j, 'deleted');
        $.cls('postNum', j)[1].appendChild(el);
        delete this.deletionQueue[j.id];
      }
      else {
        this.deletionQueue[j.id] = 1;
      }
    }
  }
};

ThreadUpdater.onload = function() {
  var i, state, self, nodes, thread, newposts, frag, lastrep, lastid,
    op, doc, autoscroll, count, fromQR, lastRepPos;
  
  self = ThreadUpdater;
  nodes = [];
  
  self.setStatus('');
  
  if (this.status == 200) {
    self.lastModified = this.getResponseHeader('Last-Modified');
    
    thread = $.id('t' + Main.tid);
    
    lastrep = thread.children[thread.childElementCount - 1];
    lastid = +lastrep.id.slice(2);
    
    newposts = Parser.parseThreadJSON(this.responseText);
    
    state = !!newposts[0].archived;
    if (window.thread_archived !== undefined && state != window.thread_archived) {
      QR.enabled && $.id('quickReply') && QR.lock();
      Main.setThreadState('archived', state);
    }
    
    state = !!newposts[0].closed;
    if (state != Main.threadClosed) {
      if (newposts[0].archived) {
        state = false;
      }
      else if (QR.enabled && $.id('quickReply')) {
        if (state) {
          QR.lock();
        }
        else {
          QR.unlock();
        }
      }
      Main.setThreadState('closed', state);
    }
    
    state = !!newposts[0].sticky;
    if (state != Main.threadSticky) {
      Main.setThreadState('sticky', state);
    }
    
    state = !!newposts[0].imagelimit;
    if (QR.enabled && state != QR.fileDisabled) {
      QR.fileDisabled = state;
    }
    
    if (!Config.revealSpoilers && newposts[0].custom_spoiler) {
      Parser.setCustomSpoiler(Main.board, newposts[0].custom_spoiler);
    }
    
    for (i = newposts.length - 1; i >= 0; i--) {
      if (newposts[i].no <= lastid) {
        break;
      }
      nodes.push(newposts[i]);
    }
    
    count = nodes.length;
    
    if (count == 1 && QR.lastReplyId == nodes[0].no) {
      fromQR = true;
      QR.lastReplyId = null;
    }
    
    if (!fromQR) {
      self.markDeletedReplies(newposts);
    }
    
    if (count) {
      doc = document.documentElement;
      
      autoscroll = (
        Config.autoScroll
        && document[self.hidden]
        && doc.scrollHeight == Math.ceil(window.innerHeight + window.pageYOffset)
      );
      
      frag = document.createDocumentFragment();
      for (i = nodes.length - 1; i >= 0; i--) {
        frag.appendChild(Parser.buildHTMLFromJSON(nodes[i], Main.board));
      }
      thread.appendChild(frag);
      
      lastRepPos = lastrep.offsetTop;
      
      Parser.hasYouMarkers = false;
      Parser.hasHighlightedPosts = false;
      Parser.parseThread(thread.id.slice(1), -nodes.length);
      
      if (lastRepPos != lastrep.offsetTop) {
        window.scrollBy(0, lastrep.offsetTop - lastRepPos);
      }
      
      if (!fromQR) {
        if (!self.force && doc.scrollHeight > window.innerHeight) {
          if (!self.lastReply && lastid != Main.tid) {
            (self.lastReply = lastrep.lastChild).className += ' newPostsMarker';
          }
          if (Parser.hasYouMarkers) {
            self.setIcon('rep');
            if (self.audioEnabled && document[self.hidden]) {
              self.audio.play();
            }
          }
          else if (Parser.hasHighlightedPosts && self.currentIcon !== 'rep') {
            self.setIcon('hl');
          }
          else if (self.unreadCount === 0) {
            self.setIcon('new');
          }
          self.unreadCount += count;
          document.title = '(' + self.unreadCount + ') ' + self.pageTitle;
        }
        else {
          self.setStatus(count + ' new post' + (count > 1 ? 's' : ''));
        }
      }
      
      if (autoscroll) {
        window.scrollTo(0, document.documentElement.scrollHeight);
      }
      
      if (Config.threadWatcher) {
        ThreadWatcher.refreshCurrent(true);
      }
      
      if (Config.threadStats) {
        op = newposts[0];
        ThreadStats.update(op.replies, op.images, op.unique_ips, op.bumplimit, op.imagelimit);
      }
      
      self.invalidateAds();
      self.refreshAds();
      
      UA.dispatchEvent('4chanThreadUpdated', { count: count });
    }
    else {
      self.setStatus('No new posts');
    }
    
    if (newposts[0].archived) {
      self.setError('This thread is archived');
      if (!self.dead) {
        self.setIcon('dead');
        window.thread_archived = true;
        self.dead = true;
        self.stop();
      }
    }
  }
  else if (this.status === 304 || this.status === 0) {
    self.setStatus('No new posts');
  }
  else if (this.status === 404) {
    self.setIcon('dead');
    self.setError('This thread has been pruned or deleted');
    self.dead = true;
    self.stop();
    return;
  }
  
  self.lastUpdated = Date.now();
  self.adjustDelay(nodes.length);
  self.updating = self.force = false;
};

ThreadUpdater.onerror = function() {
  var self = ThreadUpdater;
  
  if (UA.isOpera && !this.statusText && this.status === 0) {
    self.setStatus('No new posts');
  }
  else {
    self.setError('Connection Error');
  }
  
  self.lastUpdated = Date.now();
  self.adjustDelay(0);
  self.updating = self.force = false;
};

ThreadUpdater.setStatus = function(msg) {
  this.statusNode.textContent = this.statusNodeBot.textContent = msg;
};

ThreadUpdater.setError = function(msg) {
  this.statusNode.innerHTML
    = this.statusNodeBot.innerHTML
    = '<span class="tu-error">' + msg + '</span>';
};

ThreadUpdater.setIcon = function(type) {
  var icon;
  
  if (type === null) {
    icon = this.defaultIcon;
  }
  else {
    icon = this.icons[Main.type + type];
  }
  
  this.currentIcon = type;
  this.iconNode.href = this.iconPath + icon;
  document.head.appendChild(this.iconNode);
};

ThreadUpdater.icons = {
  wsnew: 'favicon-ws-newposts.ico',
  nwsnew: 'favicon-nws-newposts.ico',
  wsrep: 'favicon-ws-newreplies.ico',
  nwsrep: 'favicon-nws-newreplies.ico',
  wsdead: 'favicon-ws-deadthread.ico',
  nwsdead: 'favicon-nws-deadthread.ico',
  wshl: 'favicon-ws-newfilters.ico',
  nwshl: 'favicon-nws-newfilters.ico'
};