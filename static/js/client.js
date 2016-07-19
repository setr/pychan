$(document).ready(function () {
// Most of everything is based on Meguca

// Make the text spoilers toggle revealing on click
// etc.listener(document, 'click', 'del', function (event) {
//  if (event.spoilt) return;
//      event.spoilt = true;
//          event.target.classList.toggle('reveal');
//          });


// reply form injection
function createForm(article, replyform){
    // actual form
    var form = $("<form/>",
                   {method: 'post',
                    enctype:'multipart/form-data',
                    action: './upload'});
    submit = $("<input/>",
            {type:'submit',
                id:'submit',
                value:'Submit'});
    cancel =$("<input/>",
            {type:'button',
                value:'Cancel',
                style:'display: inline-block;'});
    upload = $("<input/>",
            {type:'file',
                id:'image',
                name:'image',
                accept:'image/*;.webm'});
    spoiler = $("<input/>",
            {type:'button',
                id:'toggle'});
            // meguca uses an image to represent spoiler selection
            //default => style="background-image: url("https://meguca.org/static/css/ui/pane.png");" 
            //clicked => style="background-image: url("https://meguca.org/static/spoil/spoil5.png");"

    submit.click(function() {
        $(replyform).css("display", "table")
        $(article).remove()
    });
    cancel.click(function() {
        $(replyform).css("display", "table")
        $(article).remove()
    });
    form.append(submit,
                cancel,
                spoiler,
                upload)
    return form;
}


function createarticle(replyform){
    replyform.css("display", "none")
    //surrounding post-block for form
    var article = $("<article/>");
    var header = $("<header/>").append(
                    $("<a/>", {class: 'nope'}).append(
                        $("<b> Anonymous </b>")));
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
    var form = createForm(article, replyform);
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
function create_thumb(basename, w, h){
    var img = $("<img>", {
                    "src": "/static/src/thumb/" + basename + '.jpg',
                    "class": "thumb"})
    return img;
    }
function create_expanded_image(mainpath){
    var img = $("<img>", {
                    "src": mainpath,
                    "class": "expanded"})
    return img;
    }
function create_expanded_video(mainpath){
    var vid = $("<video>", {
                    "class": "expanded",
                    controls: true});
    source = $("<source>", {
                "src": mainpath,
                "type": "video/webm"})
    vid.append(source)
    return vid
}
$(".image, .video").each(function () {
    $(this).click(function(evt) {
        // there must be a better way of doing this
        evt.preventDefault();
        basename = $(this).attr('id');
        mainpath = $(this).attr('href');
        thumb = $(this).find(".thumb");
        expanded = $(this).find(".expanded");
        img = "";
        if (thumb.length) {
            if ($(this).hasClass('image')){
                thumb.remove();
                img = create_expanded_image(mainpath);
            } else if ($(this).hasClass('video')) {
                thumb.remove();
                img = create_expanded_video(mainpath); }
        } else {
            expanded.remove();
            img = create_thumb(basename);
        }
        $(this).append(img)
        });
    });

});

