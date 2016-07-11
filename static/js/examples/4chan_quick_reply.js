/**
 * Quick reply
 */
var QR = {};

QR.init = function() {
  var item;
  
  if (!UA.hasFormData) {
    return;
  }
  
  this.enabled = true;
  this.currentTid = null;
  this.cooldown = null;
  this.timestamp = null;
  this.auto = false;
  
  this.btn = null;
  this.comField = null;
  this.comLength = window.comlen;
  this.comCheckTimeout = null;
  
  this.cdElapsed = 0;
  this.activeDelay = 0;
  
  this.cooldowns = {};
  
  for (item in window.cooldowns) {
    this.cooldowns[item] = window.cooldowns[item] * 1000;
  }
  
  this.painterData = null;
  
  this.captchaWidgetCnt = null;
  this.captchaWidgetId = null;
  this.hasCaptchaAltJs = false;
  this.pulse = null;
  this.xhr = null;
  
  this.fileDisabled = !!window.imagelimit;
  
  this.tracked = {};
  
  this.lastTid = localStorage.getItem('4chan-cd-' + Main.board + '-tid');
  
  if (Main.tid && !Main.hasMobileLayout && !Main.threadClosed) {
    QR.addReplyLink();
  }
  
  window.addEventListener('storage', this.syncStorage, false);
};

QR.openTeXPreview = function() {
  var el;
  
  QR.closeTeXPreview();
  
  if (!window.MathJax) {
    window.loadMathJax();
  }
  
  el = document.createElement('div');
  el.id = 'tex-preview-cnt';
  el.className = 'UIPanel';
  el.setAttribute('data-cmd', 'close-tex-preview');
  el.innerHTML = '\
<div class="extPanel reply"><div class="panelHeader"><span class="tex-logo">T<sub>e</sub>X</span> Preview\
<span class="panelCtrl"><img alt="Close" title="Close" class="pointer" data-cmd="close-tex-preview" src="'
+ Main.icons.cross + '"></span></div><div id="tex-protip">Use [math][/math] tags for inline, and [eqn][/eqn] tags for block equations.</div><textarea id="input-tex-preview"></textarea>\
<div id="output-tex-preview"></div></div>';
  
  document.body.appendChild(el);
  
  el = $.id('input-tex-preview');
  $.on(el, 'keyup', QR.onTeXChanged);
};

QR.closeTeXPreview = function() {
  var el;
  
  if (el = $.id('input-tex-preview')) {
    $.off(el, 'keyup', QR.onTeXChanged);
    
    el = $.id('tex-preview-cnt');
    el.parentNode.removeChild(el);
  }
};

QR.onTeXChanged = function() {
  clearTimeout(QR.timeoutTeX);
  QR.timeoutTeX = setTimeout(QR.processTeX, 50);
};

QR.processTeX = function() {
  var src, dest;

  if (QR.processingTeX || !window.MathJax || !(src = $.id('input-tex-preview'))) {
    return;
  }
  
  dest = $.id('output-tex-preview');
  
  dest.textContent = src.value;
  
  QR.processingTeX = true;
  
  MathJax.Hub.Queue(['Typeset', MathJax.Hub, dest], ['onTeXReady', QR]);
};

QR.onTeXReady = function() {
  QR.processingTeX = false;
};

QR.addReplyLink = function() {
  var cnt, el;
  
  cnt = $.cls('navLinks')[2];
  
  el = document.createElement('div');
  el.className = 'open-qr-wrap';
  el.innerHTML = '[<a href="#" class="open-qr-link" data-cmd="open-qr">Post a Reply</a>]';
  
  cnt.insertBefore(el, cnt.firstChild);
};

QR.lock = function() {
  QR.showPostError('This thread is closed.', 'closed', true);
};

QR.unlock = function() {
  QR.hidePostError('closed');
};

