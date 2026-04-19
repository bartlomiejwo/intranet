$(document).ready(function(){
  
  $("#leaveType").change(function() {
    var selectedLeaveURL = $(this).children("option:selected").val();
    window.location.href = selectedLeaveURL;
  });

});