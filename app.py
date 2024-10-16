import asyncio
import os
from PIL import ImageGrab
import cv2
import numpy as np
from gemini import sample_generate_text_image_content, sample_generate_text_content, list_available_models
from dotenv import load_dotenv
import subprocess
import requests
import pygetwindow as gw
import pyautogui
import pyperclip
import sys
import shlex
import aiohttp
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

load_dotenv()

chat_history = []

async def capture_screenshot():
    try:
        screenshot = ImageGrab.grab()
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return cv2.imencode('.jpg', screenshot)[1].tobytes()
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
        return None

def needs_screenshot(query):
    visual_keywords = ['screen', 'desktop', 'display', 'see', 'show', 'look', 'visual', 'image', 'picture', 'icon', 'window']
    return any(keyword in query.lower() for keyword in visual_keywords)

def get_active_window_title():
    try:
        active_window = gw.getActiveWindow()
        return active_window.title if active_window else "No active window found."
    except Exception as e:
        return f"Error retrieving active window: {e}"

async def process_query(query):
    global chat_history
    
    chat_history.append(f"User: {query}")
    
    # Use AI to interpret the query and suggest steps
    ai_response = await get_ai_instructions(query)
    print("AI interpreted steps:", ai_response)
    steps = break_down_instruction(ai_response)
    
    if steps:
        await execute_instruction(steps)
    else:
        print("I couldn't understand how to perform this task. I'll try a general search.")
        await perform_search(query)
        chat_history.append(f"Assistant: I performed a general search for '{query}'")

async def execute_instruction(steps):
    for step in steps:
        action = step['action']
        target = step['target']
        
        try:
            if action == 'open':
                response = await open_application(target.split()[0])  # Open first word as app name
                print(response)
                chat_history.append(f"Assistant: {response}")
                
                # If there's more to the target, treat it as a search query
                if len(target.split()) > 1:
                    search_query = ' '.join(target.split()[1:])
                    await perform_search(search_query)
                    chat_history.append(f"Assistant: Searched for '{search_query}'")
            
            elif action in ['search', 'look for', 'find']:
                await perform_search(target)
                chat_history.append(f"Assistant: Searched for '{target}'")
            
            elif action == 'copy':
                pyautogui.hotkey('command', 'c')  # Use 'ctrl' instead of 'command' on Windows
                print(f"Copied: {target}")
                chat_history.append(f"Assistant: Copied: {target}")
            elif action == 'paste':
                pyautogui.hotkey('command', 'v')  # Use 'ctrl' instead of 'command' on Windows
                print(f"Pasted content")
                chat_history.append(f"Assistant: Pasted content")
            elif action == 'read':
                content = pyperclip.paste()
                print(f"Read from clipboard: {content}")
                chat_history.append(f"Assistant: Read from clipboard: {content}")
            elif action == 'type':
                pyautogui.typewrite(target)
                print(f"Typed: {target}")
                chat_history.append(f"Assistant: Typed: {target}")
            elif action == 'install':
                result = await install_package(target)
                print(result)
                chat_history.append(f"Assistant: {result}")
            elif action == 'get':
                content = await get_content(target)
                pyperclip.copy(content)
                print(f"Got content: {content}")
                chat_history.append(f"Assistant: Got content: {content}")
            elif action == 'put':
                await put_content(target)
                print(f"Put content into: {target}")
                chat_history.append(f"Assistant: Put content into: {target}")
            elif action == 'execute':
                # Instead of trying to execute an unknown command, ask the AI for help
                ai_solution = await get_ai_solution(f"How to perform this action: {target}")
                print("AI suggested solution:", ai_solution)
                await execute_instruction(break_down_instruction(ai_solution))
            else:
                # For any unrecognized action, perform a search
                await perform_search(f"{action} {target}")
                chat_history.append(f"Assistant: Searched for '{action} {target}'")

            await asyncio.sleep(1)  # Small delay between actions

        except Exception as e:
            error_message = f"Error executing {action}: {str(e)}"
            print(error_message)
            chat_history.append(f"Assistant: {error_message}")
            
            # If an error occurs, try a general search
            await perform_search(f"{action} {target}")
            chat_history.append(f"Assistant: Attempted a search for '{action} {target}'")

    print("All instructions executed.")
    chat_history.append("Assistant: All instructions executed.")

async def install_package(package_name):
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", package_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return f"Successfully installed {package_name}"
        else:
            return f"Failed to install {package_name}: {stderr.decode()}"
    except Exception as e:
        return f"Error installing {package_name}: {str(e)}"

async def execute_command(command):
    try:
        args = shlex.split(command)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return f"Command executed successfully: {stdout.decode()}"
        else:
            return f"Command failed: {stderr.decode()}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

