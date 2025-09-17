from django.shortcuts import render
from django.utils.text import slugify
# Create your views here.
from rest_framework import viewsets, status, permissions
from rest_framework.exceptions import PermissionDenied
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
    regenerate_blog_by_feedback,
    generate_topic
)
from .image_generator import Image_generator
import openai
from django.conf import settings
import cohere
from django.utils import timezone
from .serializers import AdminSerializer, UserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import JsonResponse
import json
import time

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


class PublicBlogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for public access to published blogs.
    No authentication required.
    """
    serializer_class = BlogSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        work_domain = self.kwargs.get('work_domain')
        admin = get_object_or_404(Admin, work_domain=work_domain)
        return Blog.objects.filter(admin=admin, status='published')

class BlogViewSet(viewsets.ModelViewSet):
    serializer_class = BlogSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'slug'

    def get_queryset(self):
        try:
            # admin = Admin.objects.get(user=self.request.user)
            admin = get_object_or_404(Admin ,user=self.request.user)
            return Blog.objects.filter(admin=admin)
        except Admin.DoesNotExist:
            return Blog.objects.none()
    
    def get_object(self):
        slug = self.kwargs.get('slug')
        # admin = Admin.objects.get(user=self.request.user)
        admin = get_object_or_404(Admin ,user=self.request.user)
        blog = get_object_or_404(Blog, slug=slug, admin=admin)

        return blog
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = Blog_List_Serializer(queryset, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        admin = get_object_or_404(Admin ,user=self.request.user)
        # admin = Admin.objects.get(user=self.request.user)
        serializer.save(admin=admin)

    @action(detail=False, methods=['post'])
    def generate_topic(self, request):
        try:
            prompt = request.data.get('prompt')
            temp_doc_ids = request.data.getlist('documents')  # list of UUIDs to attach
            
            if not prompt:
                return JsonResponse({
                    'error': 'Prompt is required',
                    'status': 'failed'
                }, status=400)
            
            # Get the admin
            # admin = get_object_or_404(Admin ,user=self.request.user)
            # if admin.user != self.request.user:
            #     raise PermissionDenied("You are not authorized to access this admin profile.")
            
            # try:
            #     image_generator = Image_generator()
            #     task_id = image_generator.create_task_image("A serene lake at sunrise")
            #     if not task_id:
            #         image_url = ""
            #     image_info = image_generator.check_status()
            #     image_url = image_info['data']['response']['resultUrls'][0]
            #     # image_generator.download(image_info, 'lake.png')
            # except:
            #     image_url = ""
            image_url = "https://res.cloudinary.com/dbezwpqgi/image/upload/v1/media/admin_images/pic_3_v0ij9t"
            # Simulate topic generation (replace with your actual logic)
            # topic = generate_topic(prompt)
            time.sleep(4)
            topic = f"{prompt}. This is a simulated"
            
            # Create a blog with the generated topic
            blog_data = {
                'title': topic,  # Using response as title
                'image_url': image_url,
            }
            
            # Use your serializer to create the blog
            serializer = BlogSerializer(data=blog_data, context={'request': request})
            if serializer.is_valid():
                blog = serializer.save()
                
                # 1️⃣ Attach documents specified in request
                attached_count = 0
                for doc_id in temp_doc_ids:
                    try:
                        doc = Document.objects.get(uuid=doc_id, is_temporary=True)
                        doc.mark_as_attached(blog)
                        attached_count += 1
                    except Document.DoesNotExist:
                        continue

                # 2️⃣ Delete all other temporary documents of this admin that were not selected
                other_docs = Document.objects.filter(
                    is_temporary=True,
                    blog__isnull=True,
                    blog__admin=admin
                ).exclude(uuid__in=temp_doc_ids)
                deleted_count, _ = other_docs.delete()

                return JsonResponse({
                    'status': 'success',
                    'prompt': prompt,
                    'response': topic,
                    'blog_slug': blog.slug,
                    'timestamp': timezone.now().isoformat()
                })
            else:
                return JsonResponse({
                    'error': 'Failed to create blog',
                    'details': serializer.errors,
                    'status': 'failed'
                }, status=400)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data',
                'status': 'failed'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'status': 'failed'
            }, status=500)
    

    @action(detail=False, methods=['post'])
    def generate_contents(self, request, admin_uuid=None):
        print(request.data)
        topic = request.data.get('topic')
        
        if not topic:
            return Response(
                {'error': 'Topic is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # content = generate_blog_by_topic(topic)
            time.sleep(2)
            content = f"api:{topic}"
            print(content)

            
            return JsonResponse({
                'status': 'success',
                'topic': topic,
                'content': content,
                'timestamp': timezone.now().isoformat()
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data',
                'status': 'failed'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'status': 'failed'
            }, status=500)
    

    @action(detail=True, methods=['post'])
    def publish(self, request, slug=None):
        blog = self.get_object()
        
        blog.status = 'published'
        blog.published_at = timezone.now()
        blog.save()
        return Response(BlogSerializer(blog).data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, slug=None):
        blog = self.get_object()
        
        blog.status = 'draft'
        blog.published_at = None
        blog.save()
        return Response(BlogSerializer(blog).data)
    

    @action(detail=True, methods=['post'])
    def generate_content(self, request, slug=None):
        blog = self.get_object()

        # if blog.admin.user != request.user:
        #     return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        topic = request.data.get('topic')
        
        if not topic:
            return Response(
                {'error': 'Topic is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            
            # content = generate_blog_by_topic(topic)
            content = "this is a content test"
            time.sleep(4)
            print(content)
            blog.title = topic
            # blog.slug = slugify(topic)
            blog.content = ''.join(content.split('\n\n'))
            blog.save()
            
            return Response(BlogSerializer(blog).data)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def generate_content_by_promt(self, request, slug=None):
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
    def regenerate_content(self, request, slug=None):
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

    @action(detail=False, methods=['post'])
    def upload_temp_documents(self, request):
        """
        Upload multiple files (images, PDF, Word), extract text, create temporary Documents.
        """
        files = request.FILES.getlist('files')  # note: getlist for multiple files
        if not files:
            return Response({'error': 'No files provided'}, status=status.HTTP_400_BAD_REQUEST)

        created_docs = []

        for file in files:
            extracted_text = ""

            # Check file type
            if file.content_type.startswith("image/"):
                # Image: OCR
                image = Image.open(file)
                extracted_text = pytesseract.image_to_string(image, lang='fas+eng')

            elif file.content_type in [
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ]:
                # PDF or Word: extract text via textract
                file_bytes = BytesIO(file.read())
                extracted_text = textract.process(file_bytes).decode('utf-8', errors='ignore')

            else:
                continue  # skip unsupported files

            # Create temporary document
            doc = Document.objects.create(content_text=extracted_text, is_temporary=True)
            created_docs.append({
                'document_id': str(doc.uuid),
                'file_name': file.name,
                'text_preview': extracted_text[:200]
            })

        if not created_docs:
            return Response({'error': 'No valid files uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'success',
            'created_documents': created_docs
        }, status=status.HTTP_201_CREATED)

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
