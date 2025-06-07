from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return self.username

class Admin(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
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
    slug = models.SlugField(max_length=200, unique=True, null = True , blank = True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# class Section(models.Model):
#     blog = models.ForeignKey(Blog, related_name='sections', on_delete=models.CASCADE)
#     title = models.CharField(max_length=200, blank=True)
#     content = models.TextField()
#     order = models.IntegerField(default=0)
#     section_type = models.CharField(
#         max_length=20,
#         choices=[
#             ('introduction', 'Introduction'),
#             ('body', 'Body'),
#             ('conclusion', 'Conclusion'),
#         ],
#         default='body'
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ['order']

#     def __str__(self):
#         return f"{self.blog.title} - {self.section_type}"
    
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
    
# class Blog(models.Model):
#     title = models.CharField(max_length=200)
#     author = models.ForeignKey(User, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     status = models.CharField(
#         max_length=20,
#         choices=[
#             ('draft', 'Draft'),
#             ('published', 'Published'),
#         ],
#         default='draft'
#     )

#     def __str__(self):
#         return self.title

# class Section(models.Model):
#     blog = models.ForeignKey(Blog, related_name='sections', on_delete=models.CASCADE)
#     title = models.CharField(max_length=200, blank=True)
#     content = models.TextField()
#     order = models.IntegerField(default=0)
#     section_type = models.CharField(
#         max_length=20,
#         choices=[
#             ('introduction', 'Introduction'),
#             ('body', 'Body'),
#             ('conclusion', 'Conclusion'),
#         ],
#         default='body'
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ['order']

#     def __str__(self):
#         return f"{self.blog.title} - {self.section_type}"

# class Comment(models.Model):
#     section = models.ForeignKey(Section, related_name='comments', on_delete=models.CASCADE)
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     content = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)

#     class Meta:
#         ordering = ['created_at']

#     def __str__(self):
#         return f"Comment by {self.user.username} on {self.section.blog.title}" 