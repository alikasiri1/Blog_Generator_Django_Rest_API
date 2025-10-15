from transformers import pipeline
import cohere
import pypdf
import textwrap
import json

from django.conf import settings
import os


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


def _build_messages_for_topics(prompt: str, docs: str, num_cards: int):
    # Create a single user message combining prompt/docs with clear instructions
    base_instruction = (
        "You are an expert content strategist. Generate high-quality blog topic ideas."
        " Return a JSON object with a 'topics' array of strings with exactly the requested length."
        " Each topic should be concise (<=12 words), specific, and non-overlapping."
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


def generate_card_topics(prompt: str = "", docs: str = "", num_cards: int = 5):
    """
    Generate a list of topic strings of length num_cards using Cohere chat with JSON schema.
    - If docs are empty, rely on prompt.
    - If prompt is empty but docs are present, rely on docs.
    - If both are empty, raise ValueError.
    """
    if not prompt and not docs:
        raise ValueError("Either 'prompt' or 'docs' must be provided")

    client = _get_cohere_client_v2()
    messages = _build_messages_for_topics(prompt=prompt, docs=docs, num_cards=num_cards)

    schema = {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": max(1, int(num_cards)),
                "maxItems": max(1, int(num_cards)),
            }
        },
        "required": ["topics"],
        "additionalProperties": False,
    }

    res = client.chat(
        model="command-a-03-2025",
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
    return topics


def _build_messages_for_blog(prompt: str, docs: str, topics: list | None, title: str | None = None):
    instruction = (
        "You are a professional blog writer. Write a comprehensive, well-structured blog post."
        " Use informative headings, clear sections, and practical details."
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
        "Requirements: factual, structured, engaging, no placeholders, no hallucinations about citations."
    )
    content = "\n\n".join(user_parts)
    return [
        {
            "role": "user",
            "content": content,
        }
    ]


def generate_blog(prompt: str = "", docs: str = "", topics: list | None = None, title: str | None = None, max_tokens: int = 2000, temperature: float = 0.7):
    """
    Generate a blog post based on any combination of prompt/docs/topics.
    - topics are optional; if provided, they guide sectioning.
    - Works with prompt-only, docs-only, or both.
    """
    if not any([prompt, docs, topics]):
        raise ValueError("At least one of 'prompt', 'docs', or 'topics' must be provided")

    client = _get_cohere_client_v2()
    messages = _build_messages_for_blog(prompt=prompt, docs=docs, topics=topics, title=title)

    res = client.chat(
        model="command-a-03-2025",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Try to extract plain text content
    text = None
    message = getattr(res, "message", None)
    if message and getattr(message, "content", None):
        blocks = message.content
        parts = []
        for block in blocks:
            t = getattr(block, "text", None)
            if t:
                parts.append(t)
        if parts:
            text = "\n".join(parts)
    if not text:
        text = getattr(res, "text", None) or getattr(res, "output_text", None)
    if not text:
        text = str(res)
    return text

