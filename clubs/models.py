from django.db import models
from django.urls import reverse


class Club(models.Model):
    """School clubs and organizations"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    logo = models.ImageField(upload_to='clubs/', blank=True, help_text="Club logo - Recommended size: 300x300px")
    motto = models.CharField(max_length=500, blank=True, help_text="Club motto or tagline")
    description = models.TextField(help_text="Detailed description of the club")
    objectives = models.TextField(blank=True, help_text="Club objectives and goals")
    
    # Contact
    coordinator_name = models.CharField(max_length=200, blank=True)
    coordinator_email = models.EmailField(blank=True)
    
    # Meta
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    established_year = models.PositiveIntegerField(null=True, blank=True, help_text="Year club was established")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Club"
        verbose_name_plural = "Clubs"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('club_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        """Auto-generate slug from name"""
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Club.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
