from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from .models import Album, Photo

class GalleryListView(ListView):
    """View to list all base albums (folders)"""
    model = Album
    template_name = 'gallery/gallery_list.html'
    context_object_name = 'albums'
    queryset = Album.objects.filter(is_active=True, parent=None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Photo Gallery"
        context['page_description'] = "Explore our school life through our photo gallery."
        return context

class AlbumDetailView(DetailView):
    """View to see sub-albums and photos within an album"""
    model = Album
    template_name = 'gallery/album_detail.html'
    context_object_name = 'album'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        album = self.get_object()
        context['sub_albums'] = album.sub_albums.filter(is_active=True)
        context['photos'] = album.photos.all()
        
        # Build Breadcrumbs
        breadcrumbs = []
        curr = album
        while curr:
            breadcrumbs.insert(0, curr)
            curr = curr.parent
        context['breadcrumbs'] = breadcrumbs
        
        context['page_title'] = f"{album.title} - Gallery"
        return context
