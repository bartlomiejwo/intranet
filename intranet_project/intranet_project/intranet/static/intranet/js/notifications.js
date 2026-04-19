$(document).ready(function(){
  
  $("#notificationsButton").on('click', function(event) {
    event.stopPropagation();

    $("#notificationsContainer").fadeToggle("fast");

    let notifications = $('#notificationsList > #notification');

    for (const notification of notifications) {
      if ($(notification).data('checked') == 'False') {
        $(notification).removeClass('notification-wide');
        $(notification).removeClass('notification-high');
        
        let width = $(notification).width();
        let height = $(notification).height();
  
        if (width > height) {
          $(notification).addClass('notification-wide');
        } else {
          $(notification).addClass('notification-high');
        }
      }
    }
  });

  $("#notificationsCloseButton").on('click', function(event) {
    event.stopPropagation();
    
    $("#notificationsContainer").fadeToggle("fast");
  });
});
