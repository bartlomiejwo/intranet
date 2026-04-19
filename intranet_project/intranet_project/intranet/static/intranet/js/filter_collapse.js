$(document).ready(function(){
  if(filterFormHasAnyData()) {
    showFilters();
  }
});

function filterFormHasAnyData() {
  let hasAnyData = false;

  $("#filtersCollapse form input").each(function(){
    let input = $(this);
    
    if (input.attr('type') != 'submit') {
      if (input.val()) {
        hasAnyData = true;
        return true;
      }
    }
  });

  if (!hasAnyData) {
    $("#filtersCollapse form select").each(function(){
      let select = $(this);
      
      if (select.attr('type') != 'submit') {
        if (select.val() != '') {
          hasAnyData = true;
          return true;
        }
      }
    });
  }

  return hasAnyData;
}

function showFilters() {
  $('#filtersToggle').attr('aria-expanded', 'true');
  $('#filtersToggle .toggle-expand').removeClass('d-inline-block').addClass('d-none');
  $('#filtersToggle .toggle-collapse').removeClass('d-none').addClass('d-inline-block');
  
  $('#filtersCollapse').addClass('show');
}
