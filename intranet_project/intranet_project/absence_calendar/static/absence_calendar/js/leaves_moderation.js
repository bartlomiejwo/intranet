$(document).ready(function(){
  $("#leavesDecisions").on('click', '.leave-accept', function(event) {
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
          $('#leaveDecision[data-id="' + dataId + '"]').remove();

          if($('#leaveDecision').length == 0) {
            $('#listEmptyInfo').removeClass('d-none').addClass('d-block'); 
          }

          $('#successToastText[data-id="' + dataId + '"]').text(response.message);
          $('#successToast[data-id="' + dataId + '"]').toast('show');
          decreaseLeavesCounter();
          decreaseCounter($("#leavesToModerateCounter"));
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

  $("#leavesDecisions").on('click', '.leave-reject', function(event) {
    event.stopPropagation();
    
    let dataId = $(this).data('id');
    let dataUrl = $(this).data('url');
    
    $("#modalRejectLeaveButton").data('id', dataId);
    $("#modalRejectLeaveButton").data('url', dataUrl);
    $("#rejectionReason").val('');
    $("#rejectModal").modal('show');
  });

  $("#modalRejectLeaveButton").on('click', function(event) {
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
            $('#leaveDecision[data-id="' + dataId + '"]').remove();

            if($('#leaveDecision').length == 0) {
              $('#listEmptyInfo').removeClass('d-none').addClass('d-block'); 
            }

            $('#successToastText[data-id="' + dataId + '"]').text(response.message);
            $('#successToast[data-id="' + dataId + '"]').toast('show');
            decreaseLeavesCounter();
            decreaseCounter($("#leavesToModerateCounter"));
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

  $("#leavesDecisions").on('click', '.leave-accept-cancel', function(event) {
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
          $('#leaveDecision[data-id="' + dataId + '"]').remove();

          if($('#leaveDecision').length == 0) {
            $('#listEmptyInfo').removeClass('d-none').addClass('d-block'); 
          }

          $('#successToastText[data-id="' + dataId + '"]').text(response.message);
          $('#successToast[data-id="' + dataId + '"]').toast('show');
          decreaseLeavesCounter();
          decreaseCounter($("#leavesToModerateCounter"));
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

  $("#leavesDecisions").on('click', '.leave-reject-cancel', function(event) {
    event.stopPropagation();
    
    let dataId = $(this).data('id');
    let dataUrl = $(this).data('url');
    
    $("#modalRejectLeaveCancelationButton").data('id', dataId);
    $("#modalRejectLeaveCancelationButton").data('url', dataUrl);
    $("#cancelationRejectionReason").val('');
    $("#rejectCancelationModal").modal('show');
  });

  $("#modalRejectLeaveCancelationButton").on('click', function(event) {
    event.stopPropagation();

    let dataId = $(this).data('id');
    let dataUrl = $(this).data('url');
    let rejectionReason = $("#cancelationRejectionReason").val();

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
            $('#leaveDecision[data-id="' + dataId + '"]').remove();

            if($('#leaveDecision').length == 0) {
              $('#listEmptyInfo').removeClass('d-none').addClass('d-block'); 
            }

            $('#successToastText[data-id="' + dataId + '"]').text(response.message);
            $('#successToast[data-id="' + dataId + '"]').toast('show');
            decreaseLeavesCounter();
            decreaseCounter($("#leavesToModerateCounter"));
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
        $("#rejectCancelationModal").modal('hide');
        $("#cancelationRejectionReason").val('');
      },
    });
  });

  $("#leavesDecisions").on('click', '.leave-accept-finish-earlier', function(event) {
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
          $('#leaveDecision[data-id="' + dataId + '"]').remove();

          if($('#leaveDecision').length == 0) {
            $('#listEmptyInfo').removeClass('d-none').addClass('d-block'); 
          }

          $('#successToastText[data-id="' + dataId + '"]').text(response.message);
          $('#successToast[data-id="' + dataId + '"]').toast('show');
          decreaseLeavesCounter();
          decreaseCounter($("#leavesToModerateCounter"));
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

  $("#leavesDecisions").on('click', '.leave-reject-finish-earlier', function(event) {
    event.stopPropagation();
    
    let dataId = $(this).data('id');
    let dataUrl = $(this).data('url');
    
    $("#modalRejectFinishLeaveEarlierButton").data('id', dataId);
    $("#modalRejectFinishLeaveEarlierButton").data('url', dataUrl);
    $("#finishEarlierRejectionReason").val('');
    $("#rejectFinishEarlierModal").modal('show');
  });

  $("#modalRejectFinishLeaveEarlierButton").on('click', function(event) {
    event.stopPropagation();

    let dataId = $(this).data('id');
    let dataUrl = $(this).data('url');
    let rejectionReason = $("#finishEarlierRejectionReason").val();

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
            $('#leaveDecision[data-id="' + dataId + '"]').remove();

            if($('#leaveDecision').length == 0) {
              $('#listEmptyInfo').removeClass('d-none').addClass('d-block'); 
            }

            $('#successToastText[data-id="' + dataId + '"]').text(response.message);
            $('#successToast[data-id="' + dataId + '"]').toast('show');
            decreaseLeavesCounter();
            decreaseCounter($("#leavesToModerateCounter"));
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
        $("#rejectFinishEarlierModal").modal('hide');
        $("#finishEarlierRejectionReason").val('');
      },
    });
  });
});

function decreaseLeavesCounter() {
  if ($("#vacationLeavesButton").data('active') == true) {
    decreaseCounter($("#vacationLeavesButton div span"))
  } else if ($("#specialLeavesButton").data('active') == true) {
    decreaseCounter($("#specialLeavesButton div span"))
  } else if ($("#remoteWorksButton").data('active') == true) {
    decreaseCounter($("#remoteWorksButton div span"))
  }
}

function decreaseCounter(counterElement) {
  amount = counterElement.html()
  counterElement.html(amount > 99 ? '99+' : amount-1)
}