QR.syncStorage = function(e) {
  var key;
  
  if (!e.key) {
    return;
  }
  
  key = e.key.split('-');
  
  if (key[0] != '4chan') {
    return;
  }
  
  if (key[1] == 'cd' && e.newValue && Main.board == key[2]) {
    if (key[3] == 'tid') {
      QR.lastTid = e.newValue;
    }
    else {
      QR.startCooldown();
    }
  }
};

QR.openPainter = function() {
  var w, h, dims;
  
  dims = $.tag('input', $.id('qr-painter-ctrl'));
  
  w = +dims[0].value;
  h = +dims[1].value;
  
  if (w < 1 || h < 1) {
    return;
  }
  
  window.Tegaki.open({
    onDone: QR.onPainterDone,
    onCancel: QR.onPainterCancel,
    width: w,
    height: h
  });
};

QR.onPainterDone = function() {
  var el;
  
  QR.painterData = Tegaki.flatten().toDataURL('image/png');
  
  if (el = $.id('qrFile')) {
    el.disabled = true;
  }
  
  if (el = $.tag('button', $.id('qr-painter-ctrl'))[1]) {
    el.disabled = false;
  }
};

QR.onPainterCancel = function() {
  var el;
  
  QR.painterData = null;
  
  if (el = $.id('qrFile')) {
    el.disabled = false;
  }
  
  if (el = $.tag('button', $.id('qr-painter-ctrl'))[1]) {
    el.disabled = true;
  }
};

QR.quotePost = function(tid, pid) {
  if (!QR.noCooldown
      && (Main.threadClosed || (!Main.tid && Main.isThreadClosed(tid)))) {
    alert('This thread is closed');
    return;
  }
  QR.show(tid);
  QR.addQuote(pid);
};

QR.addQuote = function(pid) {
  var q, pos, sel, ta;
  
  ta = $.tag('textarea', document.forms.qrPost)[0];
  
  pos = ta.selectionStart;
  
  sel = UA.getSelection();
  
  if (pid) {
    q = '>>' + pid + '\n';
  }
  else {
    q = '';
  }
  
  if (sel) {
    q += '>' + sel.trim().replace(/[\r\n]+/g, '\n>') + '\n';
  }
  
  if (ta.value) {
    ta.value = ta.value.slice(0, pos)
      + q + ta.value.slice(ta.selectionEnd);
  }
  else {
    ta.value = q;
  }
  if (UA.isOpera) {
    pos += q.split('\n').length;
  }
  
  ta.selectionStart = ta.selectionEnd = pos + q.length;
  
  if (ta.selectionStart == ta.value.length) {
    ta.scrollTop = ta.scrollHeight;
  }
  ta.focus();
};

