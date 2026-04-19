$(document).ready(function(){
  var filterLocalStorageStateName = $('#filtersToggle').data('local-storage-name');
  let collapsed = window.localStorage.getItem(filterLocalStorageStateName);

  if(collapsed == 'false') {
    showFilters();
  }

  $("#filtersToggle").on('click', function(event) {
    let isCollapsed = $('#filtersToggle').attr("aria-expanded");
    window.localStorage.setItem(filterLocalStorageStateName, isCollapsed);
  });
});

function showFilters() {
  $('#filtersToggle').attr('aria-expanded', 'true');
  $('#filtersToggle .toggle-expand').removeClass('d-inline-block').addClass('d-none');
  $('#filtersToggle .toggle-collapse').removeClass('d-none').addClass('d-inline-block');
  
  $('#filtersCollapse').addClass('show');
}
