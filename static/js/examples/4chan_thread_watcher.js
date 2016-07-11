/**
 * Thread watcher
 */
var ThreadWatcher = {};

ThreadWatcher.init = function() {
  var cnt, jumpTo, rect, el;
  
  this.listNode = null;
  this.charLimit = 45;
  this.watched = {};
  this.blacklisted = {};
  this.isRefreshing = false;
  
  if (Main.hasMobileLayout) {
    el = document.createElement('a');
    el.href = '#';
    el.textContent = 'TW';
    el.addEventListener('click', ThreadWatcher.toggleList, false);
    cnt = $.id('settingsWindowLinkMobile');
    cnt.parentNode.insertBefore(el, cnt);
    cnt.parentNode.insertBefore(document.createTextNode(' '), cnt);
  }
  
  if (location.hash && (jumpTo = location.hash.split('lr')[1])) {
    if (jumpTo = $.id('pc' + jumpTo)) {
      if (jumpTo.nextElementSibling) {
        jumpTo = jumpTo.nextElementSibling;
        if (el = $.id('p' + jumpTo.id.slice(2))) {
          $.addClass(el, 'highlight');
        }
      }
      
      rect = jumpTo.getBoundingClientRect();
      
      if (rect.top < 0 || rect.bottom > document.documentElement.clientHeight) {
        window.scrollBy(0, rect.top);
      }
    }
    
    if (window.history && history.replaceState) {
      history.replaceState(null, '', location.href.split('#', 1)[0]);
    }
  }
  
  cnt = document.createElement('div');
  cnt.id = 'threadWatcher';
  cnt.className = 'extPanel reply';
  cnt.setAttribute('data-trackpos', 'TW-position');
  
  if (Main.hasMobileLayout) {
    cnt.style.display = 'none';
  }
  else {
    if (Config['TW-position']) {
      cnt.style.cssText = Config['TW-position'];
    }
    else {
      cnt.style.left = '10px';
      cnt.style.top = '380px';
    }
    
    if (Config.fixedThreadWatcher) {
      cnt.style.position = 'fixed';
    }
    else {
      cnt.style.position = '';
    }
  }
  
  cnt.innerHTML = '<div class="drag" id="twHeader">'
    + (Main.hasMobileLayout ? ('<img id="twClose" class="pointer" src="'
    + Main.icons.cross + '" alt="X">') : '')
    + 'Thread Watcher'
    + (UA.hasCORS ? ('<img id="twPrune" class="pointer right" src="'
    + Main.icons.refresh + '" alt="R" title="Refresh"></div>') : '</div>');
  
  this.listNode = document.createElement('ul');
  this.listNode.id = 'watchList';
  
  this.load();
  
  if (Main.tid) {
    this.refreshCurrent();
  }
  
  this.build();
  
  cnt.appendChild(this.listNode);
  document.body.appendChild(cnt);
  cnt.addEventListener('mouseup', this.onClick, false);
  Draggable.set($.id('twHeader'));
  window.addEventListener('storage', this.syncStorage, false);
  
  if (Main.hasMobileLayout) {
    if (Main.tid) {
      ThreadWatcher.initMobileButtons();
    }
  }
  else if (!Main.tid && this.canAutoRefresh()) {
    this.refresh();
  }
};

ThreadWatcher.toggleList = function(e) {
  var el = $.id('threadWatcher');
  
  e && e.preventDefault();
  
  if (!Main.tid && ThreadWatcher.canAutoRefresh()) {
    ThreadWatcher.refresh();
  }
  
  if (el.style.display == 'none') {
    el.style.top = (window.pageYOffset + 30) + 'px';
    el.style.display = '';
  }
  else {
    el.style.display = 'none';
  }
};

ThreadWatcher.syncStorage = function(e) {
  var key;
  
  if (!e.key) {
    return;
  }
  
  key = e.key.split('-');
  
  if (key[0] == '4chan' && key[1] == 'watch' && !key[2] && e.newValue != e.oldValue) {
    ThreadWatcher.load();
    ThreadWatcher.build(true);
  }
};

ThreadWatcher.load = function() {
  var storage;
  
  if (storage = localStorage.getItem('4chan-watch')) {
    this.watched = JSON.parse(storage);
  }
  if (storage = localStorage.getItem('4chan-watch-bl')) {
    this.blacklisted = JSON.parse(storage);
  }
};

