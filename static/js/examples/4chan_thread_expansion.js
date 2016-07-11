/**
 * Thread expansion
 */
var ThreadExpansion = {};

ThreadExpansion.init = function() {
  this.enabled = UA.hasCORS;
  this.fetchXhr = null;
};

ThreadExpansion.expandComment = function(link) {
  var ids, tid, pid, abbr;
  
  if (!(ids = link.getAttribute('href').match(/^(?:thread\/)([0-9]+)#p([0-9]+)$/))) {
    return;
  }
  
  tid = ids[1];
  pid = ids[2];
  
  abbr = link.parentNode;
  abbr.textContent = 'Loading...';
  
  $.get('//a.4cdn.org/' + Main.board + '/thread/' + tid + '.json',
    {
      onload: function() {
        var i, msg, post, posts;
        
        if (this.status == 200) {
          msg = $.id('m' + pid);
          
          posts = Parser.parseThreadJSON(this.responseText);
          
          if (tid == pid) {
            post = posts[0];
          }
          else {
            for (i = posts.length - 1; i > 0; i--) {
              if (posts[i].no == pid) {
                post = posts[i];
                break;
              }
            }
          }
          
          if (post) {
            post = Parser.buildHTMLFromJSON(post, Main.board);
            
            msg.innerHTML = $.cls('postMessage', post)[0].innerHTML;
            
            if (Parser.prettify) {
              Parser.parseMarkup(msg);
            }
            if (window.math_tags) {
              Parser.parseMathOne(msg);
            }
          }
          else {
            abbr.textContent = "This post doesn't exist anymore.";
          }
        }
        else if (this.status == 404) {
          abbr.textContent = "This thread doesn't exist anymore.";
        }
        else {
          abbr.textContent = 'Connection Error';
          console.log('ThreadExpansion: ' + this.status + ' ' + this.statusText);
        }
      },
      onerror: function() {
        abbr.textContent = 'Connection Error';
        console.log('ThreadExpansion: xhr failed');
      }
    }
  );
};

ThreadExpansion.toggle = function(tid) {
  var thread, msg, expmsg, summary, tmp;
  
  thread = $.id('t' + tid);
  summary = thread.children[1];
  if (thread.hasAttribute('data-truncated')) {
    msg = $.id('m' + tid);
    expmsg = msg.nextSibling;
  }
  
  if ($.hasClass(thread, 'tExpanded')) {
    thread.className = thread.className.replace(' tExpanded', ' tCollapsed');
    summary.children[0].src = Main.icons.plus;
    summary.children[1].style.display = 'inline';
    summary.children[2].style.display = 'none';
    if (msg) {
      tmp = msg.innerHTML;
      msg.innerHTML = expmsg.textContent;
      expmsg.textContent = tmp;
    }
  }
  else if ($.hasClass(thread, 'tCollapsed')) {
    thread.className = thread.className.replace(' tCollapsed', ' tExpanded');
    summary.children[0].src = Main.icons.minus;
    summary.children[1].style.display = 'none';
    summary.children[2].style.display = 'inline';
    if (msg) {
      tmp = msg.innerHTML;
      msg.innerHTML = expmsg.textContent;
      expmsg.textContent = tmp;
    }
  }
  else {
    summary.children[0].src = Main.icons.rotate;
    if (!ThreadExpansion.fetchXhr) {
      ThreadExpansion.fetch(tid);
    }
  }
};

ThreadExpansion.fetch = function(tid) {
  ThreadExpansion.fetchXhr = $.get(
    '//a.4cdn.org/' + Main.board + '/thread/' + tid + '.json',
    {
      onload: function() {
        var i, p, n, frag, thread, tail, posts, msg, metacap,
          expmsg, summary, abbr;
        
        ThreadExpansion.fetchXhr = null;
        
        thread = $.id('t' + tid);
        summary = thread.children[1];
        
        if (this.status == 200) {
          tail = $.cls('reply', thread);
          
          posts = Parser.parseThreadJSON(this.responseText);
          
          if (!Config.revealSpoilers && posts[0].custom_spoiler) {
            Parser.setCustomSpoiler(Main.board, posts[0].custom_spoiler);
          }
          
          frag = document.createDocumentFragment();
          
          if (tail[0]) {
            tail = +tail[0].id.slice(1);
            
            for (i = 1; p = posts[i]; ++i) {
              if (p.no < tail) {
                n = Parser.buildHTMLFromJSON(p, Main.board);
                n.className += ' rExpanded';
                frag.appendChild(n);
              }
              else {
                break;
              }
            }
          }
          else {
            for (i = 1; p = posts[i]; ++i) {
              n = Parser.buildHTMLFromJSON(p, Main.board);
              n.className += ' rExpanded';
              frag.appendChild(n);
            }
          }
          
          msg = $.id('m' + tid);
          if ((abbr = $.cls('abbr', msg)[0])
            && /^Comment/.test(abbr.textContent)) {
            thread.setAttribute('data-truncated', '1');
            expmsg = document.createElement('div');
            expmsg.style.display = 'none';
            expmsg.textContent = msg.innerHTML;
            msg.parentNode.insertBefore(expmsg, msg.nextSibling);
            if (metacap = $.cls('capcodeReplies', msg)[0]) {
              msg.innerHTML = posts[0].com + '<br><br>';
              msg.appendChild(metacap);
            }
            else {
              msg.innerHTML = posts[0].com;
            }
            if (Parser.prettify) {
              Parser.parseMarkup(msg);
            }
            if (window.math_tags) {
              Parser.parseMathOne(msg);
            }
          }
          
          thread.insertBefore(frag, summary.nextSibling);
          Parser.parseThread(tid, 1, i - 1);
          
          thread.className += ' tExpanded';
          summary.children[0].src = Main.icons.minus;
          summary.children[1].style.display = 'none';
          summary.children[2].style.display = 'inline';
        }
        else if (this.status == 404) {
          summary.children[0].src = Main.icons.plus;
          summary.children[0].display = 'none';
          summary.children[1].textContent = "This thread doesn't exist anymore.";
        }
        else {
          summary.children[0].src = Main.icons.plus;
          console.log('ThreadExpansion: ' + this.status + ' ' + this.statusText);
        }
      },
      onerror: function() {
        ThreadExpansion.fetchXhr = null;
        $.id('t' + tid).children[1].children[0].src = Main.icons.plus;
        console.log('ThreadExpansion: xhr failed');
      }
    }
  );
};