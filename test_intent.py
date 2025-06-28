import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from agent import extract_intent, BookingState

# Test the intent extraction
print("Testing intent extraction...")

# Test 1: "book meeting"
result1 = extract_intent("book meeting")
print(f"'book meeting' -> {result1['intent']} (confidence: {result1['confidence']})")

# Test 2: "today" (should be unknown without context)
result2 = extract_intent("today")
print(f"'today' -> {result2['intent']} (confidence: {result2['confidence']})")

print("Testing 'today' with booking context...")
# Test 3: "today" with booking context
state = BookingState(current_step="get_booking_details")
result3 = extract_intent("today", state.to_dict())
print(f"'today' with booking context -> {result3['intent']} (confidence: {result3['confidence']})")

# Test 4: "check availability"
result4 = extract_intent("check availability")
print(f"'check availability' -> {result4['intent']} (confidence: {result4['confidence']})")

print("\nTest completed!") 