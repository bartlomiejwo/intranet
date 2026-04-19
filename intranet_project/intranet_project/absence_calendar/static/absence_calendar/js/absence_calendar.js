$(document).ready(function(){
  $('.absence-calendar-item').each(function(i, obj) {
    let dayContentContainer = $(obj).find('.absence-calendar-day-content');
    let detailsButtonContainer = $(obj).find('.day-details-button-container');

    if (dayContentContainer.prop('scrollHeight') > dayContentContainer.height()) {
      detailsButtonContainer.css('display', 'flex');
    }
  });
});