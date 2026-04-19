$(document).ready(function(){
  var REQUEST_REMOVE_NOTIFICATION = JSON.parse($('#NOTIFIER_REQUEST_REMOVE_NOTIFICATION').text());
  var RESPONSE_PUSH_NOTIFICATION = JSON.parse($('#NOTIFIER_RESPONSE_PUSH_NOTIFICATION').text());
  var RESPONSE_NOTIFICATION_REMOVED = JSON.parse($('#NOTIFIER_RESPONSE_NOTIFICATION_REMOVED').text());
  var REQUEST_CHECK_NOTIFICATION = JSON.parse($('#NOTIFIER_REQUEST_CHECK_NOTIFICATION').text());
  var RESPONSE_NOTIFICATION_CHECKED = JSON.parse($('#NOTIFIER_RESPONSE_NOTIFICATION_CHECKED').text());

  var socket;
  startWSConnection();

  $('#notificationsList').on('click', '#notification', function(event) {
    event.stopPropagation();
    redirectNotification($(this).data('url'));
  });

  $('#notificationsList').on('click', '.notification-remove-button', function(event) {
    event.stopPropagation();
    requestNotificationRemove($(this).parent().parent().data('id'));
  });

  $('#clearNotificationsButton').on('click', function(event) {
    event.stopPropagation();
    removeAllNotifications();
  });
  
  $('#notificationsList').on('mouseenter', '#notification', function(event) {
    event.stopPropagation();

    if ($(this).data('checked') == 'False') {
      requestNotificationCheck($(this).data('id'));
    }
  });

  function startWSConnection() {
    let wsStart = 'ws://';
    if (window.location.protocol == 'https:') {
      wsStart = 'wss://';
    }
    
    let url = document.querySelector('script[data-id="wsNotifications"]').getAttribute('data-url');
    let endpoint = wsStart + window.location.host + url;
    socket = new ReconnectingWebSocket(endpoint);
    
    socket.onmessage = function(e) {
      data = JSON.parse(e.data);

      if (data.type == RESPONSE_PUSH_NOTIFICATION) {
        addNotification(data.id, data.redirect_url, data.date_created, data.title, data.description, data.checked);
      } else if (data.type == RESPONSE_NOTIFICATION_REMOVED) {
        removeNotification(data.id);
      } else if (data.type == RESPONSE_NOTIFICATION_CHECKED) {
        checkNotification(data.id);
      }
    };
    
    socket.onopen = function(e) {
      ;
    };
    
    socket.onerror = function(e) {
      ;
    };
    
    socket.onclose = function(e) {
      ;
    }
  }

  function addNotification(id, url, timeCreated, title, description, checked) {
    let notifications = $('#notificationsList > #notification');
    let alreadyPresent = false;
    let exclamationColorClass = checked == 'True' ? '' : 'text-primary';
    
    for (let i=0; i<notifications.length; i++) {
      if (id == notifications[i].getAttribute('data-id')) {
        alreadyPresent = true;
        break;
      }
    }

    if(!alreadyPresent) {
      $('#notificationsList').prepend('\
        <div class="notification mb-2 p-2" id="notification" data-id="' + id + '" data-url="' + url + '" data-checked="' + checked + '">\
          <div class="notification-content">\
            <i class="fa fa-times notification-remove-button" aria-hidden="true"></i>\
            <i class="fa fa-exclamation-circle ' + exclamationColorClass + '" aria-hidden="true"></i>\
            <small class="text-muted">' + timeCreated + '</small>\
            <h6 class="mr-auto mb-0 text-truncate text-overflow-truncate">' + title + '</h6>\
            <div class="text-wrap line-height-1em small pt-2 pl-1 pr-1">' + description + '</div>\
          </div>\
        </div>\
      ');

      let notification = $('#notification[data-id="' + id + '"]');
      let width = $(notification).width();
      let height = $(notification).height();

      if (width > 0 && height > 0) {
        if (width > height) {
          $(notification).addClass('notification-wide');
        } else {
          $(notification).addClass('notification-high');
        }
      }

      let numberOfNotifications = numberOfUncheckedNotifications();
      if(numberOfNotifications > 0) {
        if(!$('#notificationBell').hasClass('bell-shake')) {
          $('#notificationBell').addClass('bell-shake');
        }

        if($('#notificationsNumber').hasClass('d-none')) {
          $('#notificationsNumber').removeClass('d-none');
        }

        if(numberOfNotifications < 99) {
          $('#notificationsNumber').text(numberOfNotifications);
        } else {
          $('#notificationsNumber').text('99');
        }
      }
    }
  }

  function requestNotificationRemove(notification_id) {
    data = {
      'type': REQUEST_REMOVE_NOTIFICATION,
      'id': notification_id,
    }
    console.log(notification_id)
    socket.send(JSON.stringify(data));
  }

  function requestNotificationCheck(notification_id) {
    data = {
      'type': REQUEST_CHECK_NOTIFICATION,
      'id': notification_id,
    }
    socket.send(JSON.stringify(data));
  }

  function removeNotification(notification_id) {
    let notification = $('#notification[data-id="' + notification_id + '"]');

    if (notification) {
      notification.fadeOut(300, function() {
        notification.remove();

        let numberOfNotifications = numberOfUncheckedNotifications();
  
        if(numberOfNotifications < 99) {
          $('#notificationsNumber').text(numberOfNotifications);
        } else {
          $('#notificationsNumber').text('99');
        }
    
        if(numberOfNotifications < 1) {
          if($('#notificationBell').hasClass('bell-shake')) {
            $('#notificationBell').removeClass('bell-shake');
          }
    
          if(!$('#notificationsNumber').hasClass('d-none')) {
            $('#notificationsNumber').addClass('d-none');
          }
        }
      });
    }
  }

  function checkNotification(notification_id) {
    let notification = $('#notification[data-id="' + notification_id + '"]');

    if (notification) {
      notification.data('checked', 'True');
      $(notification).children('.notification-content').children('.fa-exclamation-circle').removeClass('text-primary');
      $(notification).removeClass('notification-wide');
      $(notification).removeClass('notification-high');

      let numberOfNotifications = numberOfUncheckedNotifications();

      if(numberOfNotifications < 99) {
        $('#notificationsNumber').text(numberOfNotifications);
      } else {
        $('#notificationsNumber').text('99');
      }
  
      if(numberOfNotifications < 1) {
        if($('#notificationBell').hasClass('bell-shake')) {
          $('#notificationBell').removeClass('bell-shake');
        }
  
        if(!$('#notificationsNumber').hasClass('d-none')) {
          $('#notificationsNumber').addClass('d-none');
        }
      }
    }
  }

  function removeAllNotifications() {
    let notifications = $('#notificationsList > #notification');
    
    for (let i=0; i<notifications.length; i++) {
      requestNotificationRemove(notifications[i].getAttribute('data-id'));
    }
  }

  function redirectNotification(url) {
    window.location.href = url;
  }

  function numberOfUncheckedNotifications() {
    let notifications = $('#notificationsList > #notification');
    let unchecked = 0;
    
    for (const notification of notifications) {
      if ($(notification).data('checked') == 'False') {
        unchecked += 1;
      }
    }

    return unchecked;
  }
});
