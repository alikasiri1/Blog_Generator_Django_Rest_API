# Create your views here.
# from patchright.async_api import expect
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Blog, Comment,Admin, DocumentContent
from django.utils.text import slugify
import uuid
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
from services.embeddings import   count_tokens, truncate_by_tokens , split_text_into_chunks #splitter,
from services.generate import summarize_chunk,generate_blog, generate_card_topics, image_description, FourOImageAPI , RunwayAPI, generate_webpage
# from services.image_generator import Image_generator
import requests
import asyncio
from crawl4ai import AsyncWebCrawler
import subprocess
from urllib.parse import urlparse
from bidi.algorithm import get_display
from cloudinary.uploader import upload
from django.http import StreamingHttpResponse
import copy
from rest_framework.decorators import  renderer_classes
from rest_framework.renderers import BaseRenderer
from rest_framework.renderers import JSONRenderer
import markdown

class SSERenderer(BaseRenderer):
    media_type = 'text/event-stream'
    format = 'sse'
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data
        
MAX_FILE_SIZE_MB = 10  # example: 10MB max
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024


def is_safe_url(url: str) -> bool:
    """Ensure url is a clean, simple http/https URL without injection attempts."""
    
    if not url or not isinstance(url, str):
        return False

    # Absolute basic filtering
    forbidden_chars = [" ", ";", "|", "&", "$", "<", ">", "`"]
    if any(c in url for c in forbidden_chars):
        return False

    # Use urlparse for final verification
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        return False
    if not parsed.netloc:
        return False

    return True

