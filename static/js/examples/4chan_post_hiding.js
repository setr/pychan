/**
 * Thread hiding
 */
var ThreadHiding = {};

ThreadHiding.init = function() {
  this.threshold = 43200000; // 12 hours
  
  this.hidden = {};
  
  this.load();
  
  this.purge();
};

ThreadHiding.clear = function(silent) {
  var i, id, key, msg;
  
  this.load();
  
  i = 0;
  
  for (id in this.hidden) {
    ++i;
  }
  
  key = '4chan-hide-t-' + Main.board;
  
  if (!silent) {
    if (!i) {
      alert("You don't have any hidden threads on /" + Main.board + '/');
      return;
    }
    
    msg = 'This will unhide ' + i + ' thread' + (i > 1 ? 's' : '') + ' on /' + Main.board + '/';
    
    if (!confirm(msg)) {
      return;
    }
    
    localStorage.removeItem(key);
  }
  else {
    localStorage.removeItem(key);
  }
};

ThreadHiding.isHidden = function(tid) {
  return !!ThreadHiding.hidden[tid];
};

ThreadHiding.toggle = function(tid) {
  if (this.isHidden(tid)) {
    this.show(tid);
  }
  else {
    this.hide(tid);
  }
  this.save();
};

ThreadHiding.show = function(tid) {
  var sa, th;
  
  th = $.id('t' + tid);
  sa = $.id('sa' + tid);
  
  if (Main.hasMobileLayout) {
    sa.parentNode.removeChild(sa);
    th.style.display = null;
    $.removeClass(th.nextElementSibling, 'mobile-hr-hidden');
  }
  else {
    sa.removeAttribute('data-hidden');
    sa.firstChild.src = Main.icons.minus;
    $.removeClass(th, 'post-hidden');
  }
  
  delete this.hidden[tid];
};

ThreadHiding.hide = function(tid) {
  var sa, th;
  
  th = $.id('t' + tid);
  
  if (Main.hasMobileLayout) {
    th.style.display = 'none';
    $.addClass(th.nextElementSibling, 'mobile-hr-hidden');
    
    sa = document.createElement('span');
    sa.id = 'sa' + tid;
    sa.setAttribute('data-cmd', 'hide');
    sa.setAttribute('data-id', tid);
    sa.textContent = 'Show Hidden Thread';
    sa.className = 'mobileHideButton button mobile-tu-show';
    th.parentNode.insertBefore(sa, th);
  }
  else {
    if (Config.hideStubs && !$.cls('stickyIcon', th)[0]) {
      th.style.display = th.nextElementSibling.style.display = 'none';
    }
    else {
      sa = $.id('sa' + tid);
      sa.setAttribute('data-hidden', tid);
      sa.firstChild.src = Main.icons.plus;
      th.className += ' post-hidden';
    }
  }
  
  this.hidden[tid] = Date.now();
};

ThreadHiding.load = function() {
  var storage;
  
  if (storage = localStorage.getItem('4chan-hide-t-' + Main.board)) {
    this.hidden = JSON.parse(storage);
  }
};

ThreadHiding.purge = function() {
  var i, hasHidden, lastPurged, key;
  
  key = '4chan-purge-t-' + Main.board;
  
  lastPurged = localStorage.getItem(key);
  
  for (i in this.hidden) {
    hasHidden = true;
    break;
  }
  
  if (!hasHidden) {
    return;
  }
  
  if (!lastPurged || lastPurged < Date.now() - this.threshold) {
    $.get('//a.4cdn.org/' + Main.board + '/threads.json',
    {
      onload: function() {
        var i, j, t, p, pages, threads, alive;
        
        if (this.status == 200) {
          alive = {};
          pages = JSON.parse(this.responseText);
          for (i = 0; p = pages[i]; ++i) {
            threads = p.threads;
            for (j = 0; t = threads[j]; ++j) {
              if (ThreadHiding.hidden[t.no]) {
                alive[t.no] = 1;
              }
            }
          }
          ThreadHiding.hidden = alive;
          ThreadHiding.save();
          localStorage.setItem(key, Date.now());
        }
        else {
          console.log('Bad status code while purging threads');
        }
      },
      onerror: function() {
        console.log('Error while purging hidden threads');
      }
    });
  }
};

ThreadHiding.save = function() {
  var i;
  
  for (i in this.hidden) {
    localStorage.setItem('4chan-hide-t-' + Main.board,
      JSON.stringify(this.hidden)
    );
    return;
  }
  localStorage.removeItem('4chan-hide-t-' + Main.board);
};

/**
 * Reply hiding
 */
var ReplyHiding = {};

ReplyHiding.init = function() {
  this.threshold = 7 * 86400000;
  this.hidden = {};
  this.hiddenR = {};
  this.hiddenRMap = {};
  this.hasR = false;
  this.load();
};