ThreadWatcher.build = function(rebuildButtons) {
  var html, tuid, key, cls;
  
  html = '';
  
  for (key in this.watched) {
    tuid = key.split('-');
    html += '<li id="watch-' + key
      + '"><span class="pointer" data-cmd="unwatch" data-id="'
      + tuid[0] + '" data-board="' + tuid[1] + '">&times;</span> <a href="'
      + Main.linkToThread(tuid[0], tuid[1]) + '#lr' + this.watched[key][1] + '"';
    
    if (this.watched[key][1] == -1) {
      html += ' class="deadlink">';
    }
    else {
      cls = [];
      
      if (this.watched[key][3]) {
        cls.push('archivelink');
      }
      
      if (this.watched[key][4]) {
        cls.push('hasYouReplies');
        html += ' title="This thread has replies to your posts"';
      }
      
      if (this.watched[key][2]) {
        html += ' class="' + (cls[0] ? (cls.join(' ') + ' ') : '')
          + 'hasNewReplies">(' + this.watched[key][2] + ') ';
      }
      else {
        html += (cls[0] ? ('class="' + cls.join(' ') + '"') : '') + '>';
      }
    }
    
    html += '/' + tuid[1] + '/ - ' + this.watched[key][0] + '</a></li>';
  }
  
  if (rebuildButtons) {
    ThreadWatcher.rebuildButtons();
  }
  
  ThreadWatcher.listNode.innerHTML = html;
};

ThreadWatcher.rebuildButtons = function() {
  var i, buttons, key, btn;
  
  buttons = $.cls('wbtn');
  
  for (i = 0; btn = buttons[i]; ++i) {
    key = btn.getAttribute('data-id') + '-' + Main.board;
    if (ThreadWatcher.watched[key]) {
      if (!btn.hasAttribute('data-active')) {
        btn.src = Main.icons.watched;
        btn.setAttribute('data-active', '1');
      }
    }
    else {
      if (btn.hasAttribute('data-active')) {
        btn.src = Main.icons.notwatched;
        btn.removeAttribute('data-active');
      }
    }
  }
};

ThreadWatcher.initMobileButtons = function() {
  var el, cnt, key, ref;
  
  el = document.createElement('img');
  
  key = Main.tid + '-' + Main.board;
  
  if (ThreadWatcher.watched[key]) {
    el.src = Main.icons.watched;
    el.setAttribute('data-active', '1');
  }
  else {
    el.src = Main.icons.notwatched;
  }
  
  el.className = 'extButton wbtn wbtn-' + key;
  el.setAttribute('data-cmd', 'watch');
  el.setAttribute('data-id', Main.tid);
  el.alt = 'W';
  
  cnt = document.createElement('span');
  cnt.className = 'mobileib button';
  
  cnt.appendChild(el);
  
  if (ref = $.cls('navLinks')[0]) {
    ref.appendChild(document.createTextNode(' '));
    ref.appendChild(cnt);
  }
  
  if (ref = $.cls('navLinks')[3]) {
    ref.appendChild(document.createTextNode(' '));
    ref.appendChild(cnt.cloneNode(true));
  }
};

ThreadWatcher.onClick = function(e) {
  var t = e.target;
  
  if (t.hasAttribute('data-id')) {
    ThreadWatcher.toggle(
      t.getAttribute('data-id'),
      t.getAttribute('data-board')
    );
  }
  else if (t.id == 'twPrune' && !ThreadWatcher.isRefreshing) {
    ThreadWatcher.refreshWithAutoWatch();
  }
  else if (t.id == 'twClose') {
    ThreadWatcher.toggleList();
  }
};

ThreadWatcher.generateLabel = function(sub, com, tid) {
  var label;
  
  if (label = sub) {
    label = label.slice(0, this.charLimit);
  }
  else if (label = com) {
    label = label.replace(/(?:<br>)+/g, ' ')
      .replace(/<[^>]*?>/g, '').slice(0, this.charLimit);
  }
  else {
    label = 'No.' + tid;
  }
  
  return label;
};

