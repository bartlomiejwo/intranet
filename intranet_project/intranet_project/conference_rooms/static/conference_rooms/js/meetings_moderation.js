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
          $('#meetingDecision[data-id="' + dataId + '"]').remove();

          if($('#meetingDecision').length == 0) {
            $('#listEmptyInfo').removeClass('d-none').addClass('d-block'); 
          }

          $('#successToastText[data-id="' + dataId + '"]').text(response.message);
          $('#successToast[data-id="' + dataId + '"]').toast('show');
          decreaseCounter($('#meetingsToModerateCounter'));
        } else {
          $('#errorToastText[data-id="' + dataId + '"]').text(response.message);
          $('#errorToast[data-id="' + dataId + '"]').toast('show');
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
          $('#meetingDecision[data-id="' + dataId + '"]').remove();
          $('#successToastText[data-id="' + dataId + '"]').text(response.message);
          $('#successToast[data-id="' + dataId + '"]').toast('show');
          decreaseCounter($('#meetingsToModerateCounter'));
        } else {
          $('#errorToastText[data-id="' + dataId + '"]').text(response.message);
          $('#errorToast[data-id="' + dataId + '"]').toast('show');
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

function decreaseCounter(counterElement) {
  amount = counterElement.html()
  counterElement.html(amount > 99 ? '99+' : amount-1)
}
