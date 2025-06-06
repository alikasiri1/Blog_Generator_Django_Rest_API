from django.shortcuts import render
from django.utils.text import slugify
# Create your views here.
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.decorators import api_view ,  permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from blog.models import Blog, Comment,Admin
from .serializers import (
    BlogSerializer, BlogCreateSerializer,
    CommentSerializer, CommentCreateSerializer,
    Blog_List_Serializer 
)
import openai
from django.conf import settings
import cohere
from django.utils import timezone
from .serializers import AdminSerializer, UserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User


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

    # def get_serializer_class(self):
    #     if self.action == 'list':
    #         return Blog_List_Serializer  # for GET /blogs/
    #     return BlogSerializer  # for GET /blogs/<id>/, POST, PUT, etc.

    # def get_queryset(self):
    #     return Blog.objects.all()
    #     # return Blog.objects.filter(author=self.request.user)
    
    # def perform_create(self, serializer):
    #     serializer.save(author=self.request.user)

    # @action(detail=True, methods=['post'])
    # def generate_content(self, request, pk=None):
    #     blog = self.get_object()
    #     topic = request.data.get('topic')
        
    #     if not topic:
    #         return Response(
    #             {'error': 'Topic is required'},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     try:
    #         # Initialize OpenAI client
    #         client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
    #         # Generate blog content using OpenAI
    #         response = client.chat.completions.create(
    #             model="gpt-3.5-turbo",
    #             messages=[
    #                 {"role": "system", "content": "You are a professional blog writer. Generate a well-structured blog post."},
    #                 {"role": "user", "content": f"Write a blog post about {topic}. Include an introduction, main sections, and a conclusion."}
    #             ]
    #         )
            
    #         content = response.choices[0].message.content
            
    #         # Split content into sections
    #         sections = content.split('\n\n')
            
    #         # Create sections in the database
    #         for i, section_content in enumerate(sections):
    #             if section_content.strip():
    #                 section_type = 'introduction' if i == 0 else 'conclusion' if i == len(sections) - 1 else 'body'
    #                 Section.objects.create(
    #                     blog=blog,
    #                     content=section_content.strip(),
    #                     order=i,
    #                     section_type=section_type
    #                 )
            
    #         return Response(BlogSerializer(blog).data)
            
    #     except Exception as e:
    #         return Response(
    #             {'error': str(e)},
    #             status=status.HTTP_500_INTERNAL_SERVER_ERROR
    #         )
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
            # Initialize Cohere client
            co = cohere.Client(settings.COHERE_API_KEY)
            
            # Generate blog content using Cohere
            response = co.generate(
                model='command',
                prompt=f"""You are a professional blog writer. Generate a well-structured blog post about {topic}.
                
                Include the following sections:
                1. Introduction
                2. Several main sections with detailed content
                3. Conclusion
                
                Make sure the blog post is comprehensive and well-formatted with clear section breaks.""",
                max_tokens=2000,
                temperature=0.7
            )
            
            content = response.generations[0].text
            print(content)
            # Split content into sections
            # sections = content.split('\n\n')
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
    def regenerate_content(self, request, pk=None, admin_uuid=None):
        blog = self.get_object()
        feedback = request.data.get('feedback')
        
        if not feedback:
            return Response(
                {'error': 'Feedback is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Initialize Cohere client
            co = cohere.Client(settings.COHERE_API_KEY)
            
            # Generate blog content using Cohere
            response = co.generate(
                model='command',
                prompt=f"""You are a professional blog writer. Revise the content based on the feedback.
                Original content: {blog.content}\nFeedback: {feedback}\nPlease revise the content accordingly.""",
                temperature=0.7
            )
            
            content = response.generations[0].text
            print(content)
            # Split content into sections
            # sections = content.split('\n\n')
            
            blog.content = ''.join(content.split('\n\n'))
            blog.save()
            
            return Response(BlogSerializer(blog).data)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
# class SectionViewSet(viewsets.ModelViewSet):
#     serializer_class = SectionSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         admin_uuid = self.kwargs.get('admin_uuid')
#         admin = get_object_or_404(Admin, uuid=admin_uuid)
        
#         # Ensure the authenticated user is the admin
#         if admin.user != self.request.user:
#             return Section.objects.none()
            
#         return Section.objects.filter(blog__admin=admin)

#     def list(self, request, *args, **kwargs):
#         """
#         Custom list implementation with enhanced error handling
#         """
#         try:
#             queryset = self.filter_queryset(self.get_queryset())
#             page = self.paginate_queryset(queryset)
#             if page is not None:
#                 serializer = self.get_serializer(page, many=True) 
#                 return self.get_paginated_response(serializer.data)

#             serializer = self.get_serializer(queryset, many=True)
#             return Response(serializer.data)
#         except Exception as e:
#             return Response(
#                 {"error": f"Failed to retrieve sections: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

#     @action(detail=False, methods=['get'])
#     def by_blog(self, request):
#         """
#         Custom endpoint to get sections by blog ID
#         Example: /api/blogs/sections/by_blog/?blog_id=2
#         """
#         blog_id = request.query_params.get('blog_id')
#         if not blog_id:
#             return Response(
#                 {"error": "blog_id parameter is required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             sections = self.get_queryset().filter(blog_id=blog_id)
#             serializer = self.get_serializer(sections, many=True)
#             return Response(serializer.data)
#         except Exception as e:
#             return Response(
#                 {"error": str(e)},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#     @action(detail=True, methods=['post'])
#     def regenerate_content(self, request, pk=None):
#         section = self.get_object()
#         print(section)
#         feedback = request.data.get('feedback')
        
#         if not feedback:
#             return Response(
#                 {'error': 'Feedback is required'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
            
#             co = cohere.Client(settings.COHERE_API_KEY)
#             # Generate new content based on feedback
#             response = co.generate(
#                 model='command',
#                 prompt=f"""You are a professional blog writer. Revise the content based on the feedback.
#                 Original content: {section.content}\nFeedback: {feedback}\nPlease revise the content accordingly.""",
#                 temperature=0.7
#             )
            
#             new_content = response.generations[0].text
#             new_content = ''.join(new_content.split('\n\n'))
#             print(new_content)
#             # Initialize OpenAI client
#             # client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
#             # response = client.chat.completions.create(
#             #     model="gpt-3.5-turbo",
#             #     messages=[
#             #         {"role": "system", "content": "You are a professional blog writer. Revise the content based on the feedback."},
#             #         {"role": "user", "content": f"Original content: {section.content}\nFeedback: {feedback}\nPlease revise the content accordingly."}
#             #     ]
#             # )
            
#             # new_content = response.choices[0].message.content
#             section.content = new_content
#             section.save()
            
#             return Response(SectionSerializer(section).data)
            
#         except Exception as e:
#             return Response(
#                 {'error': str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )



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