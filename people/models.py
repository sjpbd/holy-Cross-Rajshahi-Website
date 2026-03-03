from django.db import models


class Teacher(models.Model):
    """Faculty members"""
    SECTION_CHOICES = [
        ('pre_primary_primary', 'Pre Primary and Primary'),
        ('secondary', 'Secondary'),
        ('college', 'College'),
        ('office_staff', 'Office and Staffs'),
    ]

    DEPARTMENT_CHOICES = [
        ('science', 'Science'),
        ('arts', 'Arts'),
        ('commerce', 'Commerce'),
        ('english', 'English'),
        ('bangla', 'Bangla'),
        ('mathematics', 'Mathematics'),
        ('physics', 'Physics'),
        ('chemistry', 'Chemistry'),
        ('biology', 'Biology'),
        ('ict', 'ICT'),
        ('physical_education', 'Physical Education'),
        ('office', 'Office'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=200, help_text="e.g., 'Assistant Teacher', 'Senior Teacher'")
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, default='secondary')
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES)
    photo = models.ImageField(upload_to='teachers/', blank=True, help_text="Recommended size: 400x400px")
    bio = models.TextField(blank=True, help_text="Brief biography or qualifications")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first")
    is_active = models.BooleanField(default=True)
    joined_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True, null=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"

    def __str__(self):
        return f"{self.name} - {self.designation}"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            import uuid
            base_slug = slugify(self.name)
            if Teacher.objects.filter(slug=base_slug).exists():
                self.slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
            else:
                self.slug = base_slug
        super().save(*args, **kwargs)


class Administration(models.Model):
    """Administrative staff and leadership"""
    ROLE_CHOICES = [
        ('principal', 'Principal'),
        ('vice_principal', 'Vice Principal'),
        ('brother', 'Brother'),
        ('administrator', 'Administrator'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    designation = models.CharField(max_length=200)
    photo = models.ImageField(upload_to='administration/', blank=True, help_text="Recommended size: 400x400px")
    bio = models.TextField(blank=True)
    message = models.TextField(blank=True, help_text="Message from this administrator")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Administration"
        verbose_name_plural = "Administration"

    def __str__(self):
        return f"{self.name} - {self.role}"


class Staff(models.Model):
    """General staff members"""
    STAFF_CATEGORY_CHOICES = [
        ('office', 'Office Staff'),
        ('support', 'Support Staff'),
        ('security', 'Security'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=STAFF_CATEGORY_CHOICES, default='office')
    designation = models.CharField(max_length=200)
    photo = models.ImageField(upload_to='staff/', blank=True, help_text="Recommended size: 400x400px")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Staff"
        verbose_name_plural = "Staff"

    def __str__(self):
        return f"{self.name} - {self.designation}"