ReplyHiding.isHidden = function(pid) {
  var sa = $.id('sa' + pid);
  
  return !sa || sa.hasAttribute('data-hidden');
};

ReplyHiding.toggle = function(pid) {
  this.load();
  
  if (this.isHidden(pid)) {
    this.show(pid);
  }
  else {
    this.hide(pid);
  }
  this.save();
};

ReplyHiding.toggleR = function(pid) {
  var i, el, post, nodes, rid, parentPid;

  this.load();
  
  if (parentPid = this.hiddenRMap['>>' + pid]) {
    this.showR(parentPid, parentPid);
    
    for (i in this.hiddenRMap) {
      if (this.hiddenRMap[i] == parentPid) {
        this.showR(i.slice(2));
      }
    }
  }
  else {
    this.hideR(pid, pid);
    
    post = $.id('m' + pid);
    nodes = $.cls('postMessage');
    
    for (i = 1; nodes[i] !== post; ++i) {}
    
    for (; el = nodes[i]; ++i) {
      if (ReplyHiding.shouldToggleR(el)) {
        rid = el.id.slice(1);
        this.hideR(rid, pid);
      }
    }
  }
  
  this.hasR = false;
  
  for (i in this.hiddenRMap) {
    this.hasR = true;
    break;
  }
  
  this.save();
};

ReplyHiding.shouldToggleR = function(el) {
  var j, ql, hit, quotes;
  
  if (el.parentNode.hasAttribute('data-pfx')) {
    return false;
  }
  
  quotes = $.qsa('#' + el.id + ' > .quotelink', el);
  
  if (!quotes[0]) {
    return false;
  }
  
  hit = this.hiddenRMap[quotes[0].textContent];
  
  if (quotes.length === 1 && hit) {
    return hit;
  }
  else {
    for (j = 0; ql = quotes[j]; ++j) {
      if (!this.hiddenRMap[ql.textContent]) {
        return false;
      }
    }
  }
  
  return hit;
};

ReplyHiding.show = function(pid) {
  $.removeClass($.id('pc' + pid), 'post-hidden');
  $.id('sa' + pid).removeAttribute('data-hidden');
  
  delete ReplyHiding.hidden[pid];
};

ReplyHiding.showR = function(pid, parentPid) {
  $.removeClass($.id('pc' + pid), 'post-hidden');
  $.id('sa' + pid).removeAttribute('data-hidden');
  
  delete ReplyHiding.hiddenRMap['>>' + pid];
  
  if (parentPid) {
    delete ReplyHiding.hiddenR[parentPid];
  }
};

ReplyHiding.hide = function(pid) {
  $.addClass($.id('pc' + pid), 'post-hidden');
  $.id('sa' + pid).setAttribute('data-hidden', pid);
  
  ReplyHiding.hidden[pid] = Date.now();
};

ReplyHiding.hideR = function(pid, parentPid) {
  $.addClass($.id('pc' + pid), 'post-hidden');
  $.id('sa' + pid).setAttribute('data-hidden', pid);
  
  ReplyHiding.hiddenRMap['>>' + pid] = parentPid;
  
  if (pid === parentPid) {
    ReplyHiding.hiddenR[pid] = Date.now();
  }
  
  ReplyHiding.hasR = true;
};

ReplyHiding.load = function() {
  var storage;
  
  this.hasHiddenR = false;
  
  if (storage = localStorage.getItem('4chan-hide-r-' + Main.board)) {
    this.hidden = JSON.parse(storage);
  }
  
  if (storage = localStorage.getItem('4chan-hide-rr-' + Main.board)) {
    this.hiddenR = JSON.parse(storage);
  }
};

ReplyHiding.purge = function() {
  var tid, now;
  
  now = Date.now();
  
  for (tid in this.hidden) {
    if (now - this.hidden[tid] > this.threshold) {
      delete this.hidden[tid];
    }
  }
  
  for (tid in this.hiddenR) {
    if (now - this.hiddenR[tid] > this.threshold) {
      delete this.hiddenR[tid];
    }
  }
  
  this.save();
};

ReplyHiding.save = function() {
  var i, clr;
  
  clr = true;
  
  for (i in this.hidden) {
    localStorage.setItem('4chan-hide-r-' + Main.board,
      JSON.stringify(this.hidden)
    );
    clr = false;
    break;
  }
  
  clr && localStorage.removeItem('4chan-hide-r-' + Main.board);
  
  clr = true;
  
  for (i in this.hiddenR) {
    localStorage.setItem('4chan-hide-rr-' + Main.board,
      JSON.stringify(this.hiddenR)
    );
    clr = false;
    break;
  }
  
  clr && localStorage.removeItem('4chan-hide-rr-' + Main.board);
};
