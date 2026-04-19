$(document).ready(function() {
  $('#generateVCFButton').on('click', function(event) {
    event.stopPropagation();

    $('#generateVCFHiddenButton').click();
  });

  $('#generateCSVButton').on('click', function(event) {
    event.stopPropagation();

    $('#generateCSVHiddenButton').click();
  });
});