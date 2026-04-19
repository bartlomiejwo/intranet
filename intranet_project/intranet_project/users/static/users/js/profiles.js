$(document).ready(function(){
  
    $("#profileNavigation").change(function() {
      var selectedURL = $(this).children("option:selected").val();
      window.location.href = selectedURL;
    });
  
  });