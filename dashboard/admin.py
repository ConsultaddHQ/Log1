from django.contrib import admin
from .models import QuickActions

@admin.register(QuickActions)
class QuickActionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user')
    filter_horizontal = ('add_consultants', 'search_consultants')
