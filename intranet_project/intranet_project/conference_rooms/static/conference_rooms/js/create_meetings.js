$(document).ready(function(){
  
  $("#location").change(function() {
    var selectedLeaveURL = $(this).children("option:selected").val();
    window.location.href = selectedLeaveURL;
  });

});