from django.shortcuts import render
from django.utils.text import slugify

# Create your views here.
from rest_framework import viewsets, status, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.decorators import api_view ,  permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from blog.models import Blog, Comment,Admin,CustomUser, DocumentContent


from .serializers import (
    BlogSerializer, BlogCreateSerializer,
    CommentSerializer,
    Blog_List_Serializer 
)
from services.generator import ( 
    generate_blog_by_promt,
    generate_blog_by_topic,
    regenerate_blog_by_feedback,
    generate_topic
)
from services.image_generator import Image_generator
import openai
from django.conf import settings
import cohere
from django.utils import timezone
from .serializers import AdminSerializer, UserSerializer, DocumentContentSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import JsonResponse
import json
import time

from PIL import Image  # for opening image files
import pytesseract     # for OCR text extraction
import pdfplumber
from docx import Document as DocxDocument
from io import BytesIO

 
from services.embeddings import get_top_k_chunks, embedding_model, splitter

class AdminViewSet(viewsets.ModelViewSet):
    queryset = Admin.objects.all()
    serializer_class = AdminSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    

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
                'admin': AdminSerializer(admin).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['patch']) 
    def updates(self, request):
        """
        PATCH /api/admins/profile/
        Updates the admin's profile and user fields.
        """
        admin = Admin.objects.get(user=request.user) 
        print(admin)
        serializer = self.get_serializer(admin, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
            # Add admin work_domain to the response
            response.data['work_domain'] = str(admin.work_domain)
            response.data['admin_uuid'] = str(admin.uuid)
        except (CustomUser.DoesNotExist, Admin.DoesNotExist):
            response.data['work_domain'] = None
            response.data['admin_uuid'] = None
            
        return response 
