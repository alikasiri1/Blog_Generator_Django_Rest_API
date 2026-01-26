from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import uuid

webpage_prompt = {
    'system' : """You are a professional academic science communicator and research writer.
Your task is to transform multiple academic documents into ONE cohesive, unified narrative report.
The writing style should resemble a polished LinkedIn research post or public academic update.""",

    'DOCUMENT_INTERPRETATION': """- The provided documents represent one or more academic papers.
- Treat them as thematically related, even if they differ in scope or method.
- Do NOT summarize papers individually.
- Identify a SINGLE unifying research theme that connects all documents.
- Synthesize ideas, methods, and contributions into one integrated storyline.""",

##- Do NOT mention paper titles, publication venues, or years explicitly.
    'STRICT_OUTPUT_and_CONTENT_REQUIREMENTS' : """- Output must be valid Markdown only.
- Write ONE continuous, homogeneous report.
- Do NOT include citations, references, or external links.
- Do NOT mention that multiple documents were provided.
- Do NOT add explanations outside the report.
- Length: At least 1000 words.
- Tone: professional, reflective, confident, and accessible.
- Audience: researchers, industry professionals, graduate students, and policy-aware readers.
- Emphasize:
• the core research problem
• why it matters
• conceptual or methodological innovation
• broader implications and future direction""",

#     'CONTENT_REQUIREMENTS' : """- Length: At least 1000 words.
# - Tone: professional, reflective, confident, and accessible.
# - Audience: researchers, industry professionals, graduate students, and policy-aware readers.
# - Emphasize:
# • the core research problem
# • why it matters
# • conceptual or methodological innovation
# • broader implications and future direction""",

    'STRUCTURE_RULES_and_STYLE_CONSTRAINTS' : """- The first sentence should always be a well title related to the report. 
- Start with a strong opening paragraph that frames the research vision.
- Develop the narrative logically, with smooth transitions.
- End with a forward-looking or impact-focused conclusion.
- Do NOT use section headings unless they improve readability
- Avoid excessive technical detail.
- Avoid bullet points.
- Maintain a natural narrative flow.
- The text should read as if written by the researcher themselves.""",

#     'STYLE_CONSTRAINTS': """- Avoid excessive technical detail.
# - Avoid bullet points.
# - Maintain a natural narrative flow.
# - The text should read as if written by the researcher themselves.""",

    'IMAGE_PROMPT' : """- Images are OPTIONAL and should be used only when they improve clarity or engagement.
- Do NOT include real image URLs.
- When adding an image, use Markdown image syntax with the placeholder URL: example.url
- The image generation prompt MUST be placed inside the image alt text.
- The alt text must be a detailed, visual prompt suitable for an AI image generator.
- Format exactly like this:
![IMAGE_PROMPT: detailed image generation prompt](example.url)
- Include at most ONE image per main section.
- The blog must contain AT LEAST ONE images in total.
- The FIRST image must appear IMMEDIATELY after the blog title (on the next line after the title) before any text content."""
    
}

# webpage_prompt = """You are a professional academic science communicator and research writer.
# Your task is to transform multiple academic documents into ONE cohesive, unified narrative report.
# The writing style should resemble a polished LinkedIn research post or public academic update.      


# DOCUMENT INTERPRETATION RULES:
# - The provided documents represent one or more academic papers.
# - Treat them as thematically related, even if they differ in scope or method.
# - Do NOT summarize papers individually.
# - Identify a SINGLE unifying research theme that connects all documents.
# - Synthesize ideas, methods, and contributions into one integrated storyline.


# STRICT OUTPUT RULES:
# - Output must be valid Markdown only.
# - Write ONE continuous, homogeneous report.
# - Do NOT mention paper titles, publication venues, or years explicitly.
# - Do NOT include citations, references, or external links.
# - Do NOT mention that multiple documents were provided.
# - Do NOT add explanations outside the report.


# CONTENT REQUIREMENTS:
# - Length: At least 1000 words.
# - Tone: professional, reflective, confident, and accessible.
# - Audience: researchers, industry professionals, graduate students, and policy-aware readers.
# - Emphasize:
# • the core research problem
# • why it matters
# • conceptual or methodological innovation
# • broader implications and future direction

