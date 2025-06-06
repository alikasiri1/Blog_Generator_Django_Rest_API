from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import AdminViewSet, BlogViewSet

router = DefaultRouter()
router.register(r'admin', AdminViewSet, basename='admin')
router.register(r'blogs', BlogViewSet, basename='blog')

urlpatterns = [
    path('', include(router.urls)),
] 