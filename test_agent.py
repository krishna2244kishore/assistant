import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from agent import process_user_message

def test_conversation():
    """Test the calendar assistant with example conversations"""
    print("🧪 Testing Calendar Assistant\n")
    
    # Test cases based on user requirements
    test_cases = [
        "Hey, I want to schedule a call for tomorrow afternoon.",
        "Do you have any free time this Friday?",
        "Book a meeting between 3-5 PM next week.",
        "Hi there!",
        "What's my availability tomorrow?",
        "I need to book something for next week"
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"Test {i}: {test_input}")
        print("-" * 50)
        
        # Process the message
        result = process_user_message(test_input, {})
        response = result.get("response", "No response")
        
        print(f"Assistant: {response}")
        print()
    
    print("✅ All tests completed!")

if __name__ == "__main__":
    test_conversation() 