QR.show = function(tid) {
  var i, j, cnt, postForm, form, qrForm, fields, row, spoiler, file,
    el, el2, placeholder, qrError, cookie, mfs;
  
  if (QR.currentTid) {
    if (!Main.tid && QR.currentTid != tid) {
      $.id('qrTid').textContent = $.id('qrResto').value = QR.currentTid = tid;
      $.byName('com')[1].value = '';
      
      QR.startCooldown();
    }
    
    if (Main.hasMobileLayout) {
      $.id('quickReply').style.top = window.pageYOffset + 25 + 'px';
    }
    
    return;
  }
  
  QR.currentTid = tid;
  
  postForm = $.id('postForm');
  
  cnt = document.createElement('div');
  cnt.id = 'quickReply';
  cnt.className = 'extPanel reply';
  cnt.setAttribute('data-trackpos', 'QR-position');
  
  if (Main.hasMobileLayout) {
    cnt.style.top = window.pageYOffset + 28 + 'px';
  }
  else if (Config['QR-position']) {
    cnt.style.cssText = Config['QR-position'];
  }
  else {
    cnt.style.right = '0px';
    cnt.style.top = '10%';
  }
  
  cnt.innerHTML =
    '<div id="qrHeader" class="drag postblock">'
    + (window.math_tags ? '<a data-cmd="open-tex-preview" class="desktop pointer left tex-logo" '
      + 'data-tip="Preview TeX equations">T<sub>e</sub>X</a>' : '')
    + 'Reply to Thread No.<span id="qrTid">'
    + tid + '</span><img alt="X" src="' + Main.icons.cross + '" id="qrClose" '
    + 'class="extButton" title="Close Window"></div>';
  
  form = postForm.parentNode.cloneNode(false);
  form.setAttribute('name', 'qrPost');
  
  form.innerHTML =
    (
      (mfs = $.byName('MAX_FILE_SIZE')[0])
      ? ('<input type="hidden" value="' + mfs.value + '" name="MAX_FILE_SIZE">')
      : ''
    )
    + '<input type="hidden" value="regist" name="mode">'
    + '<input id="qrResto" type="hidden" value="' + tid + '" name="resto">';
  
  qrForm = document.createElement('div');
  qrForm.id = 'qrForm';
  
  this.btn = null;
  
  fields = postForm.firstElementChild.children;
  for (i = 0, j = fields.length - 1; i < j; ++i) {
    row = document.createElement('div');
    if (fields[i].id == 'captchaFormPart') {
      if (QR.noCaptcha) {
        continue;
      }
      if (Config.altCaptcha) {
        row.id = 'qrCaptchaContainerAlt';
      }
      else {
        row.id = 'qrCaptchaContainer';
      }
      QR.captchaWidgetCnt = row;
    }
    else {
      placeholder = fields[i].getAttribute('data-type');
      if (placeholder == 'Password' || placeholder == 'Spoilers') {
        continue;
      }
      else if (placeholder == 'File') {
        file = fields[i].children[1].firstChild.cloneNode(false);
        file.tabIndex = '';
        file.id = 'qrFile';
        file.size = '19';
        file.addEventListener('change', QR.onFileChange, false);
        row.appendChild(file);
        
        file.title = 'Shift + Click to remove the file';
      }
      else if (placeholder == 'Painter') {
        row.innerHTML = fields[i].children[1].innerHTML;
        row.id = 'qr-painter-ctrl';
        row.className = 'desktop';
        el = row.getElementsByTagName('button');
        el[0].setAttribute('data-cmd', 'qr-painter-draw');
        el[1].setAttribute('data-cmd', 'qr-painter-clear');
      }
      else {
        row.innerHTML = fields[i].children[1].innerHTML;
        if (row.firstChild.type == 'hidden') {
          el = row.lastChild.previousSibling;
        }
        else {
          el = row.firstChild;
        }
        el.tabIndex = '';
        if (el.nodeName == 'INPUT' || el.nodeName == 'TEXTAREA') {
          if (el.name == 'name') {
            if (cookie = Main.getCookie('4chan_name')) {
              el.value = cookie;
            }
          }
          else if (el.name == 'email') {
            el.id = 'qrEmail';
            if (cookie = Main.getCookie('options')) {
              el.value = cookie;
            }
            if (el.nextElementSibling) {
              el.parentNode.removeChild(el.nextElementSibling); 
            }
          }
          else if (el.name == 'com') {
            QR.comField = el;
            el.addEventListener('keydown', QR.onKeyDown, false);
            el.addEventListener('paste', QR.onKeyDown, false);
            el.addEventListener('cut', QR.onKeyDown, false);
            if (row.children[1]) {
              row.removeChild(el.nextSibling);
            }
          }
          else if (el.name == 'sub') {
            continue;
          }
          if (placeholder !== null) {
            el.setAttribute('placeholder', placeholder);
          }
        }
        else if ((el.name == 'flag')) {
          if (el2 = $.qs('option[selected]', el)) {
            el2.removeAttribute('selected');
          }
          if ((cookie = Main.getCookie('4chan_flag')) &&
            (el2 = $.qs('option[value="' + cookie + '"]', el))) {
            el2.setAttribute('selected', 'selected');
          }
        }
      }
    }
    qrForm.appendChild(row);
  }
  
  if (!this.btn) {
    this.btn = $.qs('input[type="submit"]', postForm).cloneNode(false);
    this.btn.tabIndex = '';
    
    if (file) {
      file.parentNode.appendChild(this.btn);
    }
    else {
      qrForm.appendChild(document.createElement('div'));
      qrForm.lastElementChild.appendChild(this.btn);
    }
  }
  
  if (el = $.qs('.desktop > label > input[name="spoiler"]', postForm)) {
    spoiler = document.createElement('span');
    spoiler.id = 'qrSpoiler';
    spoiler.innerHTML = '<label>[<input type="checkbox" value="on" name="spoiler">Spoiler?]</label>';
    file.parentNode.insertBefore(spoiler, file.nextSibling);
  }
  
  form.appendChild(qrForm);
  cnt.appendChild(form);
  
  qrError = document.createElement('div');
  qrError.id = 'qrError';
  cnt.appendChild(qrError);
  
  cnt.addEventListener('click', QR.onClick, false);
  
  document.body.appendChild(cnt);
  
  QR.startCooldown();
  
  if (Main.threadClosed) {
    QR.lock();
  }
  
  if (!window.passEnabled) {
    if (Config.altCaptcha) {
      QR.renderCaptchaAlt();
    }
    else {
      QR.renderCaptcha();
    }
  }
  
  if (!Main.hasMobileLayout) {
    Draggable.set($.id('qrHeader'));
  }
};

