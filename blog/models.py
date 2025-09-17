from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import uuid

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return self.username

class Admin(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    work_domain = models.SlugField(max_length=50, unique=True, null = True , blank = True)
    image = models.ImageField(upload_to='admin_images/', null=True, blank=True) 
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.uuid})"

class Blog(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name='blogs', null = True , blank = True)
    title = models.CharField(max_length=200)
    content = models.TextField(null = True , blank = True)
    slug = models.SlugField(max_length=200, null = True , blank = True)
    image_url = models.URLField(max_length=500, null=True, blank=True) 
    image = models.ImageField(upload_to='blog_images/', null=True, blank=True)  
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug or Blog.objects.get(pk=self.pk).title != self.title:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Blog.objects.filter(slug=slug, admin=self.admin).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)




    class Meta:
        ordering = ['-created_at']
        unique_together = ('admin', 'slug')  # slug unique per admin

    def __str__(self):
        return self.title


class DocumentContent(models.Model):
    TYPE_CHOICES = [('PDF','PDF'), ('IMG','Image')]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')  
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    text_content = models.TextField()
    is_temporary = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def mark_as_attached(self, blog):
        """وقتی بلاگ ساخته شد این متد را صدا بزنید"""
        self.blog = blog
        self.is_temporary = False
        self.save()

    def __str__(self):
        return f"{self.title} ({self.blog.title})"

class Comment(models.Model):
    # section = models.ForeignKey(Section, related_name='comments', on_delete=models.CASCADE)
    blog = models.ForeignKey(Blog, related_name='sections', on_delete=models.CASCADE, null = True , blank = True)

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.section.blog.title}" 
