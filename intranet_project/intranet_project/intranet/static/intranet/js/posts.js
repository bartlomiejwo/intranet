$(document).ready(function(){
  $(".like-button").on('click', function(event) {
    event.stopPropagation();

    let dataId = $(this).data('id');
    let dataIndicatorId = $(this).data('indicator-id');

    $.ajax({
      url: $(this).data('url'),
      data: {
        csrfmiddlewaretoken: csrfToken,
        pk: dataId,
      },
      type: 'post',
      success: function(response) {
        if (response.ok) {
          if(response.is_liked) {
            $('.like-button-area[data-id="' + dataId + '"]').removeClass(
              'like-button-area-not-liked').addClass('like-button-area-liked');
            $('.like-button[data-id="' + dataId + '"]').removeClass(
              'like-button-not-liked').addClass('like-button-liked');
            
            let likesIndicator = $('.likes-indicator[data-id="' + dataIndicatorId + '"]');
            let numberOfLikes = parseInt(likesIndicator.text());
            likesIndicator.text(String(numberOfLikes+1));
          } else {
            $('.like-button-area[data-id="' + dataId + '"]').removeClass(
              'like-button-area-liked').addClass('like-button-area-not-liked');
            $('.like-button[data-id="' + dataId + '"]').removeClass(
              'like-button-liked').addClass('like-button-not-liked');
            
            let likesIndicator = $('.likes-indicator[data-id="' + dataIndicatorId + '"]');
            let numberOfLikes = parseInt(likesIndicator.text());
            likesIndicator.text(String(numberOfLikes-1));
          }
        } else {
          alert(response.message);
        }
      },
      error: function(response) {
        if (response.responseJSON){
          alert('Błąd ' + response.status + ': ' + response.responseJSON.message);
        } else if (response.statusText) {
          alert(response.status + ' ' + response.statusText);
        } else {
          alert('Błąd ' + response.status);
        }
      },
    });
  });
});