async def crawl_url(url):

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return result.markdown

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
            language = request.data.get('language')
            temp_doc_ids = request.data.get('documents')  # list of UUIDs to attach
            num_cards = int(request.data.get('num_cards'))
            
            print(request.data)
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

            

            image_url = "https://res.cloudinary.com/dbezwpqgi/image/upload/v1/media/admin_images/pic_3_v0ij9t"
            documents = ""
            for doc_id in temp_doc_ids:
                try:
                    doc_text = ""
                    doc = DocumentContent.objects.get(uuid=doc_id , is_temporary=True)
                    print(doc.type)
                    if doc.type == 'IMG':
                        doc_text = doc.text_content
                        # doc.save()
                    else:
                        chunks = split_text_into_chunks(doc.text_content) #splitter.split_text(doc.text_content)
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
                    documents += f"Document `{doc.title}`:\n```\n{doc_text}\n```"
                    documents = truncate_by_tokens(documents ,100000 ,count_tokens(documents))
                except DocumentContent.DoesNotExist:
                    continue
            print(documents)
            # topics = generate_card_topics(prompt , documents, num_cards, language)

            # Simulate topic generation (replace with your actual logic)
            time.sleep(5)
            topics = [f"{prompt}","body",'conclusion']
            print(topics)
            content = []
            media =  {
                        "type":"",
                        "prompt":"",
                        "url":"",
                        "Position":"top",
                        "Width":"100%",
                        "Height":"100%",
                        'media_task_id':""
                    }
            for topic in topics:
                content.append({'heading': topic, 'body': "", 'media':media})
            print(content)
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
                blog.settings = {'containerWidth':'1000px', 'language':f"{'fa' if language == 'فارسی' else 'en'}",'theme':'purple-haze'}
                blog.blog_type = 'slide'
                blog.save()
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
            print("🔥 INTERNAL ERROR:", e)
            return JsonResponse({
                'error': str(e),
                'status': 'failed'
            }, status=500)

    
    @action(detail=True, methods=['get'])
    def publish(self, request, slug=None):
        blog = self.get_object()
        
        blog.status = 'published'
        blog.published_at = timezone.now()
        blog.save()
        return Response(BlogSerializer(blog).data)

    @action(detail=True, methods=['get'])
    def unpublish(self, request, slug=None):
        blog = self.get_object()
        
        blog.status = 'draft'
        blog.published_at = None
        blog.save()
        return Response(BlogSerializer(blog).data)
    
    @action(detail=True, methods=['post'])
    def generate_content_by_promt(self, request, slug=None):
        try:
            blog = self.get_object()
            prompt = request.data.get('prompt')
            title = request.data.get('title')
            topics = request.data.get('topics')
            language = request.data.get('language')
            temp_doc_ids = request.data.get('documents')  # list of UUIDs to attach
            print(request.data)
            # time.sleep(5)
            # return JsonResponse({
            #         'error': 'topics should be less than 10 and greater than 1',
            #         'status': 'failed'
            #     }, status=400)
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
            
            other_docs = DocumentContent.objects.filter(blog=blog,user=request.user).exclude(uuid__in=temp_doc_ids)
            deleted_count, _ = other_docs.delete()

            # docs = DocumentContent.objects.filter(blog=blog, user=request.user)
            # print(type(docs),docs)
            # if len(docs) > 0:
            #     documents = ""
            #     for doc in docs:
            #         try:
            #             doc_text = ""
            #             if doc.type == 'IMG':
            #                 doc_text = doc.text_content
            #             else:
            #                 if doc.summaries:
            #                     for summary in doc.summaries:
            #                         doc_text += summary['summarizes_text'] + "\n"
            #                 else: 
            #                     doc_text = doc.text_content
                            
            #             documents += f"{doc.title}:```\n{doc_text}\n```"
            #         except DocumentContent.DoesNotExist:
            #             continue
                
            #     documents = truncate_by_tokens(documents ,100000 ,count_tokens(documents))
            #     print(documents)
            #     generated_blog = generate_blog(prompt=prompt ,docs= documents,topics=topics ,title=title,language=language ,image_count=1, video_count=0)
                
            # else: 
                # pass
            generated_blog = generate_blog(prompt=prompt ,docs="" ,topics=topics ,title=title,language=language ,image_count=1, video_count=0)


            
            # content = [
            #     {
            #         "heading": "Intro",
            #         "body": "This is the intro.",
            #         "media": {
            #             "type":"image",
            #             "prompt":"A person reading a book under a tree",
            #             "url":"https://res.cloudinary.com/dbezwpqgi/image/upload/v1/media/admin_images/pic_3_v0ij9t",
            #             "Position":"top",
            #             "Width":"100%",
            #             "Height":"100%",
            #             'media_task_id':''
            #         }
            #     },
            #     {
            #         "heading": "Details",
            #         "body": "Some details here.",
            #         "media": {
            #             "type":"",
            #             "prompt":"",
            #             "url":"",
            #             "Position":"top",
            #             "Width":"100%",
            #             "Height":"100%",
            #             'media_task_id':'fadfadfadfaf'
            #         }
            #     }
            # ]
            content = []
            media =  {
                        "type":"",
                        "prompt":"",
                        "url":"",
                        "Position":"top",
                        "Width":"100%",
                        "Height":"100%",
                        'media_task_id':""
                    }
            for section in generated_blog['sections']:
                subsection = {}
                subsection['heading'] = section['heading']
                subsection['body'] = section['body']
                subsection['media'] = copy.deepcopy(media)

                content.append(subsection)
                
                
            try:
                content[0]['media']["type"] = "image"
                content[0]['media']["prompt"] = generated_blog['image_prompts'][0]
            except:
                pass
                
            # content[0]['media'] = media
            print(content)
            blog.content = content
            blog.title = title
            # slug = slugify(title)

            # if len(slug) > 1 :
            #     blog.slug = slug
            # else:
            #     blog.slug = f"{uuid.uuid4().hex[:8]}"
            blog.slug = f"{slugify(title)}-{uuid.uuid4().hex[:8]}"
            blog.save()
            
            return Response(BlogSerializer(blog).data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

    @action(detail=False, methods=['post'])
    def generate_webpage_content(self, request):
        try:
            # blog = self.get_object()
            prompt = request.data.get('prompt')
            language = request.data.get('language')
            temp_doc_ids = request.data.get('documents')  # list of UUIDs to attach
            print(request.data)
            # time.sleep(5)

            if not prompt:
                return Response(
                    {'error': 'prompt is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Delete all other temporary documents of this admin that were not selected
            other_docs = DocumentContent.objects.filter(
                is_temporary=True,
                blog__isnull=True,
                user=request.user
            ).exclude(uuid__in=temp_doc_ids)
            deleted_count, _ = other_docs.delete()
            
            # other_docs = DocumentContent.objects.filter(blog=blog,user=request.user).exclude(uuid__in=temp_doc_ids)
            # deleted_count, _ = other_docs.delete()

            # documents = ""
            # for doc_id in temp_doc_ids:
            #     try:
            #         doc_text = ""
            #         doc = DocumentContent.objects.get(uuid=doc_id , is_temporary=True)
            #         print(doc.type)
            #         if doc.type == 'IMG':
            #             doc_text = doc.text_content
            #             # doc.save()
            #         else:
            #             chunks = split_text_into_chunks(doc.text_content) #splitter.split_text(doc.text_content)
            #             if len(chunks) < 2:
            #                 doc_text = doc.text_content
            #             else:
            #                 if count_tokens(chunks[-1]) < 10000:
            #                     chunks[-2] += " " + chunks[-1]
            #                     chunks.pop(-1)
                            
            #                 summaries = []
            #                 for i, chunk in enumerate(chunks):
            #                     print(f"⏳ Summarizing chunk {i+1}/{len(chunks)} ...")
            #                     try:
            #                         summary = summarize_chunk(chunk)
            #                         summaries.append(summary)
            #                         doc_text += summary['summarizes_text'] + "\n"
            #                     except Exception as e:
            #                         print(f"❌ Error summarizing chunk {i+1}: {e}")

            #                 print("✅ All chunks summarized successfully")
            #                 doc.summaries = summaries
            #                 doc.save()
            #         documents += f"Document `{doc.title}`:\n```\n{doc_text}\n```"
            #         documents = truncate_by_tokens(documents ,100000 ,count_tokens(documents))
            #     except DocumentContent.DoesNotExist:
            #         continue
            # print(documents)

            # generated_blog = generate_webpage(prompt=prompt ,docs= documents,language=language)

            generated_blog = '## روندهای انرژی تجدیدپذیر در سال 2025\n\nانرژی\u200cهای تجدیدپذیر طی سال\u200cهای اخیر به یک محور اصلی در سیاست\u200cهای جهانی و توسعه پایدار تبدیل شده\u200cاند. با پیشرفت\u200cهای تکنولوژیکی، تغییرات جوی و فشارهای اقتصادی، جهان به سوی استفاده از منابع انرژی پاک\u200cتر و پایدارتر روی آورده است. در سال 2025، انتظار می\u200cرود که این روندها به شکل قابل توجهی تغییر کنند و نوآوری\u200cهایی در زمینه انرژی به وجود آید که نه تنها بر روی سیاست\u200cهای ملی تأثیر بگذارد بلکه بر روی سبک زندگی روزمره انسان\u200cها نیز تأثیرگذار باشد.\n\nتکنولوژی\u200cهای جدید بر پایه انرژی\u200cهای تجدیدپذیر به ما این امکان را می\u200cدهند که از منابعی چون خورشید، باد، آب و بیوماس استفاده بیشتری کنیم. در این راستا، پیشرفت\u200cها در زمینه ذخیره\u200cسازی انرژی و کارایی سیستم\u200cها به ما کمک خواهد کرد تا بتوانیم از این منابع به شکل مؤثرتری استفاده کنیم. با استفاده از انرژی تجدیدپذیر، جامعه\u200cای با انتشار کربن کمتر و محیط زیست پاک\u200cتر ساخته می\u200cشود.\n\nپیش\u200cبینی می\u200cشود که در سال 2025، انرژی خورشیدی و بادی به عنوان دو منبع اصلی انرژی تجدیدپذیر در بسیاری از کشورها شناخته شوند. این دو منبع قادر به تأمین بخش عمده\u200cای از نیازهای انرژی کشورهای پیشرفته و در حال توسعه خواهند بود و بدین ترتیب، همچنین موجب بهبود امنیت انرژی و کاهش وابستگی به سوخت\u200cهای فسیلی خواهند شد.\n\n![IMAGE_PROMPT: a futuristic solar panel farm with advanced technology, showcasing solar panels that track the sun and innovative wind turbines in the background](example.url)\n\n## پیشرفت\u200cهای فناوری و کاهش هزینه\u200cها\n\nیکی از عوامل کلیدی در رشد انرژی\u200cهای تجدیدپذیر در سال 2025، پیشرفت\u200cهای فناوری و کاهش هزینه\u200cها خواهد بود. با توسعه فناوری\u200cهای نوین مانند پنل\u200cهای خورشیدی با کارایی بالا و توربین\u200cهای بادی قوی\u200cتر، امکان تولید انرژی با هزینه\u200cهای کمتر فراهم خواهد شد. این پیشرفت\u200cها به ویژه در کشورهای در حال توسعه که به شدت به منابع انرژی جدید نیاز دارند، حائز اهمیت است.\n\nکاهش هزینه\u200cهای تولید و نصب پنل\u200cهای خورشیدی و تجهیزات بادی تنها یکی از جنبه\u200cهای این تحولات است. به عنوان مثال، بسیاری از شرکت\u200cها به بهینه\u200cسازی زنجیره تأمین خود پرداخته\u200cاند تا هزینه تمام\u200cشده تولید را به حداقل برسانند. در نتیجه، با کاهش هزینه، دسترسی به انرژی\u200cهای تجدیدپذیر برای عموم مردم آسان\u200cتر خواهد شد. این روند می\u200cتواند تأثیر زیادی بر پذیرش این نوع انرژی در سطح جامعه داشته باشد.\n\nدیگر جنبه مهم فناوری، بهبود روش\u200cهای ذخیره\u200cسازی انرژی است. با توسعه باتری\u200cهای کارآمدتر و سیستم\u200cهای ذخیره\u200cسازی بزرگ مقیاس، امکان استفاده از انرژی\u200cهای تجدیدپذیر به عنوان منبع اصلی تأمین انرژی فراهم می\u200cشود. به این ترتیب، نوسانات انرژی که به دلیل عدم ثبات در تولید منابع تجدیدپذیر به وجود می\u200cآید، به راحتی مدیریت خواهد شد و وابستگی به سوخت\u200cهای فسیلی به شدت کاهش می\u200cیابد.\n\n## پذیرش گسترده\u200cتر انرژی\u200cهای تجدیدپذیر\n\nیکی دیگر از روندهای قابل توجه در سال 2025، پذیرش گسترده\u200cتر انرژی\u200cهای تجدیدپذیر در صنایع و کسب\u200cوکارها خواهد بود. با توجه به فشارهای اجتماعی و اقتصادی برای کاهش انتشار کربن، شرکت\u200cها به سرعت به سمت استفاده از منابع انرژی پاک\u200cتر حرکت می\u200cکنند. این تغییرات نه تنها به آن\u200cها کمک می\u200cکند تا در راستای مسئولیت اجتماعی خود قدم بردارند بلکه همچنین می\u200cتواند هزینه\u200cها را کاهش دهد و مزیت\u200cهای رقابتی ایجاد کند.\n\nعلاوه بر این، بسیاری از صنایع به سمت عرضه انرژی\u200cهای تجدیدپذیر در محصولات و خدمات خود گام بر می\u200cدارند. به عنوان مثال، تولید خودروهای الکتریکی با استفاده از پنل\u200cهای خورشیدی برای شارژ و سیستم\u200cهای مدیریت هوشمند انرژی، روز به روز در حال گسترش است. این امر منجر به پیدایش نوآوری\u200cهای جدید و افزایش تقاضا برای انرژی\u200cهای پاک\u200cتر خواهد شد.\n\nسرمایه\u200cگذاری در زیرساخت\u200cهای انرژی تجدیدپذیر نیز در حال افزایش است. دولت\u200cها و نهادهای خصوصی به دنبال تأمین مالی پروژه\u200cهای انرژی پاک هستند تا به اهداف کاهش انتشار کربن و ایجاد محیط زیست سالم\u200cتر دست یابند. این روند به شکل\u200cگیری شبکه\u200cهای انرژی محلی و پایدار کمک می\u200cکند که می\u200cتواند به توسعه جوامع محلی و کاهش نابرابری\u200cهای اقتصادی منجر شود.\n\n![IMAGE_PROMPT: advanced renewable energy technology being adopted in an urban setting, showing electric vehicles charging at solar stations and buildings with green roofs](example.url)\n\n## چالش\u200cها و فرصت\u200cها\n\nاگرچه چشم\u200cانداز انرژی تجدیدپذیر در سال 2025 روشن به نظر می\u200cرسد، اما چالش\u200cهایی نیز وجود دارد که باید به آن\u200cها توجه شود. یکی از بزرگ\u200cترین چالش\u200cها، نیاز به اصلاحات قانونی و سیاست\u200cگذاری\u200cهای پایدار است. بسیاری از کشورها هنوز برای پذیرش انرژی\u200cهای تجدیدپذیر به اصلاحات اساسی نیاز دارند تا موانع موجود را برطرف کنند. همچنین، تغییر در رفتار مصرف\u200cکنندگان و عادت\u200cهای اجتماعی برای پذیرش این نوع انرژی لازم است.\n\nعلاوه بر این، تأمین مالی پروژه\u200cهای انرژی تجدیدپذیر در مناطق مختلف جهان یک چالش عمده به شمار می\u200cآید. کشورهای در حال توسعه به دلیل محدودیت\u200cهای مالی و دسترسی به منابع، ممکن است نتوانند به\u200cطور مؤثری از انرژی\u200cهای تجدیدپذیر بهره\u200cبرداری کنند. در این راستا، همکاری\u200cهای بین\u200cالمللی و ایجاد مدل\u200cهای مالی جدید می\u200cتواند به حل این مشکل کمک کند و به آنها ابتکار عمل در توسعه پایدار را بدهد.\n\nدر نهایت، چالش دیگری که باید به آن توجه شود، حفاظت از محیط زیست در هنگام استفاده از منابع تجدیدپذیر است. به عنوان مثال، پیاده\u200cسازی پروژه\u200cهای بزرگ بادی و خورشیدی ممکن است به اکوسیستم\u200cهای محلی آسیب برساند. بنابراین، در کنار خروج از سوخت\u200cهای فسیلی، ضروری است که رویکردی چندجانبه برای محافظت از منابع طبیعی و تنوع زیستی در پیش گرفته شود.\n\n## نتیجه\u200cگیری\n\nروندهای انرژی تجدیدپذیر در سال 2025 به شکل قابل توجهی منجر به تغییر شیوه تأمین انرژی در جهان خواهند شد. پیشرفت\u200cهای فناوری، پذیرش گسترده\u200cتر و سرمایه\u200cگذاری در زیرساخت\u200cها از جمله عواملی هستند که می\u200cتوانند نسل جدیدی از انرژی\u200cهای پاک و پایدار را به وجود آورند. در عین حال، اطمینان از توسعه پایدار و محافظت از محیط زیست از جمله چالش\u200cهایی است که باید بر آن فائق آمد.\n\nدر نهایت، انرژی\u200cهای تجدیدپذیر نه تنها به کاهش انتشار کربن و ایجاد جهانی پاک\u200cتر کمک می\u200cکنند بلکه می\u200cتوانند به ایجاد فرصت\u200cهای جدید شغلی و بهبود کیفیت زندگی در سراسر جهان بینجامند. با توجه به چالش\u200cها و فرصت\u200cها، آینده انرژی\u200cهای تجدیدپذیر بسیار امیدوارکننده به نظر می\u200cرسد و تمامی جوانب زندگی بشر را تحت تأثیر قرار خواهد داد.'
            content = []
            html = markdown.markdown(
                generated_blog,
                extensions=[
                    "extra",        # tables, fenced code blocks, etc.
                    "codehilite",   # syntax highlighting
                    "toc",          # table of contents (optional)
                ],
            )
            subsection = {}
            try:
                title = generated_blog.split('\n')[0].replace('#' , '').strip()
            except:
                title = generated_blog[:10]

            subsection['heading'] = title
            subsection['body'] = html.replace('\n' , '').replace('\u200c' , ' ')
            content.append(subsection)
            
            image_url = "https://res.cloudinary.com/dbezwpqgi/image/upload/v1/media/admin_images/pic_3_v0ij9t"
            print(content)
            
            
            blog_data = {
                'title': title,  # Using response as title
                'image_url': image_url,
                'content': content,
            }
            
            # Use your serializer to create the blog
            serializer = BlogSerializer(data=blog_data, context={'request': request})
            if serializer.is_valid():
                blog = serializer.save()
                blog.settings = {'containerWidth':'1000px', 'language':f"{'fa' if language == 'فارسی' else 'en'}",'theme':'purple-haze'}
                blog.blog_type = 'webpage'
                blog.save()
                # Attach documents specified in request
                attached_count = 0
                for doc_id in temp_doc_ids:
                    try:
                        doc = DocumentContent.objects.get(uuid=doc_id, is_temporary=True)
                        doc.mark_as_attached(blog)
                        attached_count += 1
                    except DocumentContent.DoesNotExist:
                        continue

                return Response(BlogSerializer(blog).data)
            else:
                return JsonResponse({
                    'error': 'Failed to create blog',
                    'details': serializer.errors,
                    'status': 'failed'
                }, status=400)

        except Exception as e:
            print(str(e))
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
        
        created_docs = []
        print(files)
        for file in files:
            extracted_text = ""

            # Check file type
            if file.content_type.startswith("image/"):
                # Image: OCR
                image = Image.open(file)
                try:
                    description = image_description(image) 
                    if description['status'] == True :
                        extracted_text = description['result']['caption'] + "Also document contains below text:\n"
                except Exception as e:
                    return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    # return Response({'error': 'We can work on image description write know'}, status=status.HTTP_404_NOT_FOUND)
                extracted_text += pytesseract.image_to_string(image, lang='fas+eng') 
                doc_type = 'IMG'
            elif file.content_type == "application/pdf":
                # text = ""
                with pdfplumber.open(file) as pdf:
                    # for page in pdf.pages:
                    #     extracted_text += page.extract_text() + "\n"
                    for page in pdf.pages:
                        raw = page.extract_text() or ""          # handle None
                        extracted_text += get_display(raw) + "\n"
                        
                doc_type = 'PDF'
            elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                docx = DocxDocument(file)
                extracted_text = "\n".join([p.text for p in docx.paragraphs])
                doc_type = 'DOCX'
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
                'title': doc.title
                # 'text_preview': doc.text_content[:200]
            })

        if not created_docs:
            return Response({'error': 'No valid files uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'success',
            'created_documents': created_docs
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def upload_temp_documents_url(self, request):
        url = request.data.get('url')
        print(url)
        if not url:
            return Response({'error': "URL is required"}, status=status.HTTP_400_BAD_REQUEST)
            # Safety check
        if not is_safe_url(url):
            return Response(
                {"error": "Invalid or unsafe URL"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_docs = []
        # Run the async crawler
        try:
            data = "test"#asyncio.run(crawl_url(url)) # run_crawl4ai(url)#
            print(data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        parsed = urlparse(url)
        doc = DocumentContent.objects.create(
                user=request.user,          # <– required ForeignKey
                title=f"{parsed.scheme}://{parsed.netloc}/",            # <– required CharField
                type='WEB',              # <– required ChoiceField
                text_content=data,
                url = url,
                is_temporary=True
            )
        
        created_docs.append({
                'document_id': str(doc.uuid),
                'title': doc.url,
            })
        return Response({'status': 'success','created_documents': created_docs})
        # return Response({'status': 'success','content': data})


    @action(detail=True, methods=['post'])
    def upload_media(self, request, slug=None):
        blog = self.get_object()
        print(request.data)
        prompt = request.data.get('prompt') 
        if not prompt:
            return Response(
                {'error': 'prompt is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate presence of file
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

            
        media_type = ''
        file = request.FILES['file']
        if file.content_type.startswith("image/"):
            media_type = 'image'
        elif file.content_type.startswith("video/"):
            media_type = 'video'
        else:
            return Response({'error': 'Unsupported file type'}, status=status.HTTP_400_BAD_REQUEST)


        # Validate file size
        if file.size > MAX_FILE_SIZE:
            return Response(
                {'error': f'File too large. Max size allowed is {MAX_FILE_SIZE_MB}MB.'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        # Validate presence of doc index
        doc_index = request.data.get('doc_index')
        if doc_index is None:
            return Response({'error': 'doc_index is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            doc_index = int(doc_index)
        except ValueError:
            return Response({'error': 'doc_index must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate content structure
        if not isinstance(blog.content, list):
            return Response({'error': 'Blog content must be a list.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # if not (0 <= doc_index < len(blog.content)):
        #     return Response({'error': 'doc_index out of range.'}, status=status.HTTP_400_BAD_REQUEST)
 

        try:
            result = upload(file)
            media_url = result["secure_url"] 
            # time.sleep(2)
            # media_url = 'https://res.cloudinary.com/dbezwpqgi/image/upload/v1764088928/uexjn0bgx8ohc73a7av2.png'
        except Exception as e:
            return Response({'error': str(e)}, status=500) 

        # Remove the temp file reference on the model
        # blog.temp_media_file.delete(save=False)
        media = {
            "type":media_type,
            "prompt":prompt,
            "url":media_url,
            "Position":"top",
            "Width":"100%",
            "Height":"100%",
            'media_task_id':''
        }
        print(media)
        # Update JSON content
        doc = blog.content[doc_index]
        doc['media']['type'] = media_type
        doc['media']['url'] = media_url
        doc['media']['media_task_id'] = ''
        blog.content[doc_index] = doc
        blog.save(update_fields=['content'])

        return Response({'url': media_url})

    @action(detail=True, methods=['post'])
    def generate_media(self, request, slug=None):
        blog = self.get_object()
        print(request.data)
        prompt = request.data.get('prompt') 
        media_type = request.data.get('media_type') 
        section_index = request.data.get('section_index') 
        print(section_index)
        if not prompt:
            return Response(
                {'error': 'prompt is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not media_type:
            return Response(
                {'error': 'media type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not section_index:
            return Response(
                {'error': 'section index is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        section_index = int(request.data.get('section_index'))
        if media_type not in ["video", "image"]:
            return Response(
                {'error': 'media_type should be image or video'}, 
                status=400
            )
        if media_type == 'image':
            # api = FourOImageAPI()
            # task_id = api.generate_image(
            # prompt=prompt,
            # size='1:1',
            # nVariants=1,
            # isEnhance=True,
            # enableFallback=True
            # )
            task_id = '3954ba0990424bb175ac01ae2ea3144e'
            blog_content = blog.content
            blog_content[section_index]['media']['media_task_id'] = task_id
            blog_content[section_index]['media']['type'] = media_type
            blog_content[section_index]['media']['prompt'] = prompt
            blog.content = blog_content

            blog.save()
            return Response({"task_id": task_id, "message": "started"})
        elif media_type == 'video':
            video_api = RunwayAPI()
            
            task_id = '3954ba0990424bb175ac01ae2ea3144e'
            blog_content = blog.content
            blog_content[section_index]['media']['media_task_id'] = task_id
            blog_content[section_index]['media']['type'] = media_type
            blog_content[section_index]['media']['prompt'] = prompt
            blog.content = blog_content

            blog.save()
            return Response({"task_id": task_id, "message": "started"})
    
    @action(detail=True, methods=['post'])
    def media_stream_2(self, request, slug=None):
        blog = self.get_object()
        print(request.data)
        task_id = request.data.get('task_id') 
        media_type = request.data.get("media_type") 
        if not task_id:
            return Response({"error": "task_id is required"}, status=400)

        if media_type not in ["image", "video"]:
            return Response({"error": "media_type must be 'image' or 'video'"}, status=400)
        if media_type == "image":
            try:
                # image_api = FourOImageAPI()
                # status = image_api.get_task_status(task_id)
                status = {
                                    "taskId": "task_4o_abc123",
                                    "paramJson": "{\"prompt\":\"A serene mountain landscape\",\"size\":\"1:1\"}",
                                    "completeTime": "2024-01-15 10:35:00",
                                    "response": {
                                        "resultUrls": [
                                            "https://res.cloudinary.com/dbezwpqgi/image/upload/v1/media/admin_images/pic_3_v0ij9t"
                                        ]
                                    },
                                    "successFlag": 1,
                                    "errorCode": None,
                                    "errorMessage": None,
                                    "createTime": "2024-01-15 10:30:00",
                                    "progress": "1.00"
                                }
                # status = {
                #                 "taskId": "task_4o_abc123",
                #                 "paramJson": "{\"prompt\":\"A serene mountain landscape\",\"size\":\"1:1\"}",
                #                 "completeTime": None,
                #                 "response": None,
                #                 "successFlag": 0,
                #                 "errorCode": None,
                #                 "errorMessage": None,
                #                 "createTime": "2024-01-15 10:30:00",
                #                 "progress": "0.90"
                #             }
                flag = status["successFlag"]
                if flag == 0:
                    progress = float(status.get("progress", 0)) * 100
                    return Response({'status': 'progress', 'progress': progress})

                # finished
                if flag == 1:
                    url = status["response"]["resultUrls"][0]
                    for card in blog.content:
                        if card['media']['media_task_id'] == task_id :
                            card['media']['media_task_id'] = ''
                            card['media']['url'] = url
                    blog.save()
                    return Response({'status': 'completed', 'url': url})

                # failed
                if flag == 2:
                    error = status.get("errorMessage", "generation failed")
                    return Response({'status': 'failed', 'error': error})

            except Exception as e:
                print(str(e))
                return Response({'status': 'error', 'error': str(e)}, status=400)
        elif media_type == "video":
            video_api = RunwayAPI()
            try:
                status = video_api.get_task_status(task_id)
                state = status["state"]
                # waiting states
                if state in ["wait", "queueing", "generating"]:
                    progress = status.get("progress", None)
                    payload = {
                        "status": state,
                    }
                    if progress is not None:
                        payload["progress"] = float(progress)

                    return Response(payload)

                # success
                if state == "success":
                    url = status["resultUrl"]
                    return Response({'status': 'completed', 'url': url})

                # fail
                if state == "fail":
                    error = status.get("failMsg", "video generation failed")
                    return Response({'status': 'failed', 'error': error})
                
            except Exception as e:
                return Response({'status': 'error', 'error': str(e)}, status=400)


    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    @renderer_classes([SSERenderer, JSONRenderer])
    def media_stream(self, request, slug=None):

        task_id = request.GET.get("task_id")
        media_type = request.GET.get("media_type")   # <-- fixed typo

        if not task_id:
            return Response({"error": "task_id is required"}, status=400)

        if media_type not in ["image", "video"]:
            return Response({"error": "media_type must be 'image' or 'video'"}, status=400)

        def event_stream():
            if media_type == "image":
                # image_api = FourOImageAPI()
                status = {
                                "taskId": "task_4o_abc123",
                                "paramJson": "{\"prompt\":\"A serene mountain landscape\",\"size\":\"1:1\"}",
                                "completeTime": None,
                                "response": None,
                                "successFlag": 0,
                                "errorCode": None,
                                "errorMessage": None,
                                "createTime": "2024-01-15 10:30:00",
                                "progress": "0.50"
                            }
                while True:
                    try:
                        # status = image_api.get_task_status(task_id)
                        
                        flag = status["successFlag"]

                        # still generating
                        if flag == 0:
                            progress = float(status.get("progress", 0)) * 100
                            yield f"data: {json.dumps({'status': 'progress', 'progress': progress})}\n\n"
                            time.sleep(3)
                            status= {
                                    "taskId": "task_4o_abc123",
                                    "paramJson": "{\"prompt\":\"A serene mountain landscape\",\"size\":\"1:1\"}",
                                    "completeTime": "2024-01-15 10:35:00",
                                    "response": {
                                        "resultUrls": [
                                            "https://example.com/generated-image.png"
                                        ]
                                    },
                                    "successFlag": 1,
                                    "errorCode": None,
                                    "errorMessage": None,
                                    "createTime": "2024-01-15 10:30:00",
                                    "progress": "1.00"
                                }
                            continue

                        # finished
                        if flag == 1:
                            url = status["response"]["resultUrls"][0]
                            yield f"data: {json.dumps({'status': 'completed', 'url': url})}\n\n"
                            return

                        # failed
                        if flag == 2:
                            error = status.get("errorMessage", "generation failed")
                            yield f"data: {json.dumps({'status': 'failed', 'error': error})}\n\n"
                            return
                    except Exception as e:
                            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
                            return

            elif media_type == "video":
                video_api = RunwayAPI()
                while True:
                    try:
                        status = video_api.get_task_status(task_id)
                        state = status["state"]

                        # waiting states
                        if state in ["wait", "queueing", "generating"]:
                            progress = status.get("progress", None)
                            payload = {
                                "status": state,
                            }
                            if progress is not None:
                                payload["progress"] = float(progress)

                            yield f"data: {json.dumps(payload)}\n\n"
                            time.sleep(4)
                            continue

                        # success
                        if state == "success":
                            url = status["resultUrl"]
                            yield f"data: {json.dumps({'status': 'completed', 'url': url})}\n\n"
                            return

                        # fail
                        if state == "fail":
                            error = status.get("failMsg", "video generation failed")
                            yield f"data: {json.dumps({'status': 'failed', 'error': error})}\n\n"
                            return
                    except Exception as e:
                        yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
                        return
        
        # Streaming response
        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"


        return response

    