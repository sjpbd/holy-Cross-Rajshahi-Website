from django.db import models
from django.utils.text import slugify

class Album(models.Model):
    """Album model representing folders and sub-folders"""
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='sub_albums',
        help_text="Select a parent album to make this a sub-folder."
    )
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='gallery/covers/', help_text="Thumbnail for the album folder.")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Album / Folder"
        verbose_name_plural = "Albums / Folders"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def photo_count(self):
        return self.photos.count()

class Photo(models.Model):
    """Photo model for individual images within an album"""
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='gallery/photos/')
    caption = models.CharField(max_length=400, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "Photo"
        verbose_name_plural = "Photos"

    def __str__(self):
        return f"Photo {self.id} in {self.album.title}"
