from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Blog(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('published', 'Published'),
        ],
        default='draft'
    )

    def __str__(self):
        return self.title

class Section(models.Model):
    blog = models.ForeignKey(Blog, related_name='sections', on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    order = models.IntegerField(default=0)
    section_type = models.CharField(
        max_length=20,
        choices=[
            ('introduction', 'Introduction'),
            ('body', 'Body'),
            ('conclusion', 'Conclusion'),
        ],
        default='body'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.blog.title} - {self.section_type}"

class Comment(models.Model):
    section = models.ForeignKey(Section, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.section.blog.title}" 