from django.contrib import admin
from .models import Blog, Admin  ,CustomUser, DocumentContent # Adjust import if models are in another app

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


@admin.register(DocumentContent)
class DocumentContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'type', 'is_temporary', 'blog', 'uploaded_at')
    search_fields = ('title', 'text_content', 'user__username', 'blog__title')
    list_filter = ('type', 'is_temporary', 'uploaded_at')
    readonly_fields = ('uuid', 'uploaded_at')
    fields = ('uuid','user','blog','title','type','text_content','is_temporary','uploaded_at','summarize_text',)
    raw_id_fields = ('user', 'blog')  # useful if you have many users/blogs

    def get_queryset(self, request):
        # optionally customize queryset (e.g., superuser sees all)
        return super().get_queryset(request).select_related('user', 'blog')