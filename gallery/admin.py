from django.contrib import admin, messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import path
from django.utils.html import format_html
from .models import Album, Photo

class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 1
    fields = ['image', 'caption', 'order']

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ['title', 'parent', 'is_active', 'order', 'photo_count_display', 'manage_photos_link']
    list_filter = ['parent', 'is_active']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['order', 'is_active']
    inlines = [PhotoInline]
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'parent', 'cover_image', 'description')
        }),
        ('Settings', {
            'fields': ('order', 'is_active'),
        }),
    )

    def photo_count_display(self, obj):
        return obj.photos.count()
    photo_count_display.short_description = "Photos"

    def manage_photos_link(self, obj):
        url = f"bulk-upload/{obj.id}/"
        return format_html('<a class="button" href="{}">Bulk Upload Photos</a>', url)
    manage_photos_link.short_description = "Action"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-upload/<int:album_id>/', self.admin_site.admin_view(self.bulk_upload_view), name='album-bulk-upload'),
        ]
        return custom_urls + urls

    def bulk_upload_view(self, request, album_id):
        album = get_object_or_404(Album, pk=album_id)
        
        if request.method == 'POST':
            files = request.FILES.getlist('photos')
            if files:
                for f in files:
                    Photo.objects.create(album=album, image=f)
                messages.success(request, f"Successfully uploaded {len(files)} photos to {album.title}")
            else:
                messages.error(request, "No files were selected.")
            return redirect('admin:gallery_album_changelist')

        context = {
            **self.admin_site.each_context(request),
            'album': album,
            'title': f"Bulk Photo Upload to {album.title}",
        }
        return render(request, 'admin/gallery/bulk_upload.html', context)

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['id', 'album', 'caption', 'order', 'image_thumbnail']
    list_filter = ['album']
    search_fields = ['caption', 'album__title']
    list_editable = ['order']

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: auto;" />', obj.image.url)
        return "-"
    image_thumbnail.short_description = "Preview"
