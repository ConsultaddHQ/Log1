from django.contrib import admin

from utils_app.admin import ExportCsvMixin
from messaging.models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv"]
    list_display = ('id', 'user1', 'user2', 'modified', 'created')
    search_fields = ('id', 'user1__owner__employee_name', 'user2')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv"]
    list_filter = ('is_sent',)
    list_display = ('id', 'conversation', 'text', 'is_sent', 'created')
    search_fields = ('id', 'conversation__user1__owner__employee_name', 'user2')
