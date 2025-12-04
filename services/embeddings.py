# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from transformers import GPT2Tokenizer
# import numpy as np

# embedding_model = SentenceTransformer('bert-base-multilingual-cased')
# embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2') 
# splitter = RecursiveCharacterTextSplitter(chunk_size=20000, chunk_overlap=50)


# initialize tokenizer (you can change the model if needed)
# tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

# def count_tokens(text: str) -> int:
#     """Return the number of tokens in a given text."""
#     return len(tokenizer.encode(text, add_special_tokens=False))

def truncate_by_tokens(text: str, max_tokens: int, total_tokens):

    # Already within limit
    if total_tokens <= max_tokens:
        return text

    # How many tokens we must remove
    extra = total_tokens - max_tokens
    print(f'removing {extra} extra words at the end of docs')
    words = text.split()

    # Remove at least `extra` words from the end
    # (Not perfect but matches your requirement: no re-counting)
    truncated_words = words[:-extra] if extra < len(words) else []

    return " ".join(truncated_words)

# def get_top_k_chunks(query_text, all_chunks, all_embs, embedding_model, k=5):
    # """
    # Retrieve top-k most relevant chunks to the query.

    # Args:
    #     query_text (str): The user's query or prompt.
    #     chunks_data (list of dict): Each dict contains 'text' and 'embedding'.
    #     embedding_model: A sentence-transformer model to encode the query.
    #     k (int): Number of top chunks to return.

    # Returns:
    #     List of top-k chunk texts, ordered by relevance.
    # """
    # # Extract texts and embeddings
    # # all_chunks = [c['text'] for c in chunks_data]
    # # all_embs = [c['embedding'] for c in chunks_data]

    # # Embed the query
    # query_emb = embedding_model.encode(query_text).reshape(1, -1)
    # embs_array = np.array(all_embs)

    # # Compute cosine similarity
    # sims = cosine_similarity(query_emb, embs_array)[0]

    # # Get indices of top-k most similar chunks
    # top_idx = np.argsort(sims)[::-1][:k]

    # # Return the top-k chunk texts
    # top_chunks = [all_chunks[i] for i in top_idx]
    # return top_chunks


import re
from typing import List

# Configurable parameters (match your original settings)
CHUNK_SIZE = 20000
CHUNK_OVERLAP = 50

# Simple tokenizer using regex: splits on whitespace and punctuation.
# This is NOT GPT-2 BPE; it's an approximate token count.
token_pattern = re.compile(r"\w+|[^\w\s]", re.UNICODE)

def simple_tokenize(text: str) -> List[str]:
    """
    Return list of tokens using a regex-based tokenizer.
    Tokens are words (\w+) or any single non-whitespace non-word character.
    """
    return token_pattern.findall(text)

def count_tokens(text: str) -> int:
    """
    Count tokens in text using the simple regex tokenizer.
    """
    return len(simple_tokenize(text))

def split_text_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into chunks of at most chunk_size characters, with chunk_overlap characters overlap.
    The function attempts to split at sentence or whitespace boundaries when possible to avoid cutting words.
    """
    if chunk_size <= chunk_overlap:
        raise ValueError("chunk_size must be larger than chunk_overlap")

    chunks: List[str] = []
    text_length = len(text)
    start = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]

        # If we didn't reach the end and the next character is not whitespace, try to extend to the next whitespace
        # to avoid splitting in the middle of a word (but don't exceed chunk_size + 100 to avoid huge jumps).
        if end < text_length and not text[end].isspace():
            extra_end = end
            # Try to move forward up to 100 chars to next whitespace or punctuation boundary
            limit = min(text_length, end + 100)
            while extra_end < limit and not text[extra_end].isspace() and text[extra_end] not in ".!?;,":
                extra_end += 1
            # Use found boundary if it's within a reasonable limit
            if extra_end < limit and extra_end > end:
                chunk = text[start:extra_end]
                end = extra_end

        chunks.append(chunk)

        # advance start by chunk_size - chunk_overlap (but ensure progress)
        step = chunk_size - chunk_overlap
        if step <= 0:
            step = chunk_size  # fallback to prevent infinite loop
        start += step

    return chunks

    