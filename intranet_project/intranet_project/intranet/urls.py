from django.urls import path
from . import views


app_name = 'intranet'

urlpatterns = [
    path('', views.PostListView.as_view(), name='home'),
    path('post/<int:pk>/', views.PostDetailView.as_view(), name='post_detail'),
    path('post/new/', views.PostCreateView.as_view(), name='post_create'),
    path('post/<int:pk>/update/', views.PostUpdateView.as_view(), name='post_update'),
    path('post/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    path('post/<int:pk>/toggle_like_state/', views.PostToggleLikeStateAjaxView.as_view(),
        name='post_toggle_like_state_ajax'),
    path('post/<int:pk>/toggle_pinned_state/', views.post_toggle_pinned_state, 
        name='post_toggle_pinned_state'),
    path('user_posts/', views.UserPostListView.as_view(), name='user_posts'),
    path('comment/<int:pk>/update/', views.CommentUpdateView.as_view(), name='comment_update'),
    path('comment/<int:pk>/delete/', views.CommentDeleteView.as_view(), name='comment_delete'),
    path('comment/<int:pk>/change_toggle_state/', views.CommentToggleLikeStateAjaxView.as_view(),
            name='comment_toggle_like_state_ajax'),
]