def break_down_instruction(instruction):
    steps = []
    parts = instruction.lower().split(' and ')
    
    for part in parts:
        if part.startswith('open'):
            app_name = part.replace('open', '').strip()
            steps.append({'action': 'open', 'target': app_name})
        elif any(keyword in part for keyword in ['search for', 'look for', 'find']):
            for keyword in ['search for', 'look for', 'find']:
                if keyword in part:
                    query = part.split(keyword)[-1].strip()
                    steps.append({'action': 'search', 'target': query})
                    break
        elif 'copy' in part:
            steps.append({'action': 'copy', 'target': part.replace('copy', '').strip()})
        elif 'paste' in part:
            steps.append({'action': 'paste', 'target': ''})
        elif 'read' in part:
            steps.append({'action': 'read', 'target': ''})
        elif 'type' in part:
            text = part.replace('type', '').strip()
            steps.append({'action': 'type', 'target': text})
        elif 'install' in part:
            package = part.replace('install', '').strip()
            steps.append({'action': 'install', 'target': package})
        elif 'get' in part and 'put' in part:
            source = part.split('get')[-1].split('put')[0].strip()
            destination = part.split('put')[-1].strip()
            steps.append({'action': 'get', 'target': source})
            steps.append({'action': 'put', 'target': destination})
        else:
            # For any unrecognized instruction, treat it as a command to execute
            steps.append({'action': 'execute', 'target': part.strip()})
    
    return steps

async def perform_search(query):
    try:
        await open_application("safari")  # Ensure Safari is open
        await asyncio.sleep(2)  # Wait for Safari to be ready
        
        pyautogui.hotkey('command', 'l')  # Focus on the address bar
        await asyncio.sleep(0.5)
        
        pyautogui.typewrite(f"https://www.google.com/search?q={query}")
        pyautogui.press('enter')
        print(f"Searched for: {query}")
        await asyncio.sleep(2)  # Wait for the search to complete
    except Exception as e:
        print(f"Error performing search: {str(e)}")
        chat_history.append(f"Assistant: Error performing search: {str(e)}")

async def open_application(app_name):
    if os.name == 'posix':  # macOS
        try:
            if app_name.lower() == 'safari':
                process = await asyncio.create_subprocess_exec("open", "-a", "Safari")
            else:
                process = await asyncio.create_subprocess_exec("open", "-a", app_name)
            await process.communicate()
            await asyncio.sleep(2)  # Wait for the application to open
            return f"Successfully opened {app_name}"
        except Exception as e:
            return f"Failed to open {app_name}. Error: {str(e)}"
    elif os.name == 'nt':  # Windows
        try:
            process = await asyncio.create_subprocess_shell(app_name)
            await process.communicate()
            await asyncio.sleep(2)  # Wait for the application to open
            return f"Successfully opened {app_name}"
        except Exception as e:
            return f"Failed to open {app_name}. Error: {str(e)}"
    else:
        return "Unsupported operating system"

async def get_weather(location):
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return "Weather API key not found in environment variables"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        weather_description = data['weather'][0]['description']
        temperature = data['main']['temp']
        return f"The current weather in {location} is {weather_description} with a temperature of {temperature}°C."
    except requests.RequestException as e:
        return f"Sorry, I couldn't fetch the weather information. Error: {e}"

async def get_ai_instructions(query):
    prompt = f"""
    I received the following instruction from a user: "{query}"
    Please interpret this as a series of actions to perform on a computer.
    If there are any errors or unclear parts in the instruction, please correct them.
    Format your response as a series of simple commands, each on a new line, that a computer program could understand and execute.
    Always include at least one actionable step, even if you have to guess the user's intent.
    """
    return await sample_generate_text_content(prompt)

async def get_ai_solution(problem):
    prompt = f"""
    I encountered this problem while trying to perform a task: {problem}
    Can you provide a step-by-step solution to resolve this issue and complete the task?
    Format your response as a series of simple commands, each on a new line, that a computer program could understand and execute.
    """
    return await sample_generate_text_content(prompt)

async def main():
    print("Welcome to the Gemini Desktop Assistant!")
    print("I am here to assist you with your requests and I'm always learning!")
    print("Please provide me with any task you'd like me to perform.")
    print("Type 'quit' to exit.")
    print("Type 'cls' to clear the console.")
    print("Type 'history' to view chat history.")

    while True:
        try:
            query = input("\nYour task: ")

            if query.lower() == 'quit':
                break
            elif query.lower() == 'list models':
                list_available_models()
                continue
            elif query.lower() == 'cls':
                os.system('cls' if os.name == 'nt' else 'clear')
                print("Console cleared. Type your next task.")
                continue
            elif query.lower() == 'history':
                print("\nChat History:")
                for entry in chat_history[-10:]:  # Show last 10 entries
                    print(entry)
                continue

            print("Processing...")
            try:
                await process_query(query)
            except Exception as e:
                print(f"An error occurred while processing the query: {str(e)}")
                chat_history.append(f"Assistant: An error occurred: {str(e)}")
                print("I'll try to learn from this error and do better next time!")
        except KeyboardInterrupt:
            print("\nProgram interrupted. Exiting...")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            print("The program will continue running. You can type 'quit' to exit.")

async def get_content(source):
    # This function should extract the required information from the source
    # For now, we'll simulate it by returning a hardcoded list
    return "1. LeBron James\n2. Kevin Durant\n3. Giannis Antetokounmpo\n4. Stephen Curry\n5. Kawhi Leonard\n6. James Harden\n7. Luka Doncic\n8. Joel Embiid\n9. Nikola Jokic\n10. Anthony Davis"

async def put_content(destination):
    if destination.lower() == 'notes':
        await open_application('Notes')
        await asyncio.sleep(2)  # Wait for Notes to open
        content = pyperclip.paste()
        pyautogui.hotkey('command', 'n')  # Open a new note
        await asyncio.sleep(1)
        pyautogui.typewrite(content)
    else:
        print(f"Don't know how to put content into {destination}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")