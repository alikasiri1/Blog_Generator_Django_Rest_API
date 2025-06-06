from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.routers import DefaultRouter
from .views import BlogViewSet, AdminViewSet, CommentViewSet, PublicBlogViewSet

# Admin router for authenticated admin operations
admin_router = DefaultRouter()
admin_router.register(r'blogs', BlogViewSet, basename='admin-blog')
# admin_router.register(r'sections', SectionViewSet, basename='admin-section')
admin_router.register(r'comments', CommentViewSet, basename='admin-comment')
admin_router.register(r'profil', AdminViewSet, basename='admin')

# Public router for viewing published blogs
public_router = DefaultRouter()
public_router.register(r'blogs', PublicBlogViewSet, basename='public-blog')

urlpatterns = [
    # Admin authentication endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Admin registration endpoint
    path('register/', AdminViewSet.as_view({'post': 'register'}), name='admin-register'),
    
    # Admin-specific endpoints (requires authentication)
    path('<uuid:admin_uuid>/admin/', include(admin_router.urls)),
    
    # Public endpoints (no authentication required)
    path('<uuid:admin_uuid>/', include(public_router.urls)),
    
    # Additional custom endpoints
    # path('sections/by_blog/', SectionViewSet.as_view({'get': 'by_blog'}), name='sections-by-blog'),
]  