QR.renderCaptcha = function() {
  if (!window.grecaptcha) {
    return;
  }
  
  QR.captchaWidgetId = grecaptcha.render(QR.captchaWidgetCnt, {
    sitekey: window.recaptchaKey,
    theme: Main.stylesheet === 'tomorrow' ? 'dark' : 'light'
  });
};

QR.renderCaptchaAlt = function() {
  if (!window.grecaptcha) {
    return;
  }
  
  if (!window.Recaptcha) {
    QR.initCaptchaAlt();
    return;
  }
  
  Recaptcha.create(window.recaptchaKey,
    'qrCaptchaContainerAlt',
    {
      theme: 'clean',
      tabindex: 0
    }
  );
};

QR.initCaptchaAlt = function(loadOnly) {
  if (QR.hasCaptchaAltJs) {
    return;
  }
  
  var el = document.createElement('script');
  el.type = 'text/javascript';
  el.src = '//www.google.com/recaptcha/api/js/recaptcha_ajax.js';
  
  if (!loadOnly) {
    el.onload = QR.renderCaptchaAlt;
  }
  
  QR.hasCaptchaAltJs = true;
  
  document.head.appendChild(el);
};

QR.resetCaptchaAlt = function(focus) {
  if (!window.grecaptcha || !$.id('recaptcha_image') || !window.RecaptchaState) {
    return;
  }
  
  if (focus) {
    Recaptcha.reload('t');
  }
  else {
    Recaptcha.reload();
  }
};

QR.resetCaptcha = function(focus) {
  if (Config.altCaptcha) {
    QR.resetCaptchaAlt(focus);
    return;
  }
  
  if (!window.grecaptcha || QR.captchaWidgetId === null) {
    return;
  }
  
  grecaptcha.reset(QR.captchaWidgetId);
};

QR.onPassError = function() {
  var el, cnt;
  
  if (QR.captchaWidgetCnt) {
    return;
  }
  
  window.passEnabled = QR.noCaptcha = false;
  
  el = document.createElement('div');
  el.id = 'qrCaptchaContainer';
  
  cnt = $.id('qrForm');
  
  cnt.insertBefore(el, cnt.lastElementChild);
  
  QR.captchaWidgetCnt = el;
  
  QR.renderCaptcha();
};

