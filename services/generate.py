import cohere
import json
from django.conf import settings
import os
import requests


def image_description(image):
    client_id = getattr(settings, 'CLIENT_ID', None) or os.getenv('COHERE_API_KEY')
    client_secret = getattr(settings, 'CLIENT_SECRET', None) or os.getenv('COHERE_API_KEY')
    data = {
        'data': image,
        "caption_len": "long"
        }
    
    description = requests.post('https://api.everypixel.com/v1/image_captioning', files=data, auth=(client_id, client_secret)).json()
    return description

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
    data = None
    try:
        content_obj = getattr(res, "message", None)
        if content_obj and getattr(content_obj, "content", None):
            blocks = content_obj.content
            if blocks and len(blocks) > 0 and hasattr(blocks[0], "text"):
                data = json.loads(blocks[0].text)
        if data is None:
            raw = getattr(res, "text", None) or getattr(res, "output_text", None) or str(res)
            data = json.loads(raw)
    except Exception:
        if isinstance(res, dict):
            data = res
        else:
            raise

    if not isinstance(data, dict):
        data = {"sections": [], "image_prompts": [], "video_prompts": []}

    # Normalize fields
    sections = data.get("sections", [])
    if not isinstance(sections, list):
        sections = []
    
    # Ensure each section has required fields
    normalized_sections = []
    for sec in sections:
        if isinstance(sec, dict):
            normalized_sections.append({
                "heading": sec.get("section", "") or "",
                "body": sec.get("content", "") or "",
                "media": {
                    "type":"",
                    "prompt":"",
                    "url":""
                }
            })
    
    image_prompts = data.get("image_prompts", [])
    if not isinstance(image_prompts, list):
        image_prompts = []
    image_prompts = [str(p) for p in image_prompts if p]
    
    video_prompts = data.get("video_prompts", [])
    if not isinstance(video_prompts, list):
        video_prompts = []
    video_prompts = [str(p) for p in video_prompts if p]
    
    # Enforce expected counts
    if image_count > 0:
        # Pad or truncate to match requested count
        if len(image_prompts) < image_count:
            image_prompts.extend([""] * (image_count - len(image_prompts)))
        elif len(image_prompts) > image_count:
            image_prompts = image_prompts[:image_count]
    else:
        image_prompts = []
    
    if video_count > 0:
        if len(video_prompts) < video_count:
            video_prompts.extend([""] * (video_count - len(video_prompts)))
        elif len(video_prompts) > video_count:
            video_prompts = video_prompts[:video_count]
    else:
        video_prompts = []

    return {
        "sections": normalized_sections,
        "image_prompts": image_prompts,
        "video_prompts": video_prompts,
    }