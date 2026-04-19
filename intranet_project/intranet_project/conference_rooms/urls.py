from django.urls import path
from . import views


app_name = 'conference_rooms'

urlpatterns = [
    path('user_meetings/accepted/', views.UserAcceptedMeetingsListView.as_view(), name='user_meetings_accepted'),
    path('user_meetings/pending/', views.UserPendingMeetingsListView.as_view(), name='user_meetings_pending'),
    path('user_meetings/rejected/', views.UserRejectedMeetingsListView.as_view(), name='user_meetings_rejected'),
    path('upcoming_meetings/', views.UpcomingMeetingsListView.as_view(), name='upcoming_meetings'),
    path('conference_rooms_pdf/<slug:date_str>/', views.conference_rooms_pdf, name='conference_rooms_pdf'),
    path('conference_room_pdf/<int:room_id>/<slug:date_str>/', views.conference_room_pdf, name='conference_room_pdf'),
    path('moderation/', views.MeetingsModerationListView.as_view(), name='meetings_moderation'),
    path('moderation/history/', views.MeetingsModerationHistoryListView.as_view(), name='meetings_moderation_history'),
    path('meeting/<int:id>/accept/', views.MeetingAcceptView.as_view(), name='meeting_accept'),
    path('meeting/<int:id>/reject/', views.MeetingRejectView.as_view(), name='meeting_reject'),
    path('meeting/<int:id>/change_decision_to_accepted/', views.MeetingDecisionChangeToAcceptedView.as_view(),
            name='meeting_decision_change_to_accepted'),
    path('meeting/<int:id>/change_decision_to_rejected/', views.MeetingDecisionChangeToRejectedView.as_view(),
        name='meeting_decision_change_to_rejected'),
    path('meeting/new/', views.MeetingCreateView.as_view(), name='meeting_create'),
    path('meeting/<int:pk>/', views.MeetingDetailView.as_view(), name='meeting_detail'),
    path('meeting/<int:pk>/update/', views.MeetingUpdateView.as_view(), name='meeting_update'),
    path('meeting/<int:pk>/delete/', views.MeetingDeleteView.as_view(), name='meeting_delete'),
    path('<int:room_id>/<slug:date_str>/', views.conference_room, name='conference_room'),
    path('<slug:date_str>/', views.conference_rooms, name='conference_rooms'),
]
