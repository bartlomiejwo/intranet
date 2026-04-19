$(document).ready(function(){
  $('.copy-file-link-to-clip-board-button').on('click', function(event) {
    event.stopPropagation();

    let dataId = $(this).data('id');
    const linkElement = $('.clip-board-link[data-id="' + dataId + '"]');

    copyToClipboard(linkElement);

    setTimeout(function(){
      $('.copy-file-link-to-clip-board-button').tooltip('hide');
    }, 1000);
  });

  $('.copy-file-link-to-clip-board-button').tooltip({
    trigger: 'click'
  });
});

function copyToClipboard(element) {
  var $temp = $('<input>');
  $('body').append($temp);
  $temp.val($(element).attr('href')).select();
  document.execCommand('copy');
  $temp.remove();
}
