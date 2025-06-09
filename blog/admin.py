from django.contrib import admin
from .models import Blog, Admin  ,CustomUser # Adjust import if models are in another app

admin.site.register(CustomUser) 

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'admin', 'status', 'slug', 'created_at', 'published_at')
    search_fields = ('title', 'content', 'slug')
    list_filter = ('status', 'created_at', 'published_at')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Admin)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'work_domain', 'is_active', 'uuid', 'created_at')
    search_fields = ('user__username', 'work_domain')
