from django.urls import path
from .views import ResourceListView, track_download, proxy_external_resource

urlpatterns = [
    path('', ResourceListView.as_view(), name='resources'),
    path('track/<int:pk>/', track_download, name='track_download'),
    path('proxy/<int:pk>/', proxy_external_resource, name='proxy_external_resource'),
]