ThreadWatcher.toggle = function(tid, board) {
  var key, label, sub, com, lastReply, thread;
  
  key = tid + '-' + (board || Main.board);
  
  if (this.watched[key]) {
    this.blacklisted[key] = 1;
    delete this.watched[key];
  }
  else {
    sub = $.cls('subject', $.id('pi' + tid))[0].textContent;
    com = $.id('m' + tid).innerHTML;
    
    label = ThreadWatcher.generateLabel(sub, com, tid);
    
    if ((thread = $.id('t' + tid)).children[1]) {
      lastReply = thread.lastElementChild.id.slice(2);
    }
    else {
      lastReply = tid;
    }
    
    this.watched[key] = [ label, lastReply, 0 ];
  }
  this.save();
  this.load();
  this.build(true);
};

ThreadWatcher.addRaw = function(post, board) {
  var key, label;
  
  key = post.no + '-' + board;
  
  if (this.watched[key]) {
    return;
  }
  
  label = ThreadWatcher.generateLabel(post.sub, post.com, post.no);
  
  this.watched[key] = [ label, 0, 0 ];
};

ThreadWatcher.save = function() {
  var i;
  
  ThreadWatcher.sortByBoard();
  
  localStorage.setItem('4chan-watch', JSON.stringify(ThreadWatcher.watched));
  
  for (i in ThreadWatcher.blacklisted) {
    localStorage.setItem('4chan-watch-bl', JSON.stringify(ThreadWatcher.blacklisted));
    break;
  }
};

ThreadWatcher.sortByBoard = function() {
  var i, self, key, sorted, keys;
  
  self = ThreadWatcher;
  
  sorted = {};
  keys = [];
  
  for (key in self.watched) {
    keys.push(key);
  }
  
  keys.sort(function(a, b) {
    a = a.split('-')[1];
    b = b.split('-')[1];
    
    if (a < b) {
      return -1;
    }
    if (a > b) {
      return 1;
    }
    return 0;
  });
  
  for (i = 0; key = keys[i]; ++i) {
    sorted[key] = self.watched[key];
  }
  
  self.watched = sorted;
};

ThreadWatcher.canAutoRefresh = function() {
  var time;
  
  if (time = localStorage.getItem('4chan-tw-timestamp')) {
    return Date.now() - (+time) >= 60000;
  }
  
  return true;
};

ThreadWatcher.setRefreshTimestamp = function() {
  localStorage.setItem('4chan-tw-timestamp', Date.now());
};

ThreadWatcher.refreshWithAutoWatch = function() {
  var i, f, count, board, boards, img;
  
  if (!Config.filter) {
    this.refresh();
    return;
  }
  
  Filter.load();
  
  boards = {};
  count = 0;
  
  for (i = 0; f = Filter.activeFilters[i]; ++i) {
    if (!f.auto || !f.boards) {
      continue;
    }
    for (board in f.boards) {
      if (boards[board]) {
        continue;
      }
      boards[board] = true;
      ++count;
    }
  }
  
  if (!count) {
    this.refresh();
    return;
  }
  
  img = $.id('twPrune');
  img.src = Main.icons.rotate;
  this.isRefreshing = true;
  
  this.fetchCatalogs(boards, count);
};

ThreadWatcher.fetchCatalogs = function(boards, count) {
  var to, board, catalogs, meta;
  
  catalogs = {};
  meta = { count: count };
  to = 0;
  
  for (board in boards) {
    setTimeout(ThreadWatcher.fetchCatalog, to, board, catalogs, meta);
    to += 200;
  }
};

ThreadWatcher.fetchCatalog = function(board, catalogs, meta) {
  var xhr;
  
  xhr = new XMLHttpRequest();
  xhr.open('GET', '//a.4cdn.org/' + board + '/catalog.json');
  xhr.onload = function() {
    meta.count--;
    catalogs[board] = Parser.parseCatalogJSON(this.responseText);
    if (!meta.count) {
      ThreadWatcher.onCatalogsLoaded(catalogs);
    }
  };
  xhr.onerror = function() {
    meta.count--;
    if (!meta.count) {
      ThreadWatcher.onCatalogsLoaded(catalogs);
    }
  };
  xhr.send(null);
};

