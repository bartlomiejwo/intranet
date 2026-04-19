let conferenceRoomsNumberData = document.getElementById('conferenceRoomsNumberData');

if(conferenceRoomsNumberData !== null) {
    let conferenceRoomsNumber = JSON.parse(conferenceRoomsNumberData.textContent);
    let columns = document.getElementsByClassName('conference-rooms-table-column-header');

    Array.prototype.forEach.call(columns, function(column) {
        column.style.width = 100.0 / conferenceRoomsNumber + '%';
    });
}
