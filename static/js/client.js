// Almost all of this code is stolen from meguca
//
// Make the text spoilers toggle revealing on click
etc.listener(document, 'click', 'del', function (event) {
 if (event.spoilt) return;
     event.spoilt = true;
         event.target.classList.toggle('reveal');
         });

// Inject reply form when clicking [Reply]
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

