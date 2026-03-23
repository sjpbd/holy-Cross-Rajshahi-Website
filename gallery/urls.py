from django.urls import path
from .views import GalleryListView, AlbumDetailView

urlpatterns = [
    path('', GalleryListView.as_view(), name='gallery_home'),
    path('album/<slug:slug>/', AlbumDetailView.as_view(), name='album_detail'),
]
