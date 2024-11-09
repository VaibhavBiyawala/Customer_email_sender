import os
from dotenv import load_dotenv
from langchain_groq import chat_models

# Load environment variables from .env file
load_dotenv()

# Initialize the LLM
groq_api_key = os.getenv('GROQ_API_KEY')  # Ensure your API key is stored securely
llm = chat_models.ChatGroq(temperature=0, model_name="llava-v1.5-7b-4096-preview")

def generate_email_content(prompt_template, row_data):
    """Generates email content using a customizable prompt template and row data."""
    # Replace placeholders in the prompt template with actual data
    filled_prompt = prompt_template.format(**row_data)
    response = llm.invoke(filled_prompt)
    if hasattr(response, 'content'):
        return response.content
    else:
        raise ValueError("Invalid response from LLM")
