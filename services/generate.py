from socket import timeout
import cohere
import json
from django.conf import settings
import os
import requests
import time
import io
from openai import OpenAI

class FourOImageAPI: 
    def __init__(self):
        self.api_key = getattr(settings, 'KIE_API_KEY', None) or os.getenv('KIE_API_KEY')
        self.base_url = 'https://api.kie.ai/api/v1/gpt4o-image'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def generate_image(self, **options):
        # response = requests.post(
        #     f'{self.base_url}/generate',
        #     headers=self.headers,
        #     json=options
        # )
        # result = response.json()

        # if not response.ok or result.get('code') != 200:
        #     raise Exception(f"Generation failed: {result.get('msg', 'Unknown error')}")

        # return result['data']['taskId']
        return "hfdahfhahfahfhahfahfah"

    def get_task_status(self, task_id):
        # response = requests.get(
        #     f'{self.base_url}/record-info?taskId={task_id}',
        #     headers={'Authorization': f'Bearer {self.api_key}'},
            
        # )
        # result = response.json()

        # if not response.ok or result.get('code') != 200:
        #     raise Exception(f"Status check failed: {result.get('msg', 'Unknown error')}")

        # return result['data']
        return {
                                    "taskId": "task_4o_abc123",
                                    "paramJson": "{\"prompt\":\"A serene mountain landscape\",\"size\":\"1:1\"}",
                                    "completeTime": "2024-01-15 10:35:00",
                                    "response": {
                                        "resultUrls": [
                                            # "https://res.cloudinary.com/dbezwpqgi/image/upload/v1/media/admin_images/pic_3_v0ij9t"
                                            "https://quera.org/media/CACHE/images/public/course/images/db6a1fea6c7540aeaa11c47eb18d2918/449eed3263985dbac10308ae824afa4b.jpg"
                                        ]
                                    },
                                    "successFlag": 1,
                                    "errorCode": None,
                                    "errorMessage": None,
                                    "createTime": "2024-01-15 10:30:00",
                                    "progress": "1.00"
                                }

    def get_download_url(self, image_url):
        response = requests.post(
            f'{self.base_url}/download-url',
            headers=self.headers,
            json={'imageUrl': image_url}
        )
        result = response.json()

        if not response.ok or result.get('code') != 200:
            raise Exception(f"Get download URL failed: {result.get('msg', 'Unknown error')}")

        return result['data']['downloadUrl']

    def poll_status(self, task_id):
        """
        Non-blocking status checker.
        Returns:
        {
            "status": "processing" | "completed" | "failed",
            "progress": float,
            "url": str or None,
            "error": str or None
        }
        """
        try:
            status = self.get_task_status(task_id)
            flag = status["successFlag"]

            # Processing
            if flag == 0:
                progress = float(status.get("progress", 0)) * 100
                return {
                    "status": "processing",
                    "progress": progress,
                    "url": None,
                    "error": None
                }

            # Completed
            if flag == 1:
                result = status["response"]["resultUrls"][0]
                return {
                    "status": "completed",
                    "progress": 100,
                    "url": result,
                    "error": None
                }

            # Failed
            if flag == 2:
                return {
                    "status": "failed",
                    "progress": None,
                    "url": None,
                    "error": status.get("errorMessage", "Unknown error")
                }

            # Unexpected
            return {
                "status": "unknown",
                "progress": None,
                "url": None,
                "error": "Unexpected API response"
            }

        except Exception as e:
            return {
                "status": "error",
                "progress": None,
                "url": None,
                "error": str(e)
            }



