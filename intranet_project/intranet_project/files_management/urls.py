from django.urls import path
from . import views


app_name = 'files_management'

urlpatterns = [
    path('upload_ajax/', views.UploadFileAjaxView.as_view(), name='upload_file_ajax'),
    path('user_files/', views.UserIntranetFilesListView.as_view(), name='user_files'),
    path('upload/', views.IntranetFileCreateView.as_view(), name='upload_file'),
    path('delete_files/', views.delete_intranet_files, name='delete_files'),
]
