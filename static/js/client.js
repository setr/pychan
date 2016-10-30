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
            'themepicked': ('#theme option:first-child').val() ,
            'hidden':  [],
            'pass':    Math.random().toString(36).substr(2,16),
           }
$.each(defaults, function(key, val) {
    if (getCookieVal(key) == null) {
        Cookies.set(key, val)
    }
});
        
$('#pass').val(getCookieVal('pass')); // password at the bottom of page
$('#spoilers').prop('checked', getCookieVal('spoilers')); // unspoiler images?
$('#theme').val(getCookieVal('themepicked'));

//hide user-specified hidden post/threads as soon as the page loads
function hide_postlist(){
    var postids = Cookies.getJSON('hidden');
    $("article, section").each( function() {
      var id = this.id;
      if ($.inArray(id, postids) > -1) {
        $(this).remove()
      }});}
hide_postlist()
    
// reply form injection
function createTrailer(article, replyform, threadid){
    var form = $("<form/>",
                   {method: 'post',
                    enctype:'multipart/form-data',
                    action: './upload'});
    var submit = $("<input/>",
            {type:'submit',
                id:'submit',
                value:'Submit'});
    var cancel =$("<input/>",
            {type:'button',
                value:'Cancel',
                style:'display: inline-block;'});
    var upload = $("<input/>",
            {type:'file',
                id:'image',
                name:'image',
                accept:'image/*;.webm'});
    var spoiler = $("<input/>",
            {type:'button',
                id:'toggle'});
    var hiddenpass = $("<input/>",
            {type:'hidden',
                name:'password',
                id:'password'});
    var tid  = $("<input/>",
            {type:'hidden',
                name:'threadid',
                id:'threadid',
                val: threadid});
            // meguca uses an image to represent spoiler selection
            //default => style="background-image: url("https://meguca.org/static/css/ui/pane.png");" 
            //clicked => style="background-image: url("https://meguca.org/static/spoil/spoil5.png");"

    submit.click(function() {
        var pass = $('#pass').val();
        if (pass.trim() && getCookieVal('pass') != pass){
            Cookies.set('pass', pass);
            $('#password').val(pass);
        } else {
            $('#password').val(getCookieVal('pass'));
        }
    });
    cancel.click(function() {
        $(replyform).css("display", "table")
        $(article).remove()
    });
    form.append(submit,
                cancel,
                spoiler,
                upload,
                hiddenpass)
    if (threadid) {
        form.append(tid);
    }
    return form;
}

function createformheader(isthread){
    if (isthread) {
        tclass = 'threadsubject';
        tname = 'subject';
        ttext = 'Subject';
        tlength = '50';
    } else {
        tclass = 'replyemail';
        tname = 'email';
        ttext = 'Email';
        tlength = '30';
    }
    var header = $("<header/>").append(
                    $("<b>", {class: "name"}).append(
                        $("<input>", 
                            {type: 'text',
                                class: 'replyname',
                                maxlength: "30",
                                name: 'name',
                                placeholder: 'Anonymous'})),
                    $("<b>", {class: "Email"}).append(
                        $("<input>",
                            {type: 'text',
                                class: tclass,
                                maxlength: tlength,
                                name: tname,
                                placeholder: ttext}))
                        );
    return header;
}
    
function createarticle(replyform, isthread){
    replyform.css("display", "none")
    if (isthread) {
        threadid = replyform.parent().attr('id');
    } else {
        threadid = null;
    }

    //surrounding post-block for form
    var article = $("<article/>");
    var header = createformheader(isthread);

    var blockquote = $("<blockquote/>").append(
                        $("<p/>"),
                        $("<p/>"),
                        $("<textarea/>",
                            {name:  'body',
                             id:    'trans',
                             rows:  '1',
                             class: 'themed',
                             autocomplete: 'false',
                             style: 'width:400px; max-width: 90%; height: 40px;',
                             maxlength: '2000'}).autogrow({flickering: false}));
    var small = $("<small/>");
    var form = createTrailer(article, replyform, threadid);
    form.prepend(header,
                blockquote,
                small)
    article.append( form )

    return article; }

// Inject New thread form on click
$(".act.posting.board").each(function () {
    // create form on clicking [Reply]
    $(this).click(function() {
        $(this).before(createarticle( $(this), true ));
        $('html, body').scrollTop(0); // scroll to top 
        });
    });

// Inject reply form on click
$(".act.posting.thread").each(function () {
    // create form on clicking [Reply]
    $(this).click(function() {
        $(this).before(createarticle( $(this), false ));
        $('html, body').scrollTop( $(document).height() ); // scroll to bottom, because the reply form gets hidden
        });
    });

// image inline expandsion
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
    $('#themepicked').attr('src', newtheme);
}

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

