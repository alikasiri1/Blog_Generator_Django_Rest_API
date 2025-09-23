import cohere
import openai
from django.conf import settings

def generate_blog_by_topic(topic: str , max_tokens=2000 , temperature=0.7):
    # Initialize Cohere client
    co = cohere.Client(settings.COHERE_API_KEY)
    
    # Generate blog content using Cohere
    response = co.generate(
        model='command',
        prompt=f"""You are a professional blog writer. Generate a well-structured blog post about {topic}.
        
        Include the following sections:
        1. Introduction
        2. Several main sections with detailed content
        3. Conclusion
        
        Make sure the blog post is comprehensive and well-formatted with clear section breaks.""",
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    content = response.generations[0].text

def generate_topic(prompt: str, temperature=0.7, max_tokens=300):
    """
    Generate a blog topic based on the given prompt using Cohere's API.
    
    Args:
        prompt (str): The input prompt to generate a topic from
        temperature (float): Controls randomness (0.0 to 1.0)
        max_tokens (int): Maximum length of the generated output
        
    Returns:
        str: Generated blog topic
    """
    # Initialize Cohere client
    co = cohere.Client(settings.COHERE_API_KEY)
    
    # Generate blog topic using Cohere
    response = co.generate(
        model='command',
        prompt=f"""You are a professional content creator. Generate an engaging and creative blog topic based on the following prompt:
        
        User Prompt: "{prompt}"
        
        Requirements:
        - The topic should be specific and interesting
        - It should appeal to a general audience
        - Keep it concise (under 10 words)
        - Make it attention-grabbing
        
        Return only the topic itself, no additional text.""",
        max_tokens=max_tokens,
        temperature=temperature,
        stop_sequences=["\n"]
    )
    
    # Extract and clean the generated topic
    topic = response.generations[0].text.strip()
    topic = topic.replace('"', '')  # Remove any quotation marks
    return topic

def generate_blog_by_promt(promt , max_tokens=2000 , temperature=0.7 , topic=None):
    # Initialize Cohere client
    co = cohere.Client(settings.COHERE_API_KEY)

    if topic:
        # Generate blog content using Cohere
        response = co.generate(
            model='command',
            prompt=f"""You are a professional blog writer. Generate a well-structured blog post about {topic} based on this promt {promt}.
            
            Include the following sections:
            1. Introduction
            2. Several main sections with detailed content
            3. Conclusion
            
            Make sure the blog post is comprehensive and well-formatted with clear section breaks.""",
            max_tokens=max_tokens,
            temperature=temperature
        )
        
    else :
        # Generate blog content using Cohere
        response = co.generate(
            model='command',
            prompt=f"""You are a professional blog writer. Generate a well-structured blog post about based on this promt{promt}.
            
            Include the following sections:
            1. topic
            2. Introduction
            3. Several main sections with detailed content
            4. Conclusion
            
            Make sure the blog post is comprehensive and well-formatted with clear section breaks.""",
            max_tokens=max_tokens,
            temperature=temperature
        )
    content = response.generations[0].text

def regenerate_blog_by_feedback(blog_content , feedback):
    # Initialize Cohere client
    co = cohere.Client(settings.COHERE_API_KEY)
    
    # Generate blog content using Cohere
    response = co.generate(
        model='command',
        prompt=f"""You are a professional blog writer. Revise the content based on the feedback.
        Original content: {blog_content}\nFeedback: {feedback}\nPlease revise the content accordingly.""",
        temperature=0.7
    )
    
    content = response.generations[0].text