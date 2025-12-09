from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import (
    AdminViewSet, 
    CustomTokenObtainPairView
)
from blog.views import BlogViewSet, PublicBlogViewSet

# Admin router for authenticated admin operations
admin_router = DefaultRouter() 
admin_router.register(r'blogs', BlogViewSet, basename='admin-blog')
# admin_router.register(r'sections', SectionViewSet, basename='admin-section')
# admin_router.register(r'comments', CommentViewSet, basename='admin-comment')
admin_router.register(r'profile', AdminViewSet, basename='admin')

# Public router for viewing published blogs
public_router = DefaultRouter()
public_router.register(r'blogs', PublicBlogViewSet, basename='public-blog')

urlpatterns = [
    # Admin authentication endpoints
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', AdminViewSet.as_view({'post': 'register'}), name='admin-register'), # Admin registration endpoint
    path('admin/', include(admin_router.urls)),
    path('<slug:work_domain>/', include(public_router.urls)), # Public routes also by work_domain
]  
