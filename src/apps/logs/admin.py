from django.contrib import admin
from .models import HistoryActionJournal

@admin.register(HistoryActionJournal)
class HistoryActionJournalAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'object_repr', 'created_at')
    list_filter = ('action', 'model_name', 'user')
    search_fields = ('object_repr', 'model_name', 'change_message')
    readonly_fields = ('user', 'action', 'model_name', 'object_repr', 'object_id', 'change_message', 'created_at')
