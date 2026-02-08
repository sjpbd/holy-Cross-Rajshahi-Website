from django.urls import path
from .views import ResourceListView, track_download

urlpatterns = [
    path('', ResourceListView.as_view(), name='resources'),
    path('track/<int:pk>/', track_download, name='track_download'),
]
