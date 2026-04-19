import json
from django.contrib.auth import get_user_model
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from django.utils.timezone import localtime
from django.conf import settings


class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    REQUEST_REMOVE_NOTIFICATION = 'remove.notification'
    RESPONSE_PUSH_NOTIFICATION = 'push.notification'
    RESPONSE_NOTIFICATION_REMOVED = 'notification.removed'
    REQUEST_CHECK_NOTIFICATION = 'check.notification'
    RESPONSE_NOTIFICATION_CHECKED = 'notification.checked'

    async def connect(self):
        if self.scope['user'].is_authenticated:
            await self.accept()
            await self.channel_layer.group_add(NotificationsConsumer.get_group_name(self.scope['user']),
                                                self.channel_name)
        else:
            await self.close()

    async def receive_json(self, request):
        if request['type'] == NotificationsConsumer.REQUEST_REMOVE_NOTIFICATION:
            await self.remove_notification(request['id'])
        elif request['type'] == NotificationsConsumer.REQUEST_CHECK_NOTIFICATION:
            await self.check_notification(request['id']) 

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(NotificationsConsumer.get_group_name(self.scope['user']),
                                                self.channel_name)

    async def push_notification(self, response):
        await self.send_json(response)

    async def send_user_notifications(self):
        user_notifications = await self.get_user_notifications()
        channel_layer = get_channel_layer()
        
        for notification in user_notifications:
            await channel_layer.group_send(
                NotificationsConsumer.get_group_name(self.scope['user']),
                NotificationsConsumer.get_push_notification_dict(notification)
            )

    @database_sync_to_async
    def get_user_notifications(self):
        return list(Notification.objects.filter(receiver=self.scope['user']).order_by('date_created')[:99])

    @staticmethod
    def get_group_name(user):
        return f'notification_channel_{user.username}_{user.id}'

    @staticmethod
    def get_push_notification_dict(notification):
        notification_dict = {
            'type': NotificationsConsumer.RESPONSE_PUSH_NOTIFICATION,
            'id': str(notification.id),
            'title': str(notification.title),
            'description': str(notification.description),
            'redirect_url': str(notification.redirect_url),
            'date_created':  localtime(notification.date_created).strftime(f'{settings.DATE_BACKEND_FORMAT} %H:%M'),
            'checked': str(notification.checked),
        }

        return notification_dict

    async def notification_removed(self, response):
        await self.send_json(response)

    async def remove_notification(self, notification_id):
        removed = await self.delete_notification(notification_id)

        if removed:
            channel_layer = get_channel_layer()

            await channel_layer.group_send(
                NotificationsConsumer.get_group_name(self.scope['user']),
                NotificationsConsumer.get_notification_removed_dict(notification_id)
            )
    
    @database_sync_to_async
    def delete_notification(self, id):
        try:
            notification = Notification.objects.get(id=id)
        except Notification.DoesNotExist:
            return False
        else:
            notification.delete()
            return True

    @staticmethod
    def get_notification_removed_dict(notification_id):
        notification_dict = {
            'type': NotificationsConsumer.RESPONSE_NOTIFICATION_REMOVED,
            'id': str(notification_id),
        }

        return notification_dict

    async def notification_checked(self, response):
        await self.send_json(response)

    async def check_notification(self, notification_id):
        checked = await self.set_notification_checked(notification_id)

        if checked:
            channel_layer = get_channel_layer()

            await channel_layer.group_send(
                NotificationsConsumer.get_group_name(self.scope['user']),
                NotificationsConsumer.get_notification_checked_dict(notification_id)
            )

    @database_sync_to_async
    def set_notification_checked(self, id):
        try:
            notification = Notification.objects.get(id=id)
        except Notification.DoesNotExist:
            return False
        else:
            if not notification.checked:
                notification.checked = True
                notification.save()
                return True
            
            return False

    @staticmethod
    def get_notification_checked_dict(notification_id):
        notification_dict = {
            'type': NotificationsConsumer.RESPONSE_NOTIFICATION_CHECKED,
            'id': str(notification_id),
        }

        return notification_dict
