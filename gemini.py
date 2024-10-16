import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure the library with your API key
api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API_KEY not found in environment variables")
genai.configure(api_key=api_key)

async def sample_generate_text_image_content(prompt, image_bytes_list):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        image_parts = [
            {
                "mime_type": "image/jpeg",
                "data": image_bytes
            }
            for image_bytes in image_bytes_list
        ]
        response = model.generate_content([prompt, *image_parts])
        return response.text
    except Exception as e:
        print(f"Error in sample_generate_text_image_content: {str(e)}")
        return "Sorry, I couldn't generate a response for the image."

# You can keep the sample_generate_text_content function if needed for other purposes
async def sample_generate_text_content(prompt):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error in sample_generate_text_content: {str(e)}")
        return "Sorry, I couldn't generate a response."

def list_available_models():
    try:
        for m in genai.list_models():
            print(f"name: {m.name}")
            print(f"description: {m.description}")
            print(f"supported generation methods:")
            print(f"  text: {m.supported_generation_methods.text}")
            print(f"  image: {m.supported_generation_methods.image}")
            print(f"  chat: {m.supported_generation_methods.chat}")
            print()
    except Exception as e:
        print(f"Error listing models: {str(e)}")

# Call this function to see available models
# list_available_models()
