import asyncio
import os
from PIL import ImageGrab
import cv2
import numpy as np
from gemini import sample_generate_text_image_content, sample_generate_text_content, list_available_models
from dotenv import load_dotenv
import speech_recognition as sr
import keyboard
import threading

load_dotenv()

async def capture_screenshot():
    screenshot = ImageGrab.grab()
    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    return cv2.imencode('.jpg', screenshot)[1].tobytes()

def needs_screenshot(query):
    visual_keywords = ['screen', 'desktop', 'display', 'see', 'show', 'look', 'visual', 'image', 'picture', 'icon', 'window']
    return any(keyword in query.lower() for keyword in visual_keywords)

async def process_query(query):
    if needs_screenshot(query):
        screenshot = await capture_screenshot()
        context = "You are an AI assistant analyzing a screenshot of a user's desktop. " \
                  "Focus only on the main visible window or application, ignoring any terminal " \
                  "or PowerShell windows. The user has asked the following about their screen: "
        prompt = f"{context}{query}\n\nAnalyze the screenshot and provide a concise, accurate answer " \
                 f"based solely on the content of the main visible window. Ignore any system tray, " \
                 f"desktop icons, or other background elements. If the main content is not visible " \
                 f"or relevant to the query, state that clearly. Provide only the answer, without any " \
                 f"additional explanations or qualifiers. After each sentence, start a new line."
        response = await sample_generate_text_image_content(prompt, [screenshot])
    else:
        context = "You are an AI assistant. Provide a concise and accurate answer to the following question. " \
                  "After each sentence, start a new line: "
        prompt = f"{context}{query}"
        response = await sample_generate_text_content(prompt)
    
    # Process the response to ensure new lines after periods
    processed_response = '. \n'.join(sentence.strip() for sentence in response.split('.') if sentence.strip())
    return processed_response

def listen_for_audio():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening... (Press Esc to stop)")
        print("Adjusting for ambient noise. Please wait...")
        r.adjust_for_ambient_noise(source, duration=1)
        print("Ready for input!")
        audio = r.listen(source, phrase_time_limit=None)
    try:
        print("Recognizing speech...")
        text = r.recognize_google(audio)
        print(f"Recognized: {text}")
        return text
    except sr.UnknownValueError:
        print("Speech was detected, but could not be recognized.")
        return "Sorry, I couldn't understand the audio."
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return "Sorry, there was an error processing the audio."

def test_microphone():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("Microphone test: Say something...")
            audio = r.listen(source, timeout=5)
            print("Audio captured. Attempting to recognize...")
            text = r.recognize_google(audio)
            print(f"You said: {text}")
            print("Microphone test successful!")
    except sr.WaitTimeoutError:
        print("No speech detected. Make sure your microphone is working.")
    except sr.RequestError:
        print("Could not request results; check your network connection")
    except sr.UnknownValueError:
        print("Speech was detected, but could not be recognized. Try speaking more clearly.")
    except Exception as e:
        print(f"An error occurred: {e}")

async def main():
    print("Welcome to the Gemini Desktop Assistant!")
    print("Type your question, or press Esc to use voice input.")
    print("Type 'quit' to exit.")
    print("Type 'cls' to clear the console.")

    audio_mode = False

    test_microphone()

    while True:
        if keyboard.is_pressed('esc'):
            audio_mode = not audio_mode
            if audio_mode:
                print("\nAudio input mode activated. Speak your question.")
                query = listen_for_audio()
                print(f"You said: {query}")
            else:
                print("\nAudio input mode deactivated. Type your question.")
                continue

        if not audio_mode:
            query = input("\nYour question: ")

        if query.lower() == 'quit':
            break
        elif query.lower() == 'list models':
            list_available_models()
            continue
        elif query.lower() == 'cls':
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Console cleared. Type your next question.")
            continue

        print("Processing...")
        try:
            response = await process_query(query)
            print(f"{response}")
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Please try again.")

if __name__ == "__main__":
    asyncio.run(main())
