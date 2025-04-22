from django.urls import path
from apps.reports.views import DeadlineListView

urlpatterns = [
    path('deadline/', DeadlineListView.as_view(), name='deadline-list'),
]


