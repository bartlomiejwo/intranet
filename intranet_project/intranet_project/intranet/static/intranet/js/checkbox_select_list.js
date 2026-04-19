$(document).ready(function(){
  removeLastSemicolonInEnabledActions();

  if(anyCheckboxesChecked()) {
    enableMultipleCheckboxActionButtons();
  } else {
    disableMultipleCheckboxActionButtons();
  }

  if(oneCheckboxChecked()) {
    enableOneCheckboxActionButtons();
  } else {
    disableOneCheckboxActionButtons();
  }

	$('#selectAllCheckbox').on('click', function(){
    if ($(this).is(':checked')) {
      $('.select-checkbox').each(function(){
        $(this).prop('checked', true);
      });
      
      if (anyCheckboxesChecked()) {
        enableMultipleCheckboxActionButtons();
      }

      if(oneCheckboxChecked()) {
        enableOneCheckboxActionButtons();
      } else {
        disableOneCheckboxActionButtons();
      }
    } else {
      $('.select-checkbox').each(function(){
        $(this).prop('checked', false);
      });

      if (!anyCheckboxesChecked()) {
        disableMultipleCheckboxActionButtons();
        disableOneCheckboxActionButtons();
      }
    }
  });

  $('.select-checkbox').on('click', function() {
    if(allCheckboxesChecked()) {
      $('#selectAllCheckbox').prop('checked', true);
    } else {
      $('#selectAllCheckbox').prop('checked', false);
    }
    
    if(anyCheckboxesChecked()) {
      enableMultipleCheckboxActionButtons();
    } else {
      disableMultipleCheckboxActionButtons();
    }

    if(oneCheckboxChecked()) {
      enableOneCheckboxActionButtons();
    } else {
      disableOneCheckboxActionButtons();
    }
  });

  $('.action-for-selected-checkboxes').on('click', function() {
    let url = getUrlWithIds($(this).data('url') + '?');
    let confirmation = $(this).data('confirmation');
    if (confirmation == true) {
      decision = confirm('Czy na pewno chcesz to zrobić?');

      if (decision) {
        location.href = url;
      }
    } else {
      location.href = url;
    }
  });

  $('.action-for-selected-checkboxes').on('contextmenu', function() {
    let url = getUrlWithIds($(this).data('url') + '?');
    open(url, '_blank');
  });
});

function allCheckboxesChecked() {
  let allChecked = true;

  $('.select-checkbox').each(function(){
    if (!$(this).is(':checked')) {
      allChecked = false;
      return false;
    }
  });

  return allChecked;
}

function anyCheckboxesChecked() {
  let anyChecked = false;

  $('.select-checkbox').each(function(){
    if ($(this).is(':checked')) {
      anyChecked = true;
      return false;
    }
  });

  return anyChecked;
}

function oneCheckboxChecked() {
  let numberOfChecked = 0;

  $('.select-checkbox').each(function(){
    if ($(this).is(':checked')) {
      numberOfChecked += 1;
    }
  });

  return numberOfChecked == 1;
}

function getUrlWithIds(url) {
  $('.select-checkbox').each(function(){
    if ($(this).is(':checked')) {
      url += '&id=' + $(this).data('id');
    }
  });

  return url;
}

function enableMultipleCheckboxActionButtons() {
  $('.action-for-selected-checkboxes').each(function(){
    $(this).prop('disabled', false);
  });
}

function disableMultipleCheckboxActionButtons() {
  $('.action-for-selected-checkboxes').each(function(){
    $(this).prop('disabled', true);
  });
}

function enableOneCheckboxActionButtons() {
  let checked = getCheckedCheckbox();
  let enabledActions = getEnabledActions(checked);

  if (enabledActions) {
    enabledActions.forEach(function (actionId) {
      $(actionId).prop('disabled', false);
    });
  }
}

function disableOneCheckboxActionButtons() {
  $('.action-for-selected-checkbox').each(function(){
    $(this).prop('disabled', true);
  });
}

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

function removeLastSemicolonInEnabledActions() {
  $('.select-checkbox').each(function(){
    let enabledActions = $(this).data('enabled-actions');

    if(enabledActions) {
      if (enabledActions.endsWith(',')) {
        $(this).data('enabled-actions', enabledActions.slice(0,-1));
      }
    }
  });
}

function getEnabledActions(checkbox) {
  let enabledActions = $(checkbox).data('enabled-actions');

  if (enabledActions) {
    enabledActions = enabledActions.split(',');
  }

  return enabledActions;
}
