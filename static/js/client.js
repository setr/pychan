$(document).ready(function () {
// Most of everything is based on Meguca

// Make the text spoilers toggle revealing on click
// etc.listener(document, 'click', 'del', function (event) {
//  if (event.spoilt) return;
//      event.spoilt = true;
//          event.target.classList.toggle('reveal');
//          });


// reply form injection
function createForm(){
    // actual form
    var form = $("<form/>",
                {action: '/myaction'});
    form.append(
            $("<input>",
                { type: "text",
                    name: "reply_form"}
             ));
    return form; }

function createarticle(){
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
                             style: 'width:202.344px',
                             maxlength: '2000'}));
    var small = $("<small/>");
    var form = createForm();
    article.append( header,
                    blockquote,
                    small,
                    form)
    return article; }

$(".act.posting").each(function () {
    // create form on clicking [Reply]
    $(this).click(function() {
        $(this).before(createarticle());
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
