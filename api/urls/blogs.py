from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import BlogViewSet, SectionViewSet

router = DefaultRouter()
router.register(r'', BlogViewSet, basename='blog')
router.register(r'sections', SectionViewSet, basename='section')

urlpatterns = [
    path('', include(router.urls)),
    # path('sections/', SectionViewSet.as_view({'get': 'list', 'post': 'create'}), name='section-list'),
    path('sections/by_blog/', SectionViewSet.as_view({'get': 'by_blog'}), name='sections-by-blog'),
] 
urlpatterns += router.urls