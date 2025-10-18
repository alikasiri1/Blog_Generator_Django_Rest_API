# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Blog, Comment,Admin, DocumentContent
from django.utils.text import slugify

from api.serializers import (
    BlogSerializer,
    Blog_List_Serializer 
)
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import JsonResponse
import json
import time

from PIL import Image  # for opening image files
import pytesseract     # for OCR text extraction
import pdfplumber
from docx import Document as DocxDocument
from services.embeddings import  splitter, count_tokens
from services.generate import summarize_chunk,generate_blog, generate_card_topics
from services.image_generator import Image_generator
# Create your views here.


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
            temp_doc_ids = request.data.get('documents')  # list of UUIDs to attach
            num_cards = int(request.data.get('num_cards'))

            if num_cards:
                if num_cards > 10 or num_cards < 1:
                    return JsonResponse({
                    'error': 'num_cards should be less than 10 and greater than 1',
                    'status': 'failed'
                }, status=400)
            else:
                return JsonResponse({
                    'error': 'num_cards is required',
                    'status': 'failed'
                }, status=400)

            if not prompt:
                return JsonResponse({
                    'error': 'Prompt is required',
                    'status': 'failed'
                }, status=400)
            


            # Delete all other temporary documents of this admin that were not selected
            other_docs = DocumentContent.objects.filter(
                is_temporary=True,
                blog__isnull=True,
                user=request.user
            ).exclude(uuid__in=temp_doc_ids)
            deleted_count, _ = other_docs.delete()

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
            documents = []
            for doc_id in temp_doc_ids:
                try:
                    doc_text = ""
                    doc = DocumentContent.objects.get(uuid=doc_id, is_temporary=True)
                    if doc.type == 'IMG':
                        doc.text_content = extracted_img_text(doc.url)
                        doc_text = doc.text_content
                        doc.save()
                    else:
                        chunks = splitter.split_text(doc.text_content)
                        if len(chunks) < 2:
                            doc_text = doc.text_content
                        else:
                            if count_tokens(chunks[-1]) < 10000:
                                chunks[-2] += " " + chunks[-1]
                                chunks.pop(-1)
                            
                            summaries = []
                            for i, chunk in enumerate(chunks):
                                print(f"⏳ Summarizing chunk {i+1}/{len(chunks)} ...")
                                try:
                                    summary = summarize_chunk(chunk)
                                    summaries.append(summary)
                                    doc_text += summary['title'] + "\n"
                                except Exception as e:
                                    print(f"❌ Error summarizing chunk {i+1}: {e}")

                            print("✅ All chunks summarized successfully")
                            doc.summaries = summaries
                            doc.save()

                except DocumentContent.DoesNotExist:
                    continue
            print(doc_text)
            # topics = generate_topic(prompt , doc_text, num_cards)

            # Simulate topic generation (replace with your actual logic)
            time.sleep(1)
            topics = [f"{prompt}. This is a simulated","body",'conclusion']
            
            content = []
            for topic in topics[1:]:
                content.append({'heading': topic, 'body': ""})
            # Create a blog with the generated topic
            blog_data = {
                'title': topics[0],  # Using response as title
                'image_url': image_url,
                'content': content,
            }
            
            # Use your serializer to create the blog
            serializer = BlogSerializer(data=blog_data, context={'request': request})
            if serializer.is_valid():
                blog = serializer.save()
                
                # Attach documents specified in request
                attached_count = 0
                for doc_id in temp_doc_ids:
                    try:
                        doc = DocumentContent.objects.get(uuid=doc_id, is_temporary=True)
                        doc.mark_as_attached(blog)
                        attached_count += 1
                    except DocumentContent.DoesNotExist:
                        continue

                return JsonResponse({
                    'status': 'success',
                    'prompt': prompt,
                    'title': topics[0],
                    'topics': topics,
                    'blog_slug': blog.slug,
                    'attached_documents': attached_count,
                    'deleted_other_temp_documents': deleted_count,
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
        try:
            blog = self.get_object()
            title = request.data.get('title')
            topics = request.data.get('topics')

            if topics:
                if len(topics) > 10 or len(topics) < 1:
                    return JsonResponse({
                    'error': 'topics should be less than 10 and greater than 1',
                    'status': 'failed'
                }, status=400)
            else:
                return JsonResponse({
                    'error': 'topics is required',
                    'status': 'failed'
                }, status=400)

            if not title:
                return Response(
                    {'error': 'title is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )



            # k = int(request.data.get('top_k', 5))


            docs = DocumentContent.objects.filter(blog=blog, user=request.user)
            print(docs)
            if docs:
                print("docs are there")
                all_chunks = []
                all_embs = []
                chunk_dic = {}

                for doc in docs:
                    for chunk in doc.chunks_data:   # your JSON list of dicts
                        chunk_dic['text'] = chunk['text']
                        chunk_dic['doc_title'] = doc.title
                        all_chunks.append(chunk_dic)
                        all_embs.append(chunk['embedding'])
                
                top_chunks = get_top_k_chunks(
                query_text=title,
                all_chunks=all_chunks,  # from your JSONField
                all_embs = all_embs,
                embedding_model=embedding_model,
                k=5
            )
                print(top_chunks)
                print("--------------------------------")
            else:
                pass

            
            
            # content = generate_blog_by_topic(topic)
            content = [
                {"heading": "Intro", "body": "This is the intro."},
                {"heading": "Details", "body": "Some details here."}
            ]
            time.sleep(1)
            print(content)
            blog.title = title
            blog.slug = slugify(title)
            blog.content = content
            blog.save()
            
            return Response(BlogSerializer(blog).data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def generate_content_by_promt(self, request, slug=None):
        try:
            blog = self.get_object()
            prompt = request.data.get('prompt')
            title = request.data.get('title')
            topics = request.data.get('topics')

            if topics:
                if len(topics) > 10 or len(topics) < 1:
                    return JsonResponse({
                    'error': 'topics should be less than 10 and greater than 1',
                    'status': 'failed'
                }, status=400)
            else:
                return JsonResponse({
                    'error': 'topics is required',
                    'status': 'failed'
                }, status=400)
            if not prompt:
                return Response(
                    {'error': 'prompt is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            docs = DocumentContent.objects.filter(blog=blog, user=request.user)
            print(docs)
            if docs:
                
                all_chunks = []
                all_embs = []
                

                for doc in docs:
                    if doc.type == 'IMG':
                        pass
                    else:
                        if doc.summaries:
                            pass
                        else: 
                            pass
                
                blog_text = generate_blog(
                    prompt=prompt,
                    docs= joined,       # or pass doc excerpts
                    topics=topics,  # optional; works with or without
                    title=title,
                    language="Farsi",
                    image_count=2 ,
                    video_count=1
                )
                content = blog_text['sections']
            else:
                blog_text = generate_blog(
                    prompt=prompt,
                    docs= [],       # or pass doc excerpts
                    topics=topics,  # optional; works with or without
                    title=title,
                    language="Farsi",
                    image_count=2 ,
                    video_count=1
                )
                content = blog_text['sections']
       

            # content = generate_blog_by_promt(promt , topics ,title, top_chunks)
            content = [
                {"heading": "Intro", "body": "This is the intro."},
                {"heading": "Details", "body": "Some details here."}
            ]
            print(content)
            blog.content = content
            blog.title = title
            blog.slug = slugify(title)
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
            
            # content = regenerate_blog_by_feedback(blog.content , feedback)
            content = "this is a content test"
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

        # slug = request.data.get('slug')
        # blog = get_object_or_404(Blog, slug=slug, user=request.user)
        created_docs = []
        print(files)
        for file in files:
            extracted_text = ""

            # Check file type
            if file.content_type.startswith("image/"):
                # Image: OCR
                image = Image.open(file)
                # extracted_text = pytesseract.image_to_string(image, lang='fas+eng')
                image_url = image_generator.generate_image(image)
                extracted_text= ""
                doc_type = 'IMG'
            elif file.content_type == "application/pdf":
                text = ""
                with pdfplumber.open(file) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
                doc_type = 'PDF'
            elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                docx = DocxDocument(file)
                text = "\n".join([p.text for p in docx.paragraphs])
                doc_type = 'DOCX'
            # elif file.content_type in [
            #     "application/pdf",
            #     "application/msword",
            #     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            # ]:
            #     # PDF or Word: extract text via textract
            #     file_bytes = BytesIO(file.read())
            #     extracted_text = textract.process(file_bytes).decode('utf-8', errors='ignore')

            else:
                return Response({'error': 'Unsupported file type'}, status=status.HTTP_400_BAD_REQUEST)
                # continue  # skip unsupported files
            

            # chunks = splitter.split_text(extracted_text)

            # 2. Create the DocumentContent object with all required fields
            doc = DocumentContent.objects.create(
                user=request.user,          # <– required ForeignKey
                title=file.name,            # <– required CharField
                type=doc_type,              # <– required ChoiceField
                text_content=extracted_text,
                is_temporary=True
            )
             # 3. Add to return list
            created_docs.append({
                'document_id': str(doc.uuid),
                'title': doc.title,
                'text_preview': doc.text_content[:200]
            })

        if not created_docs:
            return Response({'error': 'No valid files uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'success',
            'created_documents': created_docs
        }, status=status.HTTP_201_CREATED)

