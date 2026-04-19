import django.dispatch


meeting_pending = django.dispatch.Signal()
meeting_accepted = django.dispatch.Signal()
meeting_rejected = django.dispatch.Signal()
meeting_decision_changed_to_accepted = django.dispatch.Signal()
meeting_decision_changed_to_rejected = django.dispatch.Signal()
accepted_meeting_updated = django.dispatch.Signal()
accepted_meeting_deleted = django.dispatch.Signal()