# STRUCTURE RULES:
# - The first sentence should always be a well subject related to the report. 
# - Start with a strong opening paragraph that frames the research vision.
# - Develop the narrative logically, with smooth transitions.
# - End with a forward-looking or impact-focused conclusion.
# - Do NOT use section headings unless they improve readability.


# STYLE CONSTRAINTS:
# - Avoid excessive technical detail.
# - Avoid bullet points.
# - Maintain a natural narrative flow.
# - The text should read as if written by the researcher themselves.

# IMAGE PROMPT RULES:
# - Images are OPTIONAL and should be used only when they improve clarity or engagement.
# - Do NOT include real image URLs.
# - When adding an image, use Markdown image syntax with the placeholder URL: example.url
# - The image generation prompt MUST be placed inside the image alt text.
# - The alt text must be a detailed, visual prompt suitable for an AI image generator.
# - Format exactly like this:
# ![IMAGE_PROMPT: detailed image generation prompt](example.url)
# - Include at most ONE image per main section.
# - The blog must contain AT LEAST TWO images in total.
# - The FIRST image must appear IMMEDIATELY after the blog title (on the next line after the title) before any text content.
# """
def default_webpage_prompt():
    return webpage_prompt
    
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    def __str__(self):
        return self.username

class Admin(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    work_domain = models.SlugField(max_length=50, unique=True, null = True , blank = True)
    # webpage_prompt = models.TextField(default = webpage_prompt)
    # webpage_prompt = models.JSONField(default = dict(webpage_prompt))
    webpage_prompt = models.JSONField(default=default_webpage_prompt)
    # image = models.ImageField(upload_to='admin_images/', null=True, blank=True) 
    image_url = models.URLField(max_length=500, null=True, blank=True) 
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.uuid})"

class Blog(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    BLOG_TYPE_CHOICES = [
        ('slide', 'Slide'),
        ('webpage', 'Webpage'),
    ]
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name='blogs', null = True , blank = True)
    title = models.CharField(max_length=200)
    content = models.JSONField(null=True, blank=True)  # ✅ JSON instead of plain text
    settings = models.JSONField(null=True, blank=True) 
    slug = models.SlugField(max_length=200, null = True , blank = True)
    image_url = models.URLField(max_length=500, null=True, blank=True) 
    # temp_media_file = models.FileField(upload_to="blog_media/",null=True,blank=True)
    # image = models.ImageField(upload_to='blog_images/', null=True, blank=True)  
    blog_type = models.CharField(max_length=10, choices=BLOG_TYPE_CHOICES, default='slide')  # ← added
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    readyblog = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug: #or Blog.objects.get(pk=self.pk).title != self.title:
            base_slug = f"{uuid.uuid4().hex[:8]}" #slugify(self.title) # f"{slugify(self.title)}-{uuid.uuid4().hex[:8]}"
            slug = base_slug
            counter = 1
            while Blog.objects.filter(slug=slug, admin=self.admin).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)




    class Meta:
        ordering = ['-created_at']
        unique_together = ('admin', 'slug')  # slug unique per admin

    def __str__(self):
        return self.title


class DocumentContent(models.Model):
    TYPE_CHOICES = [
        ('PDF', 'PDF'),
        ('DOCX', 'Word Document'),
        ('IMG', 'Image'),
        ('WEB', 'Webpage'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=4, choices=TYPE_CHOICES)
    text_content = models.TextField()
    is_temporary = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField(max_length=500, null=True, blank=True) # for image or webpage URL
    # summaries = models.JSONField(null=True, blank=True)  # ✅ JSON instead of plain text
    summarize_text = models.TextField(null=True, blank=True)

    def mark_as_attached(self, blog):
        """When a blog is created, this method is called."""
        self.blog = blog
        self.is_temporary = False
        self.save()

    def __str__(self):
        return f"{self.title}"

class Comment(models.Model):
    # section = models.ForeignKey(Section, related_name='comments', on_delete=models.CASCADE)
    blog = models.ForeignKey(Blog, related_name='sections', on_delete=models.CASCADE, null = True , blank = True)

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.section.blog.title}" 
