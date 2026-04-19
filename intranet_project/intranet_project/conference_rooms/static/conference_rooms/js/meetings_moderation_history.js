$(document).ready(function(){

  $("#meetingDecisions").on('click', '.meeting-accept', function(event) {
    event.stopPropagation();

    let dataId = $(this).data('id');

    $.ajax({
      url: $(this).data('url'),
      data: {
        csrfmiddlewaretoken: csrfToken,
        id: dataId,
      },
      type: 'post',
      success: function(response) {
        if (response.ok) {
          alert(response.message);
          location.reload();
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

  $("#meetingDecisions").on('click', '.meeting-reject', function(event) {
    event.stopPropagation();
    
    let dataId = $(this).data('id');
    let dataUrl = $(this).data('url');
    
    $("#modalRejectMeetingButton").data('id', dataId);
    $("#modalRejectMeetingButton").data('url', dataUrl);
    $("#rejectionReason").val('');
    $("#rejectModal").modal('show');
  });

  $("#modalRejectMeetingButton").on('click', function(event) {
    event.stopPropagation();

    let dataId = $(this).data('id');
    let dataUrl = $(this).data('url');
    let rejectionReason = $("#rejectionReason").val();

    $.ajax({
      url: dataUrl,
      data: {
        csrfmiddlewaretoken: csrfToken,
        id: dataId,
        reason: rejectionReason,
      },
      type: 'post',
      success: function(response) {
        if (response.ok) {
          alert(response.message);
          location.reload();
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
      complete: function() {
        $("#rejectModal").modal('hide');
        $("#rejectionReason").val('');
      },
    });
  });
});