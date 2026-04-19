$(document).ready(function(){
	toggleCollapseItems();
});

function toggleCollapseItems() {
	let collapseTogglers = $('.collapse-toggle');
	
	for (let toggler of collapseTogglers) {
		$(toggler).click(function()  {
			if ($(this).attr('aria-expanded') == 'true') {
				jQuery(this).find('.toggle-collapse').removeClass('d-inline-block').addClass('d-none');
				jQuery(this).find('.toggle-expand').removeClass('d-none').addClass('d-inline-block');
			} else {
				jQuery(this).find('.toggle-expand').removeClass('d-inline-block').addClass('d-none');
				jQuery(this).find('.toggle-collapse').removeClass('d-none').addClass('d-inline-block');
			}
		});
	}
}
