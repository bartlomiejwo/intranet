$(document).ready(function(){
  $('#confirmConfirmationDocumentAction').on('click', function(event) {
    event.stopPropagation();

    let checked = getCheckedCheckbox();
    $("#modalConfirmDocumentButton").data('id', $(checked).data('id'));
    $("#modalConfirmDocumentButton").data('url', $(checked).data('confirm-document-data-url'));

    $('#confirmationDocumentName').html($(checked).data('confirmation-document-name'));
    $('#confirmationDocumentNumber').html($(checked).data('confirmation-document-number'));
    $('#confirmationDocumentIssueDate').html($(checked).data('confirmation-document-issue-date'));
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
          let checked = getCheckedCheckbox();
          $(checked).prop('checked', false);
          $('.special-leave-row[data-id="' + dataId + '"]').removeClass('table-info').addClass('table-success');
          $('.confirmative[data-id="' + dataId + '"]').html(response.username);
          $('#confirmConfirmationDocumentAction').prop('disabled', true);
          $('#generatePDFAction').prop('disabled', true);

          let enabledActions = getEnabledActions($('.select-checkbox[data-id="' + dataId + '"]'));
          enabledActions = enabledActions.filter(function(e) { return e !== '#confirmConfirmationDocumentAction' });
          saveEnabledActions(checked, enabledActions);

          $('#successToastText').text(response.message);
          $('#successToast').toast('show');
        } else {
          $('#errorToastText').text(response.message);
          $('#errorToast').toast('show');
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

function getCheckedCheckbox() {
  let checked = null;

  $('.select-checkbox').each(function(){
    if ($(this).is(':checked')) {
      checked = this;
      return true;
    }
  });

  return checked;
}

function getEnabledActions(checkbox) {
  let enabledActions = $(checkbox).data('enabled-actions');
  enabledActions = enabledActions.split(',');

  return enabledActions;
}


function saveEnabledActions(checkbox, enabledActions) {
  let enabledActionsString = '';
  enabledActions.forEach(function (action) {
    enabledActionsString += action + ',';
  });

  if (enabledActionsString.endsWith(',')) {
    enabledActionsString = enabledActions.slice(0,-1);
  }

  $(checkbox).data('enabled-actions', enabledActionsString);
}
