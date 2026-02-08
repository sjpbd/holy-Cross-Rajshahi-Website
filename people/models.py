from django.db import models


class Teacher(models.Model):
    """Faculty members"""
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
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=200, help_text="e.g., 'Assistant Teacher', 'Senior Teacher'")
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES)
    photo = models.ImageField(upload_to='teachers/', blank=True, help_text="Recommended size: 400x400px")
    bio = models.TextField(blank=True, help_text="Brief biography or qualifications")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first")
    is_active = models.BooleanField(default=True)
    joined_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"

    def __str__(self):
        return f"{self.name} - {self.designation}"


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
