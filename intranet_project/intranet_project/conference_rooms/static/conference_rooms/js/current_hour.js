$(document).ready(function(){
  removeColumnForCurrentTimeIndicatorCalculationsOnFirefox();

  let currentTimeIndexData = document.getElementById('currentTimeIndexData');

  if(currentTimeIndexData !== null) {
    let currentTimeIndex = JSON.parse(currentTimeIndexData.textContent);
    let tableEmptyCorner = document.getElementsByClassName('conference-rooms-table-column-header-empty-corner')[0];
    let currentTimeIndicator = document.getElementById('currentTimeIndicator');
    let conferenceRoomsScrollable = document.getElementById('conferenceRoomsScrollable');
    let currentTimeRow = document.getElementsByClassName('conference-rooms-row')[currentTimeIndex];
    
    currentTimeIndicator.style.marginLeft = tableEmptyCorner.clientWidth + 'px';
    currentTimeIndicator.style.marginTop = currentTimeRow.offsetTop + 'px';
    currentTimeIndicator.style.width = 'calc(100% - ' + tableEmptyCorner.clientWidth + 'px)';

    currentTimeIndicator.style.setProperty('-webkit-transition', 'all 1s ease-in-out');
    currentTimeIndicator.style.setProperty('-moz-transition', 'all 1s ease-in-out');
    currentTimeIndicator.style.setProperty('-o-transition', 'all 1s ease-in-out');
    currentTimeIndicator.style.setProperty('transition', 'all 1s ease-in-out');
    currentTimeIndicator.style.setProperty('transition-property', 'margin-top, opacity');
    currentTimeIndicator.style.opacity = '0.1';

    conferenceRoomsScrollable.addEventListener('scroll', function() {
      if (conferenceRoomsScrollable.scrollLeft <= tableEmptyCorner.clientWidth) {
        let scrollOffset = tableEmptyCorner.clientWidth - conferenceRoomsScrollable.scrollLeft;
        currentTimeIndicator.style.marginLeft = scrollOffset + 'px';
        currentTimeIndicator.style.width = 'calc(100% - ' + scrollOffset + 'px)';
      } else {
        currentTimeIndicator.style.marginLeft = '0px';
        currentTimeIndicator.style.width = '100%';
      }
    });

    let msUntilTimeIndicatorMove = JSON.parse(document.getElementById('msUntilTimeIndicatorMoveData').textContent);
    let indicatorMoveTimer = setTimeout(moveIndicatorTimeout, msUntilTimeIndicatorMove);

    function moveIndicatorTimeout() {
      let rows = document.getElementsByClassName('conference-rooms-row');

      if (currentTimeIndex >= rows.length) {
        currentTimeIndicator.style.opacity = '0.0';
      } else {
        currentTimeIndex += 1;
        currentTimeIndicator.style.marginTop = rows[currentTimeIndex].offsetTop + 'px';
        indicatorMoveTimer = setInterval(moveIndicatorInterval, 900000);
      }
    };

    function moveIndicatorInterval() {
      let rows = document.getElementsByClassName('conference-rooms-row');

      if (currentTimeIndex >= rows.length) {
        currentTimeIndicator.style.opacity = '0.0';
        clearInterval(indicatorMoveTimer);
      } else {
        currentTimeIndex += 1;
        currentTimeIndicator.style.marginTop = rows[currentTimeIndex].offsetTop + 'px';
      }
    };
  };
});

function removeColumnForCurrentTimeIndicatorCalculationsOnFirefox() {
  // column has to be removed because firefox calculates rowspans in tables differently than chrome,
  // and if this columns stays, the conference rooms layout breaks

  if(navigator.userAgent.indexOf("Firefox") != -1 )
  {
    var elements = document.getElementsByClassName("column-for-current-time-indicator-calculations");
    while(elements.length > 0){
      elements[0].parentNode.removeChild(elements[0]);
    }
  }
}
