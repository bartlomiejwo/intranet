from django.contrib import admin
from .models import Location, ConferenceRoom, Meeting, Participant
from .forms import ConferenceRoomForm, MeetingFormAdmin


class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'moderator_group']
    ordering = ['moderator_group', 'name']


class ConferenceRoomAdmin(admin.ModelAdmin):
    form = ConferenceRoomForm
    list_display = ['name', 'position', 'location']
    ordering = ['location', 'position',]


class ParticipantInline(admin.StackedInline):
    model = Participant
    extra = 1


class MeetingAdmin(admin.ModelAdmin):
    form = MeetingFormAdmin
    inlines = [ParticipantInline,]
    list_display = ['title', 'conference_room', 'date', 'start_time', 'end_time', 'status']
    ordering = ['-date', 'conference_room', 'start_time', 'end_time']
    search_fields = ['created_by__username', 'created_by__first_name', 'created_by__last_name', 
                        'conference_room__name', 'status']


admin.site.register(Location, LocationAdmin)
admin.site.register(ConferenceRoom, ConferenceRoomAdmin)
admin.site.register(Meeting, MeetingAdmin)
