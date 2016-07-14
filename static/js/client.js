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
                {action: '/upload'});
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

$(".act.posting").each(function () {
    // create form on clicking [Reply]
    $(this).click(function() {
        $(this).before(createarticle( $(this) ));
    });
});

//<article>
//    <header>
//        <a class="nope">
//            <b>
//            Anonymous
//            </b>
//        </a>
//        <time>
//        </time>
//    </header>
//    <blockquote>
//        <p>
//        </p>
//        <p>
//        </p>
//        <textarea name="body" id="trans" rows="1" class="themed" autocomplete="false" style="width: 202.344px;" maxlength="2000">
//        </textarea>
//    </blockquote>
//    <small>
//    </small>
//    <form method="post" enctype="multipart/form-data" target="upload">
//        <input type="button" value="Cancel" style="display: inline-block;">
//        <input type="file" id="image" name="image" accept="imager/*;.webm">
//        <input type="button" id="toggle" style="background-image: url(&quot;https://meguca.org/static/css/ui/pane.png&quot;);">
//        <strong>
//        </strong>
//    </form>
//</article>
//            
//
//$(".act.posting").each(function () { 
//    $(this).click(function() {
//        alert( "Handler for .click() called." );
//    });
//});
});
