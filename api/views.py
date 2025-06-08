from django.shortcuts import render
from django.utils.text import slugify
# Create your views here.
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.decorators import api_view ,  permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from blog.models import Blog, Comment,Admin,CustomUser
from .serializers import (
    BlogSerializer, BlogCreateSerializer,
    CommentSerializer,
    Blog_List_Serializer 
)
from .generator import (
    generate_blog_by_promt,
    generate_blog_by_topic,
    regenerate_blog_by_feedback
)
import openai
from django.conf import settings
import cohere
from django.utils import timezone
from .serializers import AdminSerializer, UserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from rest_framework_simplejwt.views import TokenObtainPairView


class AdminViewSet(viewsets.ModelViewSet):
    queryset = Admin.objects.all()
    serializer_class = AdminSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'register':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Admin.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            admin = Admin.objects.create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'admin': AdminSerializer(admin).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PublicBlogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for public access to published blogs.
    No authentication required.
    """
    serializer_class = BlogSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        admin_uuid = self.kwargs.get('admin_uuid')
        admin = get_object_or_404(Admin, uuid=admin_uuid)
        return Blog.objects.filter(admin=admin, status='published')

class BlogViewSet(viewsets.ModelViewSet):
    serializer_class = BlogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        admin_uuid = self.kwargs.get('admin_uuid')
        admin = get_object_or_404(Admin, uuid=admin_uuid)
        
        # Ensure the authenticated user is the admin
        if admin.user != self.request.user:
            return Blog.objects.none()
            
        return Blog.objects.filter(admin=admin)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = Blog_List_Serializer(queryset, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        admin_uuid = self.kwargs.get('admin_uuid')
        admin = get_object_or_404(Admin, uuid=admin_uuid)
        
        # Ensure the authenticated user is the admin
        if admin.user != self.request.user:
            raise permissions.PermissionDenied("You are not authorized to create blogs for this admin.")
            
        serializer.save(admin=admin)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None, admin_uuid=None):
        blog = self.get_object()
        if blog.admin.user != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        blog.status = 'published'
        blog.published_at = timezone.now()
        blog.save()
        return Response(BlogSerializer(blog).data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None, admin_uuid=None):
        blog = self.get_object()
        if blog.admin.user != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        blog.status = 'draft'
        blog.published_at = None
        blog.save()
        return Response(BlogSerializer(blog).data)

    @action(detail=True, methods=['post'])
    def generate_content(self, request, pk=None, admin_uuid=None):
        blog = self.get_object()
        topic = request.data.get('topic')
        
        if not topic:
            return Response(
                {'error': 'Topic is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            
            content = generate_blog_by_topic(topic)
            print(content)
            blog.title = topic
            blog.slug = slugify(topic)
            blog.content = ''.join(content.split('\n\n'))
            blog.save()
            
            return Response(BlogSerializer(blog).data)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    @action(detail=True, methods=['post'])
    def generate_content_by_promt(self, request, pk=None, admin_uuid=None):
        blog = self.get_object()
        promt = request.data.get('promt')
        topic = request.data.get('topic')
        if not promt:
            return Response(
                {'error': 'promt is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            
            content = generate_blog_by_promt(promt , topic)
            print(content)
            blog.content = ''.join(content.split('\n\n'))
            blog.save()
            
            return Response(BlogSerializer(blog).data)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

    @action(detail=True, methods=['post'])
    def regenerate_content(self, request, pk=None, admin_uuid=None):
        blog = self.get_object()
        feedback = request.data.get('feedback')
        
        if not feedback:
            return Response(
                {'error': 'Feedback is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            
            content = regenerate_blog_by_feedback(blog.content , feedback)
            print(content)
            blog.content = ''.join(content.split('\n\n'))
            blog.save()
            
            return Response(BlogSerializer(blog).data)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        admin_uuid = self.kwargs.get('admin_uuid')
        admin = get_object_or_404(Admin, uuid=admin_uuid)
        
        # Ensure the authenticated user is the admin
        if admin.user != self.request.user:
            return Comment.objects.none()
            
        return Comment.objects.filter(section__blog__admin=admin)

    def perform_create(self, serializer):
        section_id = self.request.data.get('section')
        section = get_object_or_404(Section, id=section_id)
        serializer.save(user=self.request.user, section=section) 

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        # Get username from request data
        username = request.data.get('username')
        
        # Get the user from the username
        try:
            user = CustomUser.objects.get(username=username)
            admin = Admin.objects.get(user=user) 
            # Add admin UUID to the response
            response.data['admin_uuid'] = str(admin.uuid)
        except (CustomUser.DoesNotExist, Admin.DoesNotExist):
            response.data['admin_uuid'] = None
            
        return response 
