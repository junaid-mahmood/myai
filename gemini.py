import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure the library with your API key
api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)

async def sample_generate_text_image_content(prompt, image_bytes_list):
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

# You can keep the sample_generate_text_content function if needed for other purposes
async def sample_generate_text_content(prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

def list_available_models():
    for m in genai.list_models():
        print(f"name: {m.name}")
        print(f"description: {m.description}")
        print(f"supported generation methods:")
        print(f"  text: {m.supported_generation_methods.text}")
        print(f"  image: {m.supported_generation_methods.image}")
        print(f"  chat: {m.supported_generation_methods.chat}")
        print()

# Call this function to see available models
# list_available_models()