QR.onFileChange = function() {
  var fsize, maxFilesize;
  
  if (this.value) {
    maxFilesize = window.maxFilesize;
    
    if (this.files) {
      fsize = this.files[0].size;
      if (this.files[0].type == 'video/webm' && window.maxWebmFilesize) {
        maxFilesize = window.maxWebmFilesize;
      }
    }
    else {
      fsize = 0;
    }
    
    if (QR.fileDisabled) {
      QR.showPostError('Image limit reached.', 'imagelimit', true);
    }
    else if (fsize > maxFilesize) {
      QR.showPostError('Error: Maximum file size allowed is '
        + Math.floor(maxFilesize / 1048576) + ' MB', 'filesize', true);
    }
    else {
      QR.hidePostError();
    }
  }
  else {
    QR.hidePostError();
  }
  
  QR.painterData = null;
  
  QR.startCooldown();
};

QR.onKeyDown = function(e) {
  if (e.ctrlKey && e.keyCode == 83) {
    var ta, start, end, spoiler;
    
    e.stopPropagation();
    e.preventDefault();
    
    ta = e.target;
    start = ta.selectionStart;
    end = ta.selectionEnd;
    
    if (ta.value) {
      spoiler = '[spoiler]' + ta.value.slice(start, end) + '[/spoiler]';
      ta.value = ta.value.slice(0, start) + spoiler + ta.value.slice(end);
      ta.setSelectionRange(end + 19, end + 19);
    }
    else {
      ta.value = '[spoiler][/spoiler]';
      ta.setSelectionRange(9, 9);
    }
  }
  else if (e.keyCode == 27 && !e.ctrlKey && !e.altKey && !e.shiftKey && !e.metaKey) {
    QR.close();
    return;
  }
  
  clearTimeout(QR.comCheckTimeout);
  QR.comCheckTimeout = setTimeout(QR.checkCommentField, 500);
};

QR.checkCommentField = function() {
  var byteLength;
  
  if (QR.comLength) {
    byteLength = encodeURIComponent(QR.comField.value).split(/%..|./).length - 1;
    
    if (byteLength > QR.comLength) {
      QR.showPostError('Error: Comment too long ('
        + byteLength + '/' + QR.comLength + ').', 'length', true);
    }
    else {
      QR.hidePostError('length');
    }
  }
  
  if (window.sjis_tags) {
    if (/\[sjis\]/.test(QR.comField.value)) {
      if (!$.hasClass(QR.comField, 'sjis')) {
        $.addClass(QR.comField, 'sjis');
      }
    }
    else {
      if ($.hasClass(QR.comField, 'sjis')) {
        $.removeClass(QR.comField, 'sjis');
      }
    }
  }
};

QR.close = function() {
  var el, cnt = $.id('quickReply');
  
  QR.comField = null;
  QR.currentTid = null;
  
  clearInterval(QR.pulse);
  
  if (QR.xhr) {
    QR.xhr.abort();
    QR.xhr = null;
  }
  
  cnt.removeEventListener('click', QR.onClick, false);
  
  (el = $.id('qrFile')) && el.removeEventListener('change', QR.startCooldown, false);
  (el = $.id('qrEmail')) && el.removeEventListener('change', QR.startCooldown, false);
  $.tag('textarea', cnt)[0].removeEventListener('keydown', QR.onKeyDown, false);
  
  Draggable.unset($.id('qrHeader'));
  
  if (window.RecaptchaState) {
    Recaptcha.destroy();
  }
  
  document.body.removeChild(cnt);
};

QR.onClick = function(e) {
  var t = e.target;
  
  if (t.type == 'submit') {
    e.preventDefault();
    QR.submit(e.shiftKey);
  }
  else {
    switch (t.id) {
      case 'qrFile':
        if (e.shiftKey) {
          e.preventDefault();
          QR.resetFile();
        }
        break;
      case 'qrDummyFile':
      case 'qrDummyFileButton':
      case 'qrDummyFileLabel':
        e.preventDefault();
        if (e.shiftKey) {
          QR.resetFile();
        }
        else {
          $.id('qrFile').click();
        }
        break;
      case 'recaptcha_challenge_image':
        QR.resetCaptcha(true);
        break;
      case 'qrClose':
        QR.close();
        break;
    }    
  }
};

