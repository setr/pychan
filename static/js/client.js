$(document).ready(function () {
// Most of everything is based on Meguca

// Make the text spoilers toggle revealing on click
// etc.listener(document, 'click', 'del', function (event) {
//  if (event.spoilt) return;
//      event.spoilt = true;
//          event.target.classList.toggle('reveal');
//          });

if (Cookies.get('hidden') == null){
  Cookies.set('hidden', [])
}
if (Cookies.get('pass') == null){
  newpass = Math.random().toString(36).substr(2, 16);
  Cookies.set('pass', newpass)
}
$('#pass').val(Cookies.get('pass'));

//hide user-specified hidden post/threads as soon as the page loads
function hide_postlist(){
    var postids = Cookies.getJSON('hidden');
    $("article, section").each( function() {
      var id = $(this).attr("id")
      if ($.inArray(id, postids) > -1) {
        $(this).remove()
      }});}
hide_postlist()

function hiddenpass_update(hidden, shown){
}
    
// reply form injection
function createTrailer(article, replyform){
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
            // meguca uses an image to represent spoiler selection
            //default => style="background-image: url("https://meguca.org/static/css/ui/pane.png");" 
            //clicked => style="background-image: url("https://meguca.org/static/spoil/spoil5.png");"

    submit.click(function() {
        var pass = $('#pass').val();
        if (pass.trim() && Cookies.get('pass') != pass){
            Cookies.set('pass', pass);
            $('#password').val(pass);
        } else {
            $('#password').val(Cookies.get('pass'));
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
    return form;
}


function createarticle(replyform){
    replyform.css("display", "none")
    //surrounding post-block for form
    var article = $("<article/>");
    var header = $("<header/>").append(
                    $("<b>", {class: "name"}).append(
                    $("<input>", 
                        {type: 'text',
                         class: 'replyname',
                         maxlength: "20",
                         name: 'name',
                         value: 'Anonymous'})));
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
    var form = createTrailer(article, replyform);
    form.prepend(header,
                blockquote,
                small)
    article.append( form )
    return article; }

// Inject reply form on click
$(".act.posting.thread").each(function () {
    // create form on clicking [Reply]
    $(this).click(function() {
        $(this).before(createarticle( $(this) ));
        $('html, body').scrollTop( $(document).height() ); // scroll to bottom, because the reply form gets hidden
        });
    });

// image inline expandsion
// the srcs need to refere to url_for('static').. or better yet
// cfg.static + cfg.thumb | cfg.imgs
// pdfs don't get expanded; the browser will handle opening it.
$(".image, .video").each(function () {
    $(this).click(function(evt) {
        // there must be a better way of doing this
        evt.preventDefault();
        var basename = $(this).attr('id');
        var mainpath = $(this).attr('href');
        var thumb = $(this).find(".thumb");
        var expanded = $(this).find(".expanded");
        var img = "";
        if (thumb.length) {
            if ($(this).hasClass('image')){
                thumb.remove();
                img = $("<img>", {
                          "src": mainpath,
                          "class": "expanded"});
            } else if ($(this).hasClass('video')) {
                thumb.remove();
                img = $("<video>", {"class": "expanded",
                                    controls: true}).append(
                           $("<source>", {
                               "src": mainpath,
                               "type": "video/webm"}));
            }
        } else {
            expanded.remove();
            var img = $("<img>", {
                         "src": "/static/src/thumb/" + basename + '.jpg',
                         "class": "thumb"})
        }
        $(this).append(img)
        });
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
    var curCookies = Cookies.getJSON('hidden');
    curCookies.push(postid);
    Cookies.set('hidden', curCookies, { expires: 10 });
}
    

$(".control").click(function (){ 
    if (  $( this ).css( "transform" ) == 'none' ){
        $(this).css("transform","rotate(90deg)");
        $(this).css("transition-duration", ".4s");
        // and now we spawn a dropdown menu
        var post = $(this).closest("article, section")
        var postid = post.attr("id")
        var board = location.pathname.split('/')[1]
        board = "/".concat(board)
        $(this).after(
          $("<div>", {class: "postmenu"}).append(
            $("<ul>", {class: "postmenulist"}).append(
              c_postitem("url", "Hide Post").click(
                function(e) { 
                  e.preventDefault(); 
                  add_hiddenpost(postid);
                  post.remove();}),
              c_postitem(board.concat("/delete"), "Delete Post", postid),
              c_postitem(board.concat("/report"), "Report Post", postid))));
    } else {
        $(this).css("transform","" );
        // and now remove the dropdown menu
        $(this).next().remove();
    }
});

});