class RunwayAPI:
    def __init__(self):
        self.api_key = getattr(settings, 'KIE_API_KEY', None) or os.getenv('KIE_API_KEY')
        self.base_url = 'https://api.kie.ai/api/v1/runway'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def generate_video(self, **options):
        response = requests.post(
            f'{self.base_url}/generate',
            headers=self.headers,
            json=options
        )
        result = response.json()

        if not response.ok or result.get('code') != 200:
            raise Exception(f"Generation failed: {result.get('msg', 'Unknown error')}")

        return result['data']['taskId']

    def get_task_status(self, task_id):
        response = requests.get(
            f'{self.base_url}/record-detail?taskId={task_id}',
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
        result = response.json()

        if not response.ok or result.get('code') != 200:
            raise Exception(f"Status check failed: {result.get('msg', 'Unknown error')}")

        return result['data']

    def extend_video(self, task_id, prompt, quality='720p'):
        data = {
            'taskId': task_id,
            'prompt': prompt,
            'quality': quality
        }

        response = requests.post(
            f'{self.base_url}/extend',
            headers=self.headers,
            json=data
        )
        result = response.json()

        if not response.ok or result.get('code') != 200:
            raise Exception(f"Extension failed: {result.get('msg', 'Unknown error')}")

        return result['data']['taskId']

    def poll_status(self, task_id):
        """
        Non-blocking task polling.
        Returns (example):
        {
            'status': 'queueing' | 'generating' | 'success' | 'fail',
            'progress': None or float,
            'url': None or str,
            'error': None or str
        }
        """

        try:
            status = self.get_task_status(task_id)
            state = status["state"]

            # Convert API states into unified output

            # "wait" → Task received but not started
            if state == "wait":
                return {
                    "status": "waiting",
                    "progress": None,
                    "url": None,
                    "error": None
                }

            # "queueing" → In queue
            if state == "queueing":
                return {
                    "status": "queueing",
                    "progress": None,
                    "url": None,
                    "error": None
                }

            # "generating" → Rendering video
            if state == "generating":
                progress = status.get("progress")
                if progress is not None:
                    progress = float(progress) * 100
                return {
                    "status": "generating",
                    "progress": progress,
                    "url": None,
                    "error": None
                }

            # Success
            if state == "success":
                video_url = status.get("videoUrl") or status.get("outputUrl")
                return {
                    "status": "success",
                    "progress": 100,
                    "url": video_url,
                    "error": None
                }

            # Failed
            if state == "fail":
                return {
                    "status": "fail",
                    "progress": None,
                    "url": None,
                    "error": status.get("failMsg", "Video generation failed")
                }

            # Unknown
            return {
                "status": "unknown",
                "progress": None,
                "url": None,
                "error": f"Unhandled state: {state}"
            }

        except Exception as e:
            return {
                "status": "error",
                "progress": None,
                "url": None,
                "error": str(e)
            }

# def image_description(image):
#     client_id = getattr(settings, 'CLIENT_ID', None) #or os.getenv('COHERE_API_KEY')
#     client_secret = getattr(settings, 'CLIENT_SECRET', None) #or os.getenv('COHERE_API_KEY')
#     data = {
#         'data': image,
#         "caption_len": "long"
#         }
    
#     description = requests.post('https://api.everypixel.com/v1/image_captioning', files=data, auth=(client_id, client_secret)).json()
#     return description
def image_description(image_file):
    client_id = getattr(settings, 'CLIENT_ID', None)
    client_secret = getattr(settings, 'CLIENT_SECRET', None)

    # Convert PIL image to bytes
    img_bytes = io.BytesIO()
    image_file.save(img_bytes, format=image_file.format or "PNG")
    img_bytes.seek(0)

    files = {
        'data': ('image.png', img_bytes, 'image/png')
    }

    data = {
        "caption_len": "long"
    }

    response = requests.post(
        'https://api.everypixel.com/v1/image_captioning',
        files=files,
        data=data,
        auth=(client_id, client_secret)
    )

    return response.json()



def _get_cohere_client_v2():
    api_key = getattr(settings, 'COHERE_API_KEY', None) or os.getenv('COHERE_API_KEY')
    if not api_key:
        raise ValueError('COHERE_API_KEY is not configured in settings or environment')
    # Use ClientV2 per user sample
    try:
        client = cohere.ClientV2(api_key=api_key)
    except AttributeError:
        # Fallback for older SDKs – try standard Client
        client = cohere.Client(api_key)
    return client

def summarize_chunk(chunk):
    client = _get_cohere_client_v2()
    response = client.chat(
      model="command-r-08-2024",
      messages=[
          {"role": "system", "content": "You are a helpful assistant that summarizes text."},
          {
              "role": "user",
              "content": f"Generate a JSON summarizing this text in a concise way:\n\n{chunk}, \n\n with the fields 'title' and 'summarizes_text' \n -Keep the 'title' filed concise (under 12 words)",
          }
      ],
      response_format={
          "type": "json_object",
          "schema": {
              "type": "object",
              "properties": {
                  "title": {"type": "string"},
                  "summarizes_text": {"type": "string"}
              },
              "required": ["title", "summarizes_text"],
          },
     },
  )
    return json.loads(response.message.content[0].text)


def _build_messages_for_topics(prompt: str, docs: str, num_cards: int, language: str):
    # Create a single user message combining prompt/docs with clear instructions
    base_instruction = (
        "You are an expert content strategist. Generate a cohesive outline for a single blog."
        " Return a JSON object with a 'topics' array of strings of exactly the requested length."
        " The first item MUST be the Blog Title. The remaining items MUST be subsections"
        " that together cover the entire blog from beginning to end without overlap."
        " Each string should be concise (<=12 words), specific, and ordered logically."
        " Write ALL output in the following language: " + (language or "English") + "."
    )
    user_parts = []
    user_parts.append(base_instruction)
    if prompt:
        user_parts.append(f"User prompt: {prompt}")
    if docs:
        user_parts.append("Relevant docs:\n" + docs)
    user_parts.append(f"Number of topics to generate: {max(1, int(num_cards))}")
    content = "\n\n".join(user_parts)
    return [
        {
            "role": "user",
            "content": content,
        }
    ]


def generate_card_topics(prompt: str = "", docs: str = "", num_cards: int = 5, language: str = "English"):
    """
    Generate a list of topic strings of length num_cards using Cohere chat with JSON schema.
    - If docs are empty, rely on prompt.
    - If prompt is empty but docs are present, rely on docs.
    - If both are empty, raise ValueError.
    """
    if not prompt and not docs:
        raise ValueError("Either 'prompt' or 'docs' must be provided")

    client = _get_cohere_client_v2()
    messages = _build_messages_for_topics(prompt=prompt, docs=docs, num_cards=num_cards, language=language)
    print(messages)
    schema = {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
        "required": ["topics"],
    }

    res = client.chat(
        model="command-r-08-2024",
        messages=messages,
        response_format={
            "type": "json_object",
            "schema": schema,
        },
    )

    # The Cohere V2 SDK returns JSON content directly when using json_object; be defensive and parse
    data = None
    try:
        # Some SDKs return an object with .message.content[0].text, others already parsed
        content = getattr(res, "message", None)
        if content and getattr(content, "content", None):
            # try to grab the first text block
            blocks = content.content
            if blocks and len(blocks) > 0 and hasattr(blocks[0], "text"):
                data = json.loads(blocks[0].text)
        if data is None:
            # try res.text or res.output_text
            raw = getattr(res, "text", None) or getattr(res, "output_text", None) or str(res)
            data = json.loads(raw)
    except Exception:
        # Final fallback: if already a dict
        if isinstance(res, dict):
            data = res
        else:
            raise

    topics = data.get("topics", []) if isinstance(data, dict) else []
    # Coerce length to requested number
    topics = [t for t in topics if isinstance(t, str) and t.strip()][: max(1, int(num_cards))]
    # If model returned fewer, pad by splitting or cloning best-effort
    if len(topics) < max(1, int(num_cards)) and topics:
        while len(topics) < max(1, int(num_cards)):
            topics.append(topics[len(topics) % len(topics)])
    # Ensure first item is treated as title and others as subsections per contract
    # (The prompt already enforces this; we just ensure non-empty strings.)
    return topics


def _build_messages_for_blog(prompt: str, docs: str, topics: list | None, title: str | None = None, language: str = "English", image_count: int = 0, video_count: int = 0):
    instruction = (
        "You are a professional blog writer. Write a comprehensive, well-structured blog post."
        " Break the content into clear sections with headings."
        " Write ALL prose in the following language: " + (language or "English") + "."
    )
    user_parts = [instruction]
    if title:
        user_parts.append(f"Title: {title}")
    if prompt:
        user_parts.append(f"User prompt: {prompt}")
    if docs:
        user_parts.append("Reference docs (may contain excerpts):\n" + docs)
    if topics:
        # Format topics as ordered list for guidance
        formatted = "\n".join(f"- {t}" for t in topics if isinstance(t, str) and t.strip())
        user_parts.append("Requested sections/topics:\n" + formatted)
    
    user_parts.append(
        "Return a JSON object with fields: 'sections' (array), 'image_prompts' (array), 'video_prompts' (array)."
    )
    
    user_parts.append(
        "Structure requirements:"
        "\n- 'sections': Array of objects, each with 'section' (heading/topic name) and 'content' (text for that section)"
        "\n- Each section should be well-developed with practical details"
        "\n- Match sections to the requested topics when provided"
    )
    
    if image_count > 0:
        user_parts.append(
            f"Image prompt requirements: Generate exactly {image_count} evocative, safe, single-sentence image prompts"
            f" in the 'image_prompts' array. Each should represent different aspects of the blog content."
        )
    else:
        user_parts.append("Image prompt requirements: Set 'image_prompts' to an empty array.")
    
    if video_count > 0:
        user_parts.append(
            f"Video prompt requirements: Generate exactly {video_count} evocative, safe, single-sentence video prompts"
            f" in the 'video_prompts' array. Each should represent different aspects of the blog content."
        )
    else:
        user_parts.append("Video prompt requirements: Set 'video_prompts' to an empty array.")
    
    user_parts.append(
        "Content requirements: factual, structured, engaging, no placeholders, no fabricated citations."
    )
    content = "\n\n".join(user_parts)
    return [
        {
            "role": "user",
            "content": content,
        }
    ]



def generate_blog(prompt: str = "", docs: str = "", topics: list | None = None, title: str | None = None, max_tokens: int = 2000, temperature: float = 0.7, language: str = "English", image_count: int = 1, video_count: int = 0):
    """
    Generate a structured blog response with multiple sections and media prompts.
    
    Returns a dict: { 
        'sections': [{'section': str, 'content': str}, ...],
        'image_prompts': [str, str, ...],
        'video_prompts': [str, str, ...]
    }.
    
    Parameters:
    - prompt: User's blog request/prompt
    - docs: Reference documentation or content
    - topics: List of section topics/headings to cover
    - title: Optional blog title
    - max_tokens: Maximum tokens for generation
    - temperature: Generation temperature
    - language: Output language for content and prompts
    - image_count: Number of image prompts to generate (0 = none)
    - video_count: Number of video prompts to generate (0 = none)
    """
    if not any([prompt, docs, topics]):
        raise ValueError("At least one of 'prompt', 'docs', or 'topics' must be provided")
    
    if image_count < 0 or video_count < 0:
        raise ValueError("image_count and video_count must be non-negative integers")

    client = _get_cohere_client_v2()
    messages = _build_messages_for_blog(
        prompt=prompt,
        docs=docs,
        topics=topics,
        title=title,
        language=language,
        image_count=image_count,
        video_count=video_count,
    )
    print(messages,'\n')

    schema = {
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["section", "content"]
                }
            },
            "image_prompts": {
                "type": "array",
                "items": {"type": "string"}
            },
            "video_prompts": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["sections", "image_prompts", "video_prompts"],
    }

    res = client.chat(
        model="command-r-08-2024",
        messages=messages,
        response_format={
            "type": "json_object",
            "schema": schema,
        },
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Extract JSON content defensively
    # data = None
    # try:
    #     content_obj = getattr(res, "message", None)
    #     if content_obj and getattr(content_obj, "content", None):
    #         blocks = content_obj.content
    #         if blocks and len(blocks) > 0 and hasattr(blocks[0], "text"):
    #             data = json.loads(blocks[0].text)
    #     if data is None:
    #         raw = getattr(res, "text", None) or getattr(res, "output_text", None) or str(res)
    #         data = json.loads(raw)
    # except Exception:
    #     if isinstance(res, dict):
    #         data = res
    #     else:
    #         raise

    # if not isinstance(data, dict):
    #     data = {"sections": [], "image_prompts": [], "video_prompts": []}

    # ✅ OFFICIAL WAY (based on Cohere docs)
    content_blocks = res.message.content
    if not content_blocks:
        raise ValueError("Empty response from Cohere")

    raw = content_blocks[0].text

    if isinstance(raw, dict):
        data = raw
    elif isinstance(raw, str):
        data = json.loads(raw)
    else:
        raise ValueError("Unexpected Cohere response type")

    # ---------------- Normalize ----------------

    normalized_sections = []
    for sec in data.get("sections", []):
        if isinstance(sec, dict):
            normalized_sections.append({
                "heading": sec.get("section", ""),
                "body": sec.get("content", ""),
                "media": {
                    "type": "",
                    "prompt": "",
                    "url": "",
                },
            })

    image_prompts = data.get("image_prompts", [])
    if not isinstance(image_prompts, list):
        image_prompts = []

    video_prompts = data.get("video_prompts", [])
    if not isinstance(video_prompts, list):
        video_prompts = []

    # enforce counts
    image_prompts = image_prompts[:image_count] if image_count > 0 else []
    video_prompts = video_prompts[:video_count] if video_count > 0 else []

    return {
        "sections": normalized_sections,
        "image_prompts": image_prompts,
        "video_prompts": video_prompts,
    }
    # Normalize fields
    # sections = data.get("sections", [])
    # if not isinstance(sections, list):
    #     sections = []
    
    # # Ensure each section has required fields
    # normalized_sections = []
    # for sec in sections:
    #     if isinstance(sec, dict):
    #         normalized_sections.append({
    #             "heading": sec.get("section", "") or "",
    #             "body": sec.get("content", "") or "",
    #             "media": {
    #                 "type":"",
    #                 "prompt":"",
    #                 "url":""
    #             }
    #         })
    
    # image_prompts = data.get("image_prompts", [])
    # if not isinstance(image_prompts, list):
    #     image_prompts = []
    # image_prompts = [str(p) for p in image_prompts if p]
    
    # video_prompts = data.get("video_prompts", [])
    # if not isinstance(video_prompts, list):
    #     video_prompts = []
    # video_prompts = [str(p) for p in video_prompts if p]
    
    # # Enforce expected counts
    # if image_count > 0:
    #     # Pad or truncate to match requested count
    #     if len(image_prompts) < image_count:
    #         image_prompts.extend([""] * (image_count - len(image_prompts)))
    #     elif len(image_prompts) > image_count:
    #         image_prompts = image_prompts[:image_count]
    # else:
    #     image_prompts = []
    
    # if video_count > 0:
    #     if len(video_prompts) < video_count:
    #         video_prompts.extend([""] * (video_count - len(video_prompts)))
    #     elif len(video_prompts) > video_count:
    #         video_prompts = video_prompts[:video_count]
    # else:
    #     video_prompts = []

    # return {
    #     "sections": normalized_sections,
    #     "image_prompts": image_prompts,
    #     "video_prompts": video_prompts,
    # }



def _build_messages_for_webpageـblog(prompt: str,docs: str, setting_prompt , language: str = "English",):
    # system_message = (
    # "You are a professional long-form blog writer.\n"
    # "You write cohesive, narrative-driven articles with depth.\n"
    # f"All prose must be written in {language or 'English'}.\n\n"

    # "STRICT OUTPUT RULES:\n"
    # "- Output must be valid Markdown only.\n"
    # "- Write ONE fully integrated blog article.\n"
    # "- Do NOT include citations, references, or source links.\n"
    # "- Do NOT mention reports, studies, or external sources.\n"
    # "- Do NOT add explanations outside the blog.\n\n"

    # 'CONTENT DEPTH REQUIREMENTS:\n'
    # "- The article must be at least 1200 words.\n"
    # "- Each main section must contain AT LEAST 3 paragraphs.\n"
    # "- Each paragraph must contain 4–6 complete sentences.\n"
    # "- Each paragraph must introduce new information or analysis.\n"
    # "- Avoid repetition across paragraphs.\n\n"

    # "STRUCTURE RULES:\n"
    # "- Use a clear introduction and conclusion.\n"
    # "- Use Markdown headings (##) for main sections.\n"
    # "- Ensure smooth transitions between sections.\n\n"

    # "IMAGE PROMPT RULES:\n"
    # "- Images are OPTIONAL and should be used only when they improve clarity or engagement.\n"
    # "- Do NOT include real image URLs.\n"
    # "- When adding an image, use Markdown image syntax with the placeholder URL: example.url\n"
    # "- The image generation prompt MUST be placed inside the image alt text.\n"
    # "- The alt text must be a detailed, visual prompt suitable for an AI image generator.\n"
    # "- Format exactly like this:\n"
    # "  ![IMAGE_PROMPT: detailed image generation prompt](example.url)\n"
    # "- Include at most ONE image per main section.\n"
    # "- The blog must contain AT LEAST TWO images in total.\n"
    # "- The FIRST image must appear IMMEDIATELY after the blog title (on the next line after the title) before any text content.\n"
    # )
    system_message = f"""{setting_prompt['system']}\n
All prose must be written in {language or 'English'}\n
DOCUMENT INTERPRETATION RULES
{setting_prompt['DOCUMENT_INTERPRETATION']}\n
STRICT OUTPUT RULES and CONTENT REQUIREMENTS
{setting_prompt['STRICT_OUTPUT_and_CONTENT_REQUIREMENTS']}\n
STRUCTURE RULES and STYLE CONSTRAINTS
{setting_prompt['STRUCTURE_RULES_and_STYLE_CONSTRAINTS']}\n
IMAGE PROMPT RULES
{setting_prompt['IMAGE_PROMPT']}
"""
    # system_message = (
    #     "You are a professional academic science communicator and research writer.\n"
    #     "Your task is to transform multiple academic documents into ONE cohesive, unified narrative report.\n"
    #     "The writing style should resemble a polished LinkedIn research post or public academic update.\n\n"

    #     f"All prose must be written in {language or 'English'}.\n\n"

    #     "DOCUMENT INTERPRETATION RULES:\n"
    #     "- The provided documents represent one or more academic papers.\n"
    #     "- Treat them as thematically related, even if they differ in scope or method.\n"
    #     "- Do NOT summarize papers individually.\n"
    #     "- Identify a SINGLE unifying research theme that connects all documents.\n"
    #     "- Synthesize ideas, methods, and contributions into one integrated storyline.\n\n"

    #     "STRICT OUTPUT RULES:\n"
    #     "- Output must be valid Markdown only.\n"
    #     "- Write ONE continuous, homogeneous report.\n"
    #     "- Do NOT mention paper titles, publication venues, or years explicitly.\n"
    #     "- Do NOT include citations, references, or external links.\n"
    #     "- Do NOT mention that multiple documents were provided.\n"
    #     "- Do NOT add explanations outside the report.\n\n"

    #     "CONTENT REQUIREMENTS:\n"
    #     "- Length: At least 1000 words.\n"
    #     "- Tone: professional, reflective, confident, and accessible.\n"
    #     "- Audience: researchers, industry professionals, graduate students, and policy-aware readers.\n"
    #     "- Emphasize:\n"
    #     "  • the core research problem\n"
    #     "  • why it matters\n"
    #     "  • conceptual or methodological innovation\n"
    #     "  • broader implications and future direction\n\n"

    #     "STRUCTURE RULES:\n"
    #     "- Start with a strong opening paragraph that frames the research vision.\n"
    #     "- Develop the narrative logically, with smooth transitions.\n"
    #     "- End with a forward-looking or impact-focused conclusion.\n"
    #     "- Do NOT use section headings unless they improve readability.\n\n"

    #     "STYLE CONSTRAINTS:\n"
    #     "- Avoid excessive technical detail.\n"
    #     "- Avoid bullet points.\n"
    #     "- Maintain a natural narrative flow.\n"
    #     "- The text should read as if written by the researcher themselves.\n"

    #     "IMAGE PROMPT RULES:\n"
    #     "- Images are OPTIONAL and should be used only when they improve clarity or engagement.\n"
    #     "- Do NOT include real image URLs.\n"
    #     "- When adding an image, use Markdown image syntax with the placeholder URL: example.url\n"
    #     "- The image generation prompt MUST be placed inside the image alt text.\n"
    #     "- The alt text must be a detailed, visual prompt suitable for an AI image generator.\n"
    #     "- Format exactly like this:\n"
    #     "  ![IMAGE_PROMPT: detailed image generation prompt](example.url)\n"
    #     "- Include at most ONE image per main section.\n"
    #     "- The blog must contain AT LEAST TWO images in total.\n"
    #     "- The FIRST image must appear IMMEDIATELY after the blog title (on the next line after the title) before any text content.\n"
    # )

    # f"All prose must be written in {language or 'English'}."

    user_parts = []


    if prompt:
        user_parts.append(f"Overall blog prompt:\n{prompt}")

    if docs:
        user_parts.append(f"Reference material:\n{docs}")


    user_message = "\n\n".join(user_parts)

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]