QR.showPostError = function(msg, type, silent) {
  var qrError;
  
  qrError = $.id('qrError');
  
  if (!qrError) {
    return;
  }
  
  qrError.innerHTML = msg;
  qrError.style.display = 'block';
  
  qrError.setAttribute('data-type', type || '');
  
  if (!silent && (document.hidden
    || document.mozHidden
    || document.webkitHidden
    || document.msHidden)) {
    alert('Posting Error');
  }
};

QR.hidePostError = function(type) {
  var el = $.id('qrError');
  
  if (!el.hasAttribute('style')) {
    return;
  }
  
  if (!type || el.getAttribute('data-type') == type) {
    el.removeAttribute('style');
  }
};

QR.resetFile = function() {
  var file, el;
  
  QR.painterData = null;
  
  if (el = $.id('qrDraw')) {
    el.firstElementChild.textContent = 'Draw';
  }
  
  el = document.createElement('input');
  el.id = 'qrFile';
  el.type = 'file';
  el.size = '19';
  el.name = 'upfile';
  el.addEventListener('change', QR.onFileChange, false);
  
  file = $.id('qrFile');
  file.removeEventListener('change', QR.onFileChange, false);
  
  file.parentNode.replaceChild(el, file);
  
  QR.hidePostError('imagelimit');
  
  QR.needPreuploadCaptcha = false;
  
  QR.startCooldown();
};

QR.submit = function(force) {
  var formdata;
  
  QR.hidePostError();
  
  if (!QR.presubmitChecks(force)) {
    return;
  }
  
  QR.auto = false;
  
  QR.xhr = new XMLHttpRequest();
  
  QR.xhr.open('POST', document.forms.qrPost.action, true);
  
  QR.xhr.withCredentials = true;
  
  QR.xhr.upload.onprogress = function(e) {
    if (e.loaded >= e.total) {
      QR.btn.value = '100%';
    }
    else {
      QR.btn.value = (0 | (e.loaded / e.total * 100)) + '%';
    }
  };
  
  QR.xhr.onerror = function() {
    QR.xhr = null;
    QR.showPostError('Connection error.');
  };
  
  QR.xhr.onload = function() {
    var resp, el, hasFile, ids, tid, pid, tracked;
    
    QR.xhr = null;
    
    QR.btn.value = 'Post';
    
    if (this.status == 200) {
      if (resp = this.responseText.match(/"errmsg"[^>]*>(.*?)<\/span/)) {
        if (window.passEnabled && /4chan Pass/.test(resp)) {
          QR.onPassError();
        }
        else {
          QR.resetCaptcha(true);
        }
        QR.showPostError(resp[1]);
        return;
      }
      
      if (ids = this.responseText.match(/<!-- thread:([0-9]+),no:([0-9]+) -->/)) {
        tid = ids[1];
        pid = ids[2];
        
        QR.lastTid = tid;
        
        localStorage.setItem('4chan-cd-' + Main.board + '-tid', tid);
        
        hasFile = (el = $.id('qrFile')) && el.value;
        
        QR.setPostTime();
        
        if (Config.persistentQR) {
          $.byName('com')[1].value = '';
          
          if (el = $.byName('spoiler')[2]) {
            el.checked = false;
          }
          
          QR.resetCaptcha();
          
          if (hasFile || QR.painterData) {
            QR.resetFile();
          }
          
          QR.startCooldown();
        }
        else {
          QR.close();
        }
        
        if (Main.tid) {
          if (Config.threadWatcher) {
            ThreadWatcher.setLastRead(pid, tid);
          }
          QR.lastReplyId = +pid;
          Parser.trackedReplies['>>' + pid] = 1;
          Parser.saveTrackedReplies(tid, Parser.trackedReplies);
        }
        else {
          tracked = Parser.getTrackedReplies(Main.board, tid) || {};
          tracked['>>' + pid] = 1;
          Parser.saveTrackedReplies(tid, tracked);
        }
        
        UA.dispatchEvent('4chanQRPostSuccess', { threadId: tid, postId: pid });
      }
      
      if (ThreadUpdater.enabled) {
        setTimeout(ThreadUpdater.forceUpdate, 500);
      }
    }
    else {
      QR.showPostError('Error: ' + this.status + ' ' + this.statusText);
    }
  };
  
  formdata = new FormData(document.forms.qrPost);
  
  if (QR.painterData) {
    QR.appendPainter(formdata);
  }
  
  clearInterval(QR.pulse);
  
  QR.btn.value = 'Sending';
  
  QR.xhr.send(formdata);
};

