$(document).ready(function(){
    let lang = JSON.parse($('#BACKEND_LANGUAGE_CODE').text());

    tinymce.init({
      selector: '.tinymce-comment',
      cleanup_on_startup: true,
      relative_urls: false,
      remove_script_host: false,
      convert_urls: true,
      menubar: false,
      height: '300',
      plugins: 'link emoticons',
      toolbar: 'bold italic underline | link image media |',
      branding: false,
      language: lang,
      file_picker_callback: intranetFilePicker,
    });
});