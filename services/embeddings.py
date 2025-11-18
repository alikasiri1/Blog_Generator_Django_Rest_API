# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity
from langchain.text_splitter import RecursiveCharacterTextSplitter
from transformers import GPT2Tokenizer
# import numpy as np

# embedding_model = SentenceTransformer('bert-base-multilingual-cased')
# embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2') 
splitter = RecursiveCharacterTextSplitter(chunk_size=20000, chunk_overlap=50)


# initialize tokenizer (you can change the model if needed)
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

def count_tokens(text: str) -> int:
    """Return the number of tokens in a given text."""
    return len(tokenizer.encode(text, add_special_tokens=False))

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