# def generate_webpage( prompt: str, docs: str, language: str = "English", ):
#     messages = _build_messages_for_webpageـblog(prompt=prompt,docs=docs,language=language,)
#     co = _get_cohere_client_v2()
#     response = co.chat(
#     model="command-r-08-2024",
#     messages=messages,timeout=300
#     )

#     return response.message.content[0].text
 
def generate_webpage( prompt: str, docs: str,setting_prompt , language: str = "English", ):
    messages = _build_messages_for_webpageـblog(prompt=prompt,docs=docs,language=language, setting_prompt= setting_prompt)
    print(messages)
    metis_api_key = getattr(settings, 'METIS_API', None)
    client = OpenAI(api_key = metis_api_key, base_url="https://api.metisai.ir/openai/v1")
    response = client.responses.create(
        model= "gpt-4o-mini",#"metis-gpt",#
        # tools=[{"type": "web_search_preview"}],
        input=messages 
    )

    return response.output_text

    # return '## روندهای انرژی تجدیدپذیر در سال 2025\n\nانرژی\u200cهای تجدیدپذیر طی سال\u200cهای اخیر به یک محور اصلی در سیاست\u200cهای جهانی و توسعه پایدار تبدیل شده\u200cاند. با پیشرفت\u200cهای تکنولوژیکی، تغییرات جوی و فشارهای اقتصادی، جهان به سوی استفاده از منابع انرژی پاک\u200cتر و پایدارتر روی آورده است. در سال 2025، انتظار می\u200cرود که این روندها به شکل قابل توجهی تغییر کنند و نوآوری\u200cهایی در زمینه انرژی به وجود آید که نه تنها بر روی سیاست\u200cهای ملی تأثیر بگذارد بلکه بر روی سبک زندگی روزمره انسان\u200cها نیز تأثیرگذار باشد.\n\nتکنولوژی\u200cهای جدید بر پایه انرژی\u200cهای تجدیدپذیر به ما این امکان را می\u200cدهند که از منابعی چون خورشید، باد، آب و بیوماس استفاده بیشتری کنیم. در این راستا، پیشرفت\u200cها در زمینه ذخیره\u200cسازی انرژی و کارایی سیستم\u200cها به ما کمک خواهد کرد تا بتوانیم از این منابع به شکل مؤثرتری استفاده کنیم. با استفاده از انرژی تجدیدپذیر، جامعه\u200cای با انتشار کربن کمتر و محیط زیست پاک\u200cتر ساخته می\u200cشود.\n\nپیش\u200cبینی می\u200cشود که در سال 2025، انرژی خورشیدی و بادی به عنوان دو منبع اصلی انرژی تجدیدپذیر در بسیاری از کشورها شناخته شوند. این دو منبع قادر به تأمین بخش عمده\u200cای از نیازهای انرژی کشورهای پیشرفته و در حال توسعه خواهند بود و بدین ترتیب، همچنین موجب بهبود امنیت انرژی و کاهش وابستگی به سوخت\u200cهای فسیلی خواهند شد.\n\n![IMAGE_PROMPT: a futuristic solar panel farm with advanced technology, showcasing solar panels that track the sun and innovative wind turbines in the background](example.url)\n\n## پیشرفت\u200cهای فناوری و کاهش هزینه\u200cها\n\nیکی از عوامل کلیدی در رشد انرژی\u200cهای تجدیدپذیر در سال 2025، پیشرفت\u200cهای فناوری و کاهش هزینه\u200cها خواهد بود. با توسعه فناوری\u200cهای نوین مانند پنل\u200cهای خورشیدی با کارایی بالا و توربین\u200cهای بادی قوی\u200cتر، امکان تولید انرژی با هزینه\u200cهای کمتر فراهم خواهد شد. این پیشرفت\u200cها به ویژه در کشورهای در حال توسعه که به شدت به منابع انرژی جدید نیاز دارند، حائز اهمیت است.\n\nکاهش هزینه\u200cهای تولید و نصب پنل\u200cهای خورشیدی و تجهیزات بادی تنها یکی از جنبه\u200cهای این تحولات است. به عنوان مثال، بسیاری از شرکت\u200cها به بهینه\u200cسازی زنجیره تأمین خود پرداخته\u200cاند تا هزینه تمام\u200cشده تولید را به حداقل برسانند. در نتیجه، با کاهش هزینه، دسترسی به انرژی\u200cهای تجدیدپذیر برای عموم مردم آسان\u200cتر خواهد شد. این روند می\u200cتواند تأثیر زیادی بر پذیرش این نوع انرژی در سطح جامعه داشته باشد.\n\nدیگر جنبه مهم فناوری، بهبود روش\u200cهای ذخیره\u200cسازی انرژی است. با توسعه باتری\u200cهای کارآمدتر و سیستم\u200cهای ذخیره\u200cسازی بزرگ مقیاس، امکان استفاده از انرژی\u200cهای تجدیدپذیر به عنوان منبع اصلی تأمین انرژی فراهم می\u200cشود. به این ترتیب، نوسانات انرژی که به دلیل عدم ثبات در تولید منابع تجدیدپذیر به وجود می\u200cآید، به راحتی مدیریت خواهد شد و وابستگی به سوخت\u200cهای فسیلی به شدت کاهش می\u200cیابد.\n\n## پذیرش گسترده\u200cتر انرژی\u200cهای تجدیدپذیر\n\nیکی دیگر از روندهای قابل توجه در سال 2025، پذیرش گسترده\u200cتر انرژی\u200cهای تجدیدپذیر در صنایع و کسب\u200cوکارها خواهد بود. با توجه به فشارهای اجتماعی و اقتصادی برای کاهش انتشار کربن، شرکت\u200cها به سرعت به سمت استفاده از منابع انرژی پاک\u200cتر حرکت می\u200cکنند. این تغییرات نه تنها به آن\u200cها کمک می\u200cکند تا در راستای مسئولیت اجتماعی خود قدم بردارند بلکه همچنین می\u200cتواند هزینه\u200cها را کاهش دهد و مزیت\u200cهای رقابتی ایجاد کند.\n\nعلاوه بر این، بسیاری از صنایع به سمت عرضه انرژی\u200cهای تجدیدپذیر در محصولات و خدمات خود گام بر می\u200cدارند. به عنوان مثال، تولید خودروهای الکتریکی با استفاده از پنل\u200cهای خورشیدی برای شارژ و سیستم\u200cهای مدیریت هوشمند انرژی، روز به روز در حال گسترش است. این امر منجر به پیدایش نوآوری\u200cهای جدید و افزایش تقاضا برای انرژی\u200cهای پاک\u200cتر خواهد شد.\n\nسرمایه\u200cگذاری در زیرساخت\u200cهای انرژی تجدیدپذیر نیز در حال افزایش است. دولت\u200cها و نهادهای خصوصی به دنبال تأمین مالی پروژه\u200cهای انرژی پاک هستند تا به اهداف کاهش انتشار کربن و ایجاد محیط زیست سالم\u200cتر دست یابند. این روند به شکل\u200cگیری شبکه\u200cهای انرژی محلی و پایدار کمک می\u200cکند که می\u200cتواند به توسعه جوامع محلی و کاهش نابرابری\u200cهای اقتصادی منجر شود.\n\n![IMAGE_PROMPT: advanced renewable energy technology being adopted in an urban setting, showing electric vehicles charging at solar stations and buildings with green roofs](example.url)\n\n## چالش\u200cها و فرصت\u200cها\n\nاگرچه چشم\u200cانداز انرژی تجدیدپذیر در سال 2025 روشن به نظر می\u200cرسد، اما چالش\u200cهایی نیز وجود دارد که باید به آن\u200cها توجه شود. یکی از بزرگ\u200cترین چالش\u200cها، نیاز به اصلاحات قانونی و سیاست\u200cگذاری\u200cهای پایدار است. بسیاری از کشورها هنوز برای پذیرش انرژی\u200cهای تجدیدپذیر به اصلاحات اساسی نیاز دارند تا موانع موجود را برطرف کنند. همچنین، تغییر در رفتار مصرف\u200cکنندگان و عادت\u200cهای اجتماعی برای پذیرش این نوع انرژی لازم است.\n\nعلاوه بر این، تأمین مالی پروژه\u200cهای انرژی تجدیدپذیر در مناطق مختلف جهان یک چالش عمده به شمار می\u200cآید. کشورهای در حال توسعه به دلیل محدودیت\u200cهای مالی و دسترسی به منابع، ممکن است نتوانند به\u200cطور مؤثری از انرژی\u200cهای تجدیدپذیر بهره\u200cبرداری کنند. در این راستا، همکاری\u200cهای بین\u200cالمللی و ایجاد مدل\u200cهای مالی جدید می\u200cتواند به حل این مشکل کمک کند و به آنها ابتکار عمل در توسعه پایدار را بدهد.\n\nدر نهایت، چالش دیگری که باید به آن توجه شود، حفاظت از محیط زیست در هنگام استفاده از منابع تجدیدپذیر است. به عنوان مثال، پیاده\u200cسازی پروژه\u200cهای بزرگ بادی و خورشیدی ممکن است به اکوسیستم\u200cهای محلی آسیب برساند. بنابراین، در کنار خروج از سوخت\u200cهای فسیلی، ضروری است که رویکردی چندجانبه برای محافظت از منابع طبیعی و تنوع زیستی در پیش گرفته شود.\n\n## نتیجه\u200cگیری\n\nروندهای انرژی تجدیدپذیر در سال 2025 به شکل قابل توجهی منجر به تغییر شیوه تأمین انرژی در جهان خواهند شد. پیشرفت\u200cهای فناوری، پذیرش گسترده\u200cتر و سرمایه\u200cگذاری در زیرساخت\u200cها از جمله عواملی هستند که می\u200cتوانند نسل جدیدی از انرژی\u200cهای پاک و پایدار را به وجود آورند. در عین حال، اطمینان از توسعه پایدار و محافظت از محیط زیست از جمله چالش\u200cهایی است که باید بر آن فائق آمد.\n\nدر نهایت، انرژی\u200cهای تجدیدپذیر نه تنها به کاهش انتشار کربن و ایجاد جهانی پاک\u200cتر کمک می\u200cکنند بلکه می\u200cتوانند به ایجاد فرصت\u200cهای جدید شغلی و بهبود کیفیت زندگی در سراسر جهان بینجامند. با توجه به چالش\u200cها و فرصت\u200cها، آینده انرژی\u200cهای تجدیدپذیر بسیار امیدوارکننده به نظر می\u200cرسد و تمامی جوانب زندگی بشر را تحت تأثیر قرار خواهد داد.'

def summarize_document(document):
    message = f"""You are an expert academic editor and science communicator.
Your task is to summarize the following document in a clear, accurate, and structured way.

GOALS:
- Preserve the core scientific contribution of the document
- Focus on the main problem, methodology, key findings, and conclusions
- Remove unnecessary details, repetitions, references, and formatting artifacts
- Write in a neutral, informative, and professional tone
- The summary will later be used to generate a public-facing scientific blog post

INSTRUCTIONS:
- Do NOT invent information
- Do NOT add opinions or interpretations beyond the document
- Do NOT mention figures, tables, or section numbers explicitly
- If the document is incomplete, summarize only what is available

OUTPUT FORMAT:
- Write a coherent paragraph-based summary
- Length: concise but informative (approximately 20–30% of the original text)
- Use clear academic language
- Avoid bullet points; write in continuous prose
"""
    metis_api_key = getattr(settings, 'METIS_API', None)
    client = OpenAI(api_key = metis_api_key, base_url="https://api.metisai.ir/openai/v1")
    response = client.responses.create(
        model= "gpt-4o-mini",
        input=[
          {"role": "system", "content": message},
          {
              "role": "user",
              "content": f"DOCUMENT:\n\n```{document}``` \n",
          }
      ],
    )

    return response.output_text 