$(document).ready(function(){
  $("#leavesDecisions").on('click', '.leave-change-decision', function(event) {
    event.stopPropagation();

    let dataId = $(this).data('id');
    let dataAcceptUrl = $(this).data('accept-url');
    let dataRejectUrl = $(this).data('reject-url');

    if ($(this).data('accepted')) {
      $("#modalRejectLeaveButton").data('id', dataId);
      $("#modalRejectLeaveButton").data('accept-url', dataAcceptUrl);
      $("#modalRejectLeaveButton").data('reject-url', dataRejectUrl);
      $("#rejectionReason").val('');
      $("#rejectModal").modal('show');
    } else {
      $("#modalAcceptLeaveButton").data('id', dataId);
      $("#modalAcceptLeaveButton").data('accept-url', dataAcceptUrl);
      $("#modalAcceptLeaveButton").data('reject-url', dataRejectUrl);
      $("#acceptModal").modal('show');
    }
  });

  $("#modalAcceptLeaveButton").on('click', function(event) {
    event.stopPropagation();

    let dataId = $(this).data('id');
    let dataRejectUrl = $(this).data('reject-url');
    let dataAcceptUrl = $(this).data('accept-url');

    $.ajax({
      url: dataAcceptUrl,
      data: {
        csrfmiddlewaretoken: csrfToken,
        id: dataId,
      },
      type: 'post',
      success: function(response) {
        if (response.ok) {
          let leaveDecisionAlert = $('#leaveDecisionAlert[data-id="' + dataId + '"]');
          leaveDecisionAlert.removeClass('alert-danger').addClass('alert-success');
          leaveDecisionAlert.html(
            'Wniosek urlopowy został zaakceptowany ' + 
            '<button type="button" class="btn btn-sm btn-danger ml-1 ' + 'leave-change-decision" data-id="' + 
            dataId + '" data-accepted="true" data-reject-url="' + dataRejectUrl + '" data-accept-url="' + 
            dataAcceptUrl + '">Zmień decyzję - odmów</button>'
          );
          $('#successToastText[data-id="' + dataId + '"]').text(response.message);
          $('#successToast[data-id="' + dataId + '"]').toast('show');
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
        $("#acceptModal").modal('hide');
      },
    });
  });
  
  $("#modalRejectLeaveButton").on('click', function(event) {
    event.stopPropagation();

    let dataId = $(this).data('id');
    let dataRejectUrl = $(this).data('reject-url');
    let dataAcceptUrl = $(this).data('accept-url');
    let rejectionReason = $("#rejectionReason").val();

    $.ajax({
      url: dataRejectUrl,
      data: {
        csrfmiddlewaretoken: csrfToken,
        id: dataId,
        reason: rejectionReason,
      },
      type: 'post',
      success: function(response) {
        if (response.ok) {
          let leaveDecisionAlert = $('#leaveDecisionAlert[data-id="' + dataId + '"]');
          leaveDecisionAlert.removeClass('alert-success').addClass('alert-danger');

          if (rejectionReason) {
            leaveDecisionAlert.html(
              'Wniosek urlopowy został odrzucony ' + 
              ' z następującego powodu:<br>' + rejectionReason + '<br><button type="button"' + 
              'class="btn btn-sm btn-success ml-1 ' + 'leave-change-decision" data-id="' + 
              dataId + '" data-accepted="false" data-accept-url="' + dataAcceptUrl + '" data-reject-url="' + 
              dataRejectUrl + '">Zmień decyzję - akceptuj</button>'
            );
          } else {
            leaveDecisionAlert.html('Wniosek urlopowy został odrzucony ' +
              '<button type="button" class="btn btn-sm btn-success ml-1 ' + 'leave-change-decision" data-id="' + 
              dataId + '" data-accepted="false" data-accept-url="' + dataAcceptUrl + '" data-reject-url="' + 
              dataRejectUrl + '">Zmień decyzję - akceptuj</button>');
          }

          $('#successToastText[data-id="' + dataId + '"]').text(response.message);
          $('#successToast[data-id="' + dataId + '"]').toast('show');
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

  $("#leavesDecisions").on('click', '.confirm-document-data', function(event) {
    event.stopPropagation();

    let dataId = $(this).data('id');
    let dataUrl = $(this).data('url');

    $("#modalConfirmDocumentButton").data('id', dataId);
    $("#modalConfirmDocumentButton").data('url', dataUrl);
    $("#confirmModal").modal('show');
  });

  $("#modalConfirmDocumentButton").on('click', function(event) {
    event.stopPropagation();

    let dataId = $(this).data('id');
    let dataUrl = $(this).data('url');

    $.ajax({
      url: dataUrl,
      data: {
        csrfmiddlewaretoken: csrfToken,
        id: dataId,
      },
      type: 'post',
      success: function(response) {
        if (response.ok) {
          $('.confirming-person-display[data-id="' + dataId + '"]').html(response.username);

          $('#successToastText[data-id="' + dataId + '"]').text(response.message);
          $('#successToast[data-id="' + dataId + '"]').toast('show');
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
        $("#confirmModal").modal('hide');
      },
    });
  });
});
