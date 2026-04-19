function intranetFilePicker(callback, value, meta) {
  var filetype = '.pdf, .txt, .zip, .rar, .7z, .doc, .docx, .xls, .xlsx, .ppt, ' + 
                  '.pptx, .jpg, .jpeg, .png, .gif, .mp3, .mp4';

  if(meta.filetype == 'image') {
    filetype = '.jpg, .jpeg, .png, .gif';
  } else if(meta.filetype == 'media') {
    filetype = '.mp3, .mp4';
  }

  var input = document.createElement('input');
  input.setAttribute('type', 'file');
  input.setAttribute('accept', filetype);
  input.click();

  input.onchange = function () {
    var file = this.files[0];
    var formData = new FormData();
    formData.append('csrfmiddlewaretoken', csrfToken);
    formData.append('file', file, file.name);

    $.ajax({
      url: fileUploadUrl,
      data: formData,
      type: 'post',
      processData: false,
      contentType: false,
      beforeSend: function() {
        if(isLoadingUIEnabled()) {
          showUploadingInfo();
        }
      },
      success: function(response) {
        if (response.ok) {

          if(meta.filetype == 'file') {
            callback(response.file_url, { title: response.filename, text: response.filename });
          } else if(meta.filetype == 'image') {
            callback(response.file_url, { alt: response.filename });
          } else if(meta.filetype == 'media') {
            callback(response.file_url, {});
          }
          
        } else {
          alert(response.message);
        }

        input.remove();
      },
      error: function(response) {
        if (response.responseJSON){
          alert('Błąd ' + response.status + ': ' + response.responseJSON.message);
        } else if (response.statusText) {
          alert(response.status + ' ' + response.statusText);
        } else {
          alert('Błąd ' + response.status);
        }

        input.remove();
      },
      complete: function() {
        if(isLoadingUIEnabled()) {
          hideUploadingInfo();
        }
      },
    });
  };
}

function showUploadingInfo() {
  $(document.body).append(
    '<div class="modal" id="fileUploadingInfoModal" tabindex="-1" role="dialog" data-backdrop="static" aria-labelledby="exampleModalCenterTitle" aria-hidden="true">' +
      '<div class="modal-dialog modal-dialog-centered" role="document">' +
        '<div class="modal-content">' +
          '<div class="modal-header">' +
            '<h5 class="modal-title">Przesyłanie pliku</h5>' +
          '</div>' +
          '<div class="modal-body">'+
            'Trwa przesyłanie pliku... ' +
            '<div class="spinner-border text-primary" role="status">' +
              '<span class="sr-only">Trwa przesyłanie pliku...</span>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>'
  );

  $('#fileUploadingInfoModal').css('z-index', '9999');

  $("#fileUploadingInfoModal").on('show.bs.modal', function (e) {
    setTimeout(function(){
      $('.modal-backdrop').css('z-index', '9998');
    });
  });

  $("#fileUploadingInfoModal").on('hidden.bs.modal', function () {
    $(this).data('bs.modal', null);
  });

  $('#fileUploadingInfoModal').modal('show');
}

function hideUploadingInfo() {
  $('#fileUploadingInfoModal').modal('hide');
}

function isLoadingUIEnabled() {
  if (typeof showFileUploadLoading !== 'undefined') {
    return showFileUploadLoading;
  }

  return true;
}