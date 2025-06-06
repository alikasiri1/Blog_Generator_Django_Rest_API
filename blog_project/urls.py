from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('api.urls.auth')),
    path('api/blogs/', include('api.urls.blogs')),
    path('api/comments/', include('api.urls.comments')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) # for media files