ThreadWatcher.onCatalogsLoaded = function(catalogs) {
  var i, j, board, page, pages, threads, thread, key, blacklisted;
  
  $.id('twPrune').src = Main.icons.refresh;
  this.isRefreshing = false;
  
  blacklisted = {};
  
  for (board in catalogs) {
    pages = catalogs[board];
    for (i = 0; page = pages[i]; ++i) {
      threads = page.threads;
      for (j = 0; thread = threads[j]; ++j) {
        key = thread.no + '-' + board;
        if (this.blacklisted[key]) {
          blacklisted[key] = 1;
          continue;
        }
        if (Filter.match(thread, board)) {
          this.addRaw(thread, board);
        }
      }
    }
  }
  
  this.blacklisted = blacklisted;
  this.build(true);
  this.refresh();
};

ThreadWatcher.refresh = function() {
  var i, to, key, total, img;
  
  if (total = $.id('watchList').children.length) {
    i = to = 0;
    img = $.id('twPrune');
    img.src = Main.icons.rotate;
    ThreadWatcher.isRefreshing = true;
    ThreadWatcher.setRefreshTimestamp();
    for (key in ThreadWatcher.watched) {
      setTimeout(ThreadWatcher.fetch, to, key, ++i == total ? img : null);
      to += 200;
    }
  }
};

ThreadWatcher.refreshCurrent = function(rebuild) {
  var key, thread, lastReply;
  
  key = Main.tid + '-' + Main.board;
  
  if (this.watched[key]) {
    if ((thread = $.id('t' + Main.tid)).children[1]) {
      lastReply = thread.lastElementChild.id.slice(2);
    }
    else {
      lastReply = Main.tid;
    }
    if (this.watched[key][1] < lastReply) {
      this.watched[key][1] = lastReply;
    }
    
    this.watched[key][2] = 0;
    this.watched[key][4] = 0;
    this.save();
    
    if (rebuild) {
      this.build();
    }
  }
};

ThreadWatcher.setLastRead = function(pid, tid) {
  var key = tid + '-' + Main.board;
  
  if (this.watched[key]) {
    this.watched[key][1] = pid;
    this.watched[key][2] = 0;
    this.watched[key][4] = 0;
    this.save();
    this.build();
  }
};

ThreadWatcher.onRefreshEnd = function(img) {
  img.src = Main.icons.refresh;
  this.isRefreshing = false;
  this.save();
  this.load();
  this.build();
};

ThreadWatcher.fetch = function(key, img) {
  var tuid, xhr, li;
  
  li = $.id('watch-' + key);
  
  if (ThreadWatcher.watched[key][1] == -1) {
    delete ThreadWatcher.watched[key];
    li.parentNode.removeChild(li);
    if (img) {
      ThreadWatcher.onRefreshEnd(img);
    }
    return;
  }
  
  tuid = key.split('-'); // tid, board
  
  xhr = new XMLHttpRequest();
  xhr.onload = function() {
    var i, newReplies, posts, lastReply, trackedReplies, dummy, quotelinks, q, j;
    if (this.status == 200) {
      posts = Parser.parseThreadJSON(this.responseText);
      lastReply = ThreadWatcher.watched[key][1];
      newReplies = 0;
      
      if (!ThreadWatcher.watched[key][4]) {
        trackedReplies = Parser.getTrackedReplies(tuid[1], tuid[0]);
        
        if (trackedReplies) {
          dummy = document.createElement('div');
        }
      }
      else {
        trackedReplies = null;
      }
      
      for (i = posts.length - 1; i >= 1; i--) {
        if (posts[i].no <= lastReply) {
          break;
        }
        ++newReplies;
        
        if (trackedReplies) {
          dummy.innerHTML = posts[i].com;
          quotelinks = $.cls('quotelink', dummy);
          
          if (!quotelinks[0]) {
            continue;
          }
          
          for (j = 0; q = quotelinks[j]; ++j) {
            if (trackedReplies[q.textContent]) {
              ThreadWatcher.watched[key][4] = 1;
              trackedReplies = null;
              break;
            }
          }
        }
      }
      if (newReplies > ThreadWatcher.watched[key][2]) {
        ThreadWatcher.watched[key][2] = newReplies;
      }
      if (posts[0].archived) {
        ThreadWatcher.watched[key][3] = 1;
      }
    }
    else if (this.status == 404) {
      ThreadWatcher.watched[key][1] = -1;
    }
    if (img) {
      ThreadWatcher.onRefreshEnd(img);
    }
  };
  if (img) {
    xhr.onerror = xhr.onload;
  }
  xhr.open('GET', '//a.4cdn.org/' + tuid[1] + '/thread/' + tuid[0] + '.json');
  xhr.send(null);
};