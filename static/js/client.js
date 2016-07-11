// Almost all of this code is stolen from meguca
//
// Make the text spoilers toggle revealing on click
etc.listener(document, 'click', 'del', function (event) {
 if (event.spoilt) return;
     event.spoilt = true;
         event.target.classList.toggle('reveal');
         });

// inject reply form on clicking [Reply]
function createForm() {
    var input = document.createElement('input');
    input.type='text';
    input.name='body';
    return input;}

var replies = document.getElementsByClassName("act posting");
for (var i = 0; i < replies.length; ++i) {
    var reply_button = replies[i];
    reply_button.addEventListener('click', function(e) {
        reply_button.appendChild(createInputForm);
    });}


// Proxy image clicks to views. More performant than dedicated listeners for
// each view.
$threads.on('click', 'img, video', function (e) {
    //if (options.get('inlinefit') == 'none' || e.which !== 1) return;
    var model = etc.getModel(e.target);
    if (!model) return;
    e.preventDefault();
    // Remove image hover preview, if any
    main.request('imager:clicked');
    model.dispatch('toggleImageExpansion', !model.get('imageExpanded'), model.get('image'), true);
});