QR.appendPainter = function(formdata) {
  var blob;
  
  blob = QR.b64toBlob(QR.painterData.slice(QR.painterData.indexOf(',') + 1));
  
  if (blob) {
    if (blob.size > window.maxFilesize) {
      QR.showPostError('Error: Maximum file size allowed is '
        + Math.floor(window.maxFilesize / 1048576) + ' MB', 'filesize', true);
      
      return;
    }
    
    formdata.append('upfile', blob, 'tegaki.png');
  }
};

QR.b64toBlob = function(data) {
  var i, bytes, ary, bary, len;
  
  bytes = atob(data);
  len = bytes.length;
  
  ary = new Array(len);
  
  for (i = 0; i < len; ++i) {
    ary[i] = bytes.charCodeAt(i);
  }
  
  bary = new Uint8Array(ary);
  
  return new Blob([bary]);
};

QR.presubmitChecks = function(force) {
  if (QR.xhr) {
    QR.xhr.abort();
    QR.xhr = null;
    QR.showPostError('Aborted.');
    QR.btn.value = 'Post';
    return false;
  }
  
  if (!force && QR.cooldown) {
    if (QR.auto = !QR.auto) {
      QR.btn.value = QR.cooldown + 's (auto)';
    }
    else {
      QR.btn.value = QR.cooldown + 's';
    }
    return false;
  }
  
  return true;
};

QR.getCooldown = function(type) {
  if (QR.currentTid != QR.lastTid) {
    return QR.cooldowns[type];
  }
  else {
    return QR.cooldowns[type + '_intra'];
  }
};

QR.setPostTime = function() {
  return localStorage.setItem('4chan-cd-' + Main.board, Date.now());
};

QR.getPostTime = function() {
  return localStorage.getItem('4chan-cd-' + Main.board);
};

QR.removePostTime = function() {
  return localStorage.removeItem('4chan-cd-' + Main.board);
};

QR.startCooldown = function() {
  var type, el, time;
  
  if (QR.noCooldown || !$.id('quickReply') || QR.xhr) {
    return;
  }
  
  clearInterval(QR.pulse);
  
  type = ((el = $.id('qrFile')) && el.value) ? 'image' : 'reply';
  
  time = QR.getPostTime(type);
  
  if (!time) {
    QR.btn.value = 'Post';
    return;
  }
  
  QR.timestamp = parseInt(time, 10);
  
  QR.activeDelay = QR.getCooldown(type);
  
  QR.cdElapsed = Date.now() - QR.timestamp;
  
  QR.cooldown = Math.floor((QR.activeDelay - QR.cdElapsed) / 1000);
  
  if (QR.cooldown <= 0 || QR.cdElapsed < 0) {
    QR.cooldown = false;
    QR.btn.value = 'Post';
    return;
  }
  
  QR.btn.value = QR.cooldown + 's';
  
  QR.pulse = setInterval(QR.onPulse, 1000);
};

QR.onPulse = function() {
  QR.cdElapsed = Date.now() - QR.timestamp;
  QR.cooldown = Math.floor((QR.activeDelay - QR.cdElapsed) / 1000);
  if (QR.cooldown <= 0) {
    clearInterval(QR.pulse);
    QR.btn.value = 'Post';
    QR.cooldown = false;
    if (QR.auto) {
      QR.submit();
    }
  }
  else {
    QR.btn.value = QR.cooldown + (QR.auto ? 's (auto)' : 's');
  }
};
