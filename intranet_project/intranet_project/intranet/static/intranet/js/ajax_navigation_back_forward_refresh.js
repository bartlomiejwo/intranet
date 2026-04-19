$(document).ready(function(){
    let perfEntries = performance.getEntriesByType('navigation');

    if (perfEntries[0].type === 'back_forward') {
        window.location.reload();
    }
});