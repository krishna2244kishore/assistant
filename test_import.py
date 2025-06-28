import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

try:
    from backend.agent import process_user_message
    print("Successfully imported process_user_message from backend.agent")
    print("Function:", process_user_message)
except ImportError as e:
    print("Error importing:", e)
    print("Current Python path:", sys.path)
    print("Current working directory:", os.getcwd())
