$(document).ready(function () {
// Most of everything is based on Meguca

// Make the text spoilers toggle revealing on click
// etc.listener(document, 'click', 'del', function (event) {
//  if (event.spoilt) return;
//      event.spoilt = true;
//          event.target.classList.toggle('reveal');
//          });

// autoconvert strings to real values
function getCookieVal(key){
    var temp = Cookies.get(key);
    switch (temp) {
        case 'false': return false;
        case 'true': return true;
        default: return temp;
    }
}
// cookie defaults
defaults = {'spoilers': false,
            'themepicked': document.querySelector('#theme option:first-child').value ,
            'hidden':  [],
            'pass':    Math.random().toString(36).substr(2,16),
           }
$.each(defaults, function(key, val) {
    if (getCookieVal(key) == null) {
        Cookies.set(key, val)
    }
});
        
document.getElementById('pass').value = getCookieVal('pass'); // password at the bottom of page
document.getElementById('spoilers').checked = getCookieVal('spoilers');
document.getElementById('theme').value = getCookieVal('themepicked');

//hide user-specified hidden post/threads as soon as the page loads
function hide_postlist(){
    var postids = Cookies.getJSON('hidden');
    document.querySelectorAll("article, section").forEach( function() {
      var id = this.id;
      if (postids.indexOf(id) != -1) {
        $(this).remove()
      }});}
hide_postlist()
    
// NEED TO APPLY TO POST FORMS
document.querySelectorAll(".act.posting.thread, .act.posting.board").forEach(function (button) {
    // button = [New Reply] || [New Thread]
    var replyform = button.nextElementSibling;
    // hide the button, show the form
    button.addEventListener('click', function () {
        button.style.display = 'none';
        replyform.style.display = 'table';
    });
    // hide the form, show the button
    var cancel = replyform.getElementsByClassName("form_cancel")[0];
    cancel.addEventListener('click', function() {
        button.style.display = 'table';
        replyform.style.display = 'none';
        // firstchild = the actual form
        replyform.firstChild.reset(); // resets all elements in the form; magic ~~~~
    });

    // submit w/ the pass from bottom right
    var submit = replyform.getElementsByClassName("form_submit")[0];
    var password = replyform.getElementsByClassName("form_password")[0];
    submit.addEventListener('click', function() {
        var pass = document.getElementById('pass').value;
        if (pass.trim() && getCookieVal('pass') != pass){
            Cookies.set('pass', pass);
            password.val(pass);
        } else {
            password.val(getCookieVal('pass'));
        }
    });

    // make the textarea dynamically grow on user input
    // eventually switch to native js autogrow
    // https://github.com/CodingAspect/Textarea-Autogrow
    /*
    var textarea = replyform.getElementsByClassName("form_trans")[0];
    Autogrow(textarea)

    textarea.addEventListener('click', function() {
        this.autogrow({flickering: false});
    });
    */

});
// currenty we still rely on jquery lib to autogrow textbox
$('.form_trans').autogrow({flickering: false});



// image inline expansion
// expanded images are injected so that we only load the full version
// if the thumbnail is clicked on.
// pdfs don't get expanded; the browser will handle opening it.
$('.image, .video').each( function (){
    $(this).click(function(evt) {
        evt.preventDefault();
        mainfile = this.href;
        if ($(this).children('.expanded').length == 0) { // inject a new expanded
            var img = '';
            $(this).children('.thumb').hide();
            if (this.classList.contains('image')){
                img = $("<img>", 
                         {"src": mainfile,
                          "class": "expanded"});
            } else if (this.classList.contains('video')){
                img = $("<video>", {"class": "expanded",
                                    "controls": true,
                                    "loop": true,
                                    "autoplay": true}).append(
                           $("<source>", {
                               "src": mainfile,
                               "type": "video/webm"}));
            }
            $(this).append(img);
        } else {
            $(this).children('.expanded, .thumb').toggle();
        }
    })
});

function c_postitem(action, value, postid){
    return $("<li>").append(
             $("<form>", {action: action, method: "POST"}).append(
               $("<input>", {type: "hidden", name: "postid", value: postid}),
               $("<input>", {type: "hidden", name: "url", value: location.href}),
               $("<input>", {type: "hidden", name: "password", value: $('#pass').val()}),
               $("<input>", {type: "Submit", value: value})));
}

/* adds the postid to hidden posts, but _does not_ hide them.
 Posts are hidden automatically only when the page is loaded. Otherwise,
 methods will have to hide them itself.
 This is because automagic hiding could be troublesome, like in the case of inline-replying pointing to a post that had been previously hidden.
 In this case, we want to see the hidden post.*/
function add_hiddenpost(postid){
    var curCookies = cookies.getJSON('hidden');
    curCookies.push(postid);
    Cookies.set('hidden', curCookies, { expires: 10 });
}
    
$(".control").click(function (){ 
    $('.popup-menu').remove();
    $('.control').not(this).css('transform', '');

    if (  $( this ).css( "transform" ) == 'none' ){
        $(this).css("transform","rotate(90deg)");
        $(this).css("transition-duration", ".4s");
        // and now we spawn a dropdown menu
        var post = $(this).closest("article, section")
        var postid = post.id;
        var board = location.pathname.split('/')[1]
        board = "/".concat(board)
        var menu = $("<ul>", {class: "popup-menu"}).append(
                        c_postitem("url", "Hide Post").click(
                            function(e) { 
                                e.preventDefault(); 
                                add_hiddenpost(postid); // add it to cookies so it stays hidden
                                post.remove();}),
                        c_postitem(board.concat("/delete"), "Delete Post", postid)
                    );
        menu.hover(
            function () {}, // do nothing on mouse enter
            function () { $(this).remove(); $('.control').css('transform', '');} // delete on mouse leave
            );
        $(this).after(menu); // if you make it a child of the arrow, it'll rotate too

    } else {
        $(this).css("transform","" );
    }
});

// BANNER CONTROLS
$('#options').click( function() {
    $('#options-panel').toggle();
});

$('[data-content^=tab-]').click( function() {
    // reset other menu items to hidden
    $('[data-content^=tab-').not(this).each( function() {
        $(this).removeClass('tab_sel');
        var tab = '.' + this.dataset.content;
        $(tab).removeClass('tab_sel')
    });
    // set this one to shown
    $(this).toggleClass('tab_sel');
    var tab = '.' + this.dataset.content;
    $(tab).addClass('tab_sel')
});

$('#theme').change(function() {
    var newtheme = $(this).val();
    Cookies.set('themepicked', newtheme);
    $('#themepicked').attr('href', newtheme);
});

$('#spoilers').change( function () {
    var checked = this.checked;
    Cookies.set('spoilers', checked);
    if (!checked){
        // swap all spoilered images with their real thumb
        $(`.image > .spoiler, 
            .pdf > .spoiler, 
            .webm > .spoiler`).each( function() {
                this.className = 'thumb unspoiler'
        });
    } else {
        $(`.image > .unspoiler, 
            .pdf > .unspoiler, 
            .webm > .unspoiler`).each( function() {
                this.className = 'thumb spoiler'
        });
    }
});

}); //end document-ready

