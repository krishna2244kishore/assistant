import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser, relativedelta
from typing import Dict, Any, Optional, List, Tuple

# Simulated in-memory calendar (for demo)
calendar_events = []  # Each event: {"date": date, "time": time, "duration": int, "title": str}

def extract_intent(text: str, session_state: Dict[str, Any] = None) -> str:
    """Extract user intent from natural language."""
    text_lower = text.lower().strip()
    
    # Check if we're in a booking flow and user provides time
    if session_state and session_state.get("waiting_for_time"):
        # If user just provides a number, treat as time selection
        if re.match(r'^\d{1,2}$', text_lower):
            return "select_time"
    
    # Check if we're after availability check and user selects a time
    if session_state and session_state.get("availability_date") and session_state.get("available_slots"):
        # If user just provides a number, treat as time selection
        if re.match(r'^\d{1,2}$', text_lower):
            return "select_time"
    
    # Check if we're in a time range booking flow and user selects a time
    if session_state and session_state.get("waiting_for_time") and session_state.get("available_slots"):
        # If user just provides a number, treat as time selection
        if re.match(r'^\d{1,2}$', text_lower):
            return "select_time"
    
    # Check if we're in a booking flow and user provides date/time
    if session_state and session_state.get("booking_flow"):
        # If we're in booking flow and user provides date/time, treat as booking
        if extract_date_time(text)[0] or extract_date_time(text)[1]:
            return "book"
    
    # Check if we're checking availability and user provides a date
    if session_state and session_state.get("checking_availability"):
        # If we're checking availability and user provides a date, treat as availability check
        if extract_date_time(text)[0]:
            return "check"
    
    # Booking intent
    if any(word in text_lower for word in ["book", "schedule", "meeting", "call", "appointment", "reserve"]):
        return "book"
    
    # Availability check intent
    if any(word in text_lower for word in ["free", "available", "availability", "slots", "open", "have time", "free time", "check availability"]):
        return "check"
    
    # Cancellation intent
    if any(word in text_lower for word in ["cancel", "remove", "delete", "unbook"]):
        return "cancel"
    
    # Greeting intent
    if any(word in text_lower for word in ["hi", "hello", "hey", "greetings"]):
        return "greeting"
    
    # Confirmation intent
    if any(word in text_lower for word in ["yes", "yeah", "sure", "ok", "okay", "confirm"]):
        return "confirm"
    
    # Rejection intent
    if any(word in text_lower for word in ["no", "nope", "not", "cancel"]):
        return "reject"
    
    return "unknown"

def extract_date_time(text: str) -> Tuple[Optional[datetime], Optional[str]]:
    """Extract date and time from natural language text."""
    text_lower = text.lower().strip()
    
    # Handle relative dates
    today = datetime.now()
    
    if "tomorrow" in text_lower:
        date = today + timedelta(days=1)
    elif "today" in text_lower:
        date = today
    elif "next week" in text_lower:
        # Next week means the next Monday (or today if it's Monday)
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:  # Today is Monday
            date = today + timedelta(days=7)  # Next Monday
        else:
            date = today + timedelta(days=days_until_monday)
    elif "this week" in text_lower:
        date = today + timedelta(days=1)  # Default to tomorrow
    else:
        # Handle day-of-week expressions like "this Friday", "next Monday"
        day_patterns = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2,
            'thursday': 3, 'thu': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6
        }
        
        date = None
        for day_name, day_num in day_patterns.items():
            if day_name in text_lower:
                if "this" in text_lower:
                    # This week's occurrence of the day
                    days_ahead = day_num - today.weekday()
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    date = today + timedelta(days=days_ahead)
                    break
                elif "next" in text_lower:
                    # Next week's occurrence of the day
                    days_ahead = day_num - today.weekday()
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    date = today + timedelta(days=days_ahead + 7)
                    break
                else:
                    # Just the day name - assume this week
                    days_ahead = day_num - today.weekday()
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    date = today + timedelta(days=days_ahead)
                    break
        
        # If no day-of-week found, try to parse specific dates
        if not date:
            try:
                # Remove common words that might confuse the parser
                clean_text = re.sub(r'\b(book|schedule|meeting|call|appointment|for|at|on)\b', '', text_lower)
                date = date_parser.parse(clean_text, fuzzy=True, default=today)
            except:
                date = None
    
    # Extract time
    time_str = None
    time_patterns = [
        r'(\d{1,2}):(\d{2})\s*(am|pm)?',  # 3:30 PM, 14:30
        r'(\d{1,2})\s*(am|pm)',  # 3 PM, 3pm
        r'^(\d{1,2})$',  # Just a number like "9" (only at start of text)
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if len(match.groups()) == 3:  # 3:30 PM format
                hour, minute, ampm = match.groups()
                hour = int(hour)
                if ampm and ampm.lower() == 'pm' and hour != 12:
                    hour += 12
                elif ampm and ampm.lower() == 'am' and hour == 12:
                    hour = 0
                time_str = f"{hour:02d}:{minute}"
            elif len(match.groups()) == 2:  # 3 PM format
                hour, ampm = match.groups()
                hour = int(hour)
                if ampm.lower() == 'pm' and hour != 12:
                    hour += 12
                elif ampm.lower() == 'am' and hour == 12:
                    hour = 0
                time_str = f"{hour:02d}:00"
            elif len(match.groups()) == 1:  # Just a number like "9"
                hour = int(match.group(1))
                # Assume AM for early hours, PM for later hours
                if hour < 6:  # Very early morning
                    hour += 12  # Make it PM
                elif hour < 12:  # Morning
                    pass  # Keep as AM
                else:  # Afternoon/evening
                    pass  # Keep as is (already PM)
                time_str = f"{hour:02d}:00"
            break
    
    # Handle time periods
    if "morning" in text_lower:
        time_str = "09:00"
    elif "afternoon" in text_lower:
        time_str = "14:00"
    elif "evening" in text_lower:
        time_str = "17:00"
    
    return date, time_str

def get_free_slots(date: datetime) -> List[str]:
    """Get available time slots for a given date."""
    # Business hours: 9 AM to 6 PM, 1 hour slots
    slots = [f"{hour:02d}:00" for hour in range(9, 18)]
    
    # Remove booked slots
    booked = []
    for e in calendar_events:
        event_date = e["date"]
        if isinstance(event_date, str):
            event_date = datetime.fromisoformat(event_date)
        if event_date.date() == date.date():
            booked.append(e["time"])
    return [s for s in slots if s not in booked]

def parse_time_to_hour(time_str: str) -> Optional[int]:
    """Parse time string to hour (0-23) for comparison."""
    time_str = time_str.strip().lower()
    
    # Handle formats like "3pm", "3:30pm", "15:30"
    if 'pm' in time_str:
        time_str = time_str.replace('pm', '').strip()
        if ':' in time_str:
            hour, minute = time_str.split(':')
            hour = int(hour)
            if hour != 12:  # 12pm stays 12
                hour += 12
            return hour
        else:
            hour = int(time_str)
            if hour != 12:  # 12pm stays 12
                hour += 12
            return hour
    elif 'am' in time_str:
        time_str = time_str.replace('am', '').strip()
        if ':' in time_str:
            hour, minute = time_str.split(':')
            hour = int(hour)
            if hour == 12:  # 12am becomes 0
                hour = 0
            return hour
        else:
            hour = int(time_str)
            if hour == 12:  # 12am becomes 0
                hour = 0
            return hour
    else:
        # Assume 24-hour format
        if ':' in time_str:
            hour, minute = time_str.split(':')
            return int(hour)
        else:
            return int(time_str)

def suggest_time_slots(free_slots: List[str]) -> str:
    """Suggest available time slots in a friendly way."""
    if not free_slots:
        return "I'm sorry, but I don't have any free slots available."
    
    if len(free_slots) <= 3:
        return f"I have these slots available: {', '.join(free_slots)}."
    else:
        return f"I have several slots available, including {', '.join(free_slots[:3])} and more."

def process_user_message(text: str, session_state: Dict[str, Any]) -> Dict[str, Any]:
    """Process user message and return appropriate response."""
    # Initialize session state if not provided
    if not session_state:
        session_state = {}
    
    intent = extract_intent(text, session_state)
    date, time_str = extract_date_time(text)
    
    # --- Confirmation of pending booking ---
    if session_state.get("pending_confirmation") and intent in ("confirm", "yes", "ok"):
        booking = session_state.get("pending_booking")
        if booking:
            # Add booking to calendar_events with all required fields
            calendar_events.append({
                "date": booking["date"],
                "time": booking["time"],
                "duration": booking.get("duration", 60),
                "title": booking.get("title", "Meeting")
            })
            session_state.clear()
            # Convert date string back to datetime for formatting
            if isinstance(booking['date'], str):
                booking_date = datetime.fromisoformat(booking['date'])
            else:
                booking_date = booking['date']
            return {
                "response": f"Your meeting for {booking_date.strftime('%A, %B %d at %H:%M')} has been confirmed! 📅",
                "session_state": session_state
            }
        else:
            session_state.clear()
            return {
                "response": "There is no pending booking to confirm.",
                "session_state": session_state
            }
    # --- Handle time selection after availability check ---
    if session_state.get("availability_date") and intent == "select_time":
        selected_date = session_state["availability_date"]
        # If selected_date is a string, convert to datetime
        if isinstance(selected_date, str):
            selected_date = datetime.fromisoformat(selected_date)
        # Get the time from the user's message
        try:
            hour = int(text.strip())
            selected_time = f"{hour:02d}:00"
        except Exception:
            session_state.clear()
            return {
                "response": "Sorry, I didn't understand that time. Please enter an hour like '13' for 1 PM.",
                "session_state": session_state
            }
        # Only set pending confirmation, do NOT clear session_state
        session_state["pending_confirmation"] = True
        session_state["pending_booking"] = {
            "date": selected_date.replace(hour=hour, minute=0).isoformat(),
            "time": selected_time,
            "duration": 60,
            "title": "Meeting"
        }
        return {
            "response": f"You selected {selected_time} on {selected_date.strftime('%A, %B %d')}. Do you want to book this slot? (yes/no)",
            "session_state": session_state
        }
    # --- Handle availability check flow ---
    if intent == "check_availability":
        if date:
            free_slots = get_free_slots(date)
            session_state.clear()
            if free_slots:
                session_state["availability_date"] = date.isoformat()
                return {
                    "response": f"On {date.strftime('%A, %B %d')}, I have these free slots: {', '.join(free_slots)}. Would you like to book one of these times? Please reply with the hour (e.g., '13' for 1 PM).",
                    "session_state": session_state
                }
            else:
                return {
                    "response": f"I'm sorry, but I don't have any free slots on {date.strftime('%A, %B %d')}. Would you like to check another date?",
                    "session_state": session_state
                }
        else:
            session_state["checking_availability"] = True
            return {
                "response": "I'd be happy to check my availability for you! What date would you like to check? You can say things like 'this Friday', 'tomorrow', or 'next week'.",
                "session_state": session_state
            }

    # --- Greeting ---
    if intent == "greeting":
        session_state.clear()
        return {
            "response": "Hello! I'm your calendar assistant. I can help you schedule meetings, check availability, or manage your calendar. What would you like to do?",
            "session_state": session_state
        }

    # --- Time selection (number only) ---
    if intent == "select_time":
        # Handle time selection after availability check
        if session_state.get("availability_date") and session_state.get("available_slots"):
            try:
                hour = int(text.strip())
                selected_time = f"{hour:02d}:00"
                if selected_time in session_state["available_slots"]:
                    selected_date = datetime.fromisoformat(session_state["availability_date"])
                    # Set pending confirmation, do NOT clear session_state
                    session_state["pending_confirmation"] = True
                    session_state["pending_booking"] = {
                        "date": selected_date.isoformat(),
                        "time": selected_time
                    }
                    return {
                        "response": f"You selected {selected_time} on {selected_date.strftime('%A, %B %d')}. Do you want to book this slot? (yes/no)",
                        "session_state": session_state
                    }
                else:
                    return {
                        "response": f"{selected_time} is not an available slot. Please select one of the available times.",
                        "session_state": session_state
                    }
            except Exception:
                pass
        
        # Handle time selection in time range booking flow
        if session_state.get("waiting_for_time") and session_state.get("available_slots"):
            try:
                hour = int(text.strip())
                selected_time = f"{hour:02d}:00"
                
                # Check if the selected time is in the available slots
                if selected_time in session_state["available_slots"]:
                    # Get the selected date from session state
                    selected_date = None
                    if session_state.get("selected_date"):
                        selected_date = datetime.fromisoformat(session_state["selected_date"])
                    elif session_state.get("availability_date"):
                        selected_date = datetime.fromisoformat(session_state["availability_date"])
                    else:
                        # Fallback to today if no date is set
                        selected_date = datetime.now()
                    
                    # Set pending confirmation, do NOT clear session_state
                    session_state["pending_confirmation"] = True
                    session_state["pending_booking"] = {
                        "date": selected_date.replace(hour=hour, minute=0).isoformat(),
                        "time": selected_time,
                        "duration": 60,
                        "title": "Meeting"
                    }
                    return {
                        "response": f"You selected {selected_time} on {selected_date.strftime('%A, %B %d')}. Do you want to book this slot? (yes/no)",
                        "session_state": session_state
                    }
                else:
                    return {
                        "response": f"{selected_time} is not an available slot. Please select one of the available times: {', '.join(session_state['available_slots'])}",
                        "session_state": session_state
                    }
            except Exception:
                return {
                    "response": "Sorry, I didn't understand that time. Please enter an hour like '15' for 3 PM.",
                    "session_state": session_state
                }
        
        # fallback to help message if not in time selection context
        return {
            "response": "I'm here to help with your calendar! You can ask me to: • Schedule a meeting (e.g., 'Book a call for tomorrow afternoon') • Check availability (e.g., 'Do you have free time this Friday?') • Cancel appointments\nWhat would you like to do?",
            "session_state": {}
        }

    # --- Confirmation intent ---
    if intent == "confirm" and session_state.get("pending_confirmation") and session_state.get("pending_booking"):
        booking = session_state["pending_booking"]
        date = datetime.fromisoformat(booking["date"])
        time = booking["time"]
        # Add booking to calendar_events
        calendar_events.append({
            "date": booking["date"],
            "time": booking["time"],
            "duration": booking.get("duration", 60),
            "title": booking.get("title", "Meeting")
        })
        # Clear session state after booking
        session_state.clear()
        return {
            "response": f"Your meeting has been booked for {date.strftime('%A, %B %d')} at {time}.",
            "session_state": session_state
        }

    # --- Cancel intent ---
    if intent == "cancel" and session_state.get("pending_confirmation"):
        session_state.clear()
        return {
            "response": "Booking cancelled. Let me know if you want to check availability or book another slot!",
            "session_state": session_state
        }

    # --- Availability check ---
    if intent == "check":
        if not date:
            session_state["checking_availability"] = True
            return {
                "response": "I'd be happy to check my availability for you! What date would you like to check? You can say things like 'this Friday', 'tomorrow', or 'next week'.",
                "session_state": session_state
            }
        free_slots = get_free_slots(date)
        session_state.clear()
        if free_slots:
            session_state["availability_date"] = date.isoformat()
            session_state["available_slots"] = free_slots
            return {
                "response": f"On {date.strftime('%A, %B %d')}, I have these free slots: {', '.join(free_slots)}. Would you like to book one of these times? Please reply with the hour (e.g., '13' for 1 PM).",
                "session_state": session_state
            }
        else:
            return {
                "response": f"I'm sorry, but I don't have any free slots on {date.strftime('%A, %B %d')}. Would you like to check another date?",
                "session_state": session_state
            }

    # --- Booking intent ---
    elif intent == "book":
        session_state["booking_flow"] = True
        if not date:
            session_state["waiting_for_date"] = True
            return {
                "response": "I'd be happy to help you schedule a meeting! When would you like to meet? You can say things like 'tomorrow afternoon', 'this Friday at 3pm', or 'next week'.",
                "session_state": session_state
            }
        free_slots = get_free_slots(date)
        session_state["selected_date"] = date.isoformat()
        
        # Check if user specified a time range (e.g., "between 3-5 PM")
        time_range_match = re.search(r'between\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*-\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', text.lower())
        
        if time_range_match:
            # User specified a time range, show available slots within that range
            start_time_str = time_range_match.group(1)
            end_time_str = time_range_match.group(2)
            
            # Convert to 24-hour format for comparison
            start_hour = parse_time_to_hour(start_time_str)
            end_hour = parse_time_to_hour(end_time_str)
            
            if start_hour is not None and end_hour is not None:
                # Filter free slots within the specified range
                available_in_range = []
                for slot in free_slots:
                    slot_hour = int(slot.split(':')[0])
                    if start_hour <= slot_hour <= end_hour:
                        available_in_range.append(slot)
                
                if available_in_range:
                    session_state["waiting_for_time"] = True
                    session_state["available_slots"] = available_in_range
                    return {
                        "response": f"Great! I have availability on {date.strftime('%A, %B %d')} between {start_time_str} and {end_time_str}. Available slots: {', '.join(available_in_range)}. Which time works best for you?",
                        "session_state": session_state
                    }
                else:
                    return {
                        "response": f"I'm sorry, but I don't have any free slots between {start_time_str} and {end_time_str} on {date.strftime('%A, %B %d')}. Would you like to check a different time or date?",
                        "session_state": session_state
                    }
        
        if time_str:
            if time_str in free_slots:
                # Direct booking without confirmation for specific times
                session_state.clear()
                calendar_events.append({
                    "date": date.replace(hour=int(time_str.split(':')[0]), minute=int(time_str.split(':')[1])).isoformat(),
                    "time": time_str,
                    "duration": 60,
                    "title": "Meeting"
                })
                return {
                    "response": f"Perfect! I've booked your meeting for {date.strftime('%A, %B %d')} at {time_str}. 📅",
                    "session_state": session_state
                }
            else:
                session_state["waiting_for_time"] = True
                return {
                    "response": f"I'm sorry, but {time_str} is not available on {date.strftime('%A, %B %d')}. {suggest_time_slots(free_slots)}",
                    "session_state": session_state
                }
        else:
            if free_slots:
                session_state["waiting_for_time"] = True
                session_state["available_slots"] = free_slots
                return {
                    "response": f"Great! I have availability on {date.strftime('%A, %B %d')}. {suggest_time_slots(free_slots)} What time works best for you?",
                    "session_state": session_state
                }
            else:
                session_state["waiting_for_date"] = True
                return {
                    "response": f"I'm sorry, but I don't have any free slots on {date.strftime('%A, %B %d')}. Would you like to check another date?",
                    "session_state": session_state
                }

    # --- Unknown intents and flow management ---
    else:
        # If we're checking availability and user provides a date, treat it as availability check
        if session_state.get("checking_availability") and date:
            free_slots = get_free_slots(date)
            session_state.clear()
            if free_slots:
                return {
                    "response": f"On {date.strftime('%A, %B %d')}, I have these free slots: {', '.join(free_slots)}. Would you like to book one of these times?",
                    "session_state": session_state
                }
            else:
                return {
                    "response": f"I'm sorry, but I don't have any free slots on {date.strftime('%A, %B %d')}. Would you like to check another date?",
                    "session_state": session_state
                }
        # If we're in booking flow and user provides date/time, treat it as booking
        elif session_state.get("booking_flow") and (date or time_str):
            if not date:
                session_state["waiting_for_date"] = True
                return {
                    "response": "I'm still waiting for you to tell me when you'd like to schedule the meeting. You can say things like 'tomorrow', 'this Friday', or 'next week'.",
                    "session_state": session_state
                }
            free_slots = get_free_slots(date)
            session_state["selected_date"] = date.isoformat()
            if time_str:
                if time_str in free_slots:
                    # Direct booking without confirmation for specific times
                    session_state.clear()
                    calendar_events.append({
                        "date": date.replace(hour=int(time_str.split(':')[0]), minute=int(time_str.split(':')[1])).isoformat(),
                        "time": time_str,
                        "duration": 60,
                        "title": "Meeting"
                    })
                    return {
                        "response": f"Perfect! I've booked your meeting for {date.strftime('%A, %B %d')} at {time_str}. 📅",
                        "session_state": session_state
                    }
                else:
                    session_state["waiting_for_time"] = True
                    return {
                        "response": f"I'm sorry, but {time_str} is not available on {date.strftime('%A, %B %d')}. {suggest_time_slots(free_slots)}",
                        "session_state": session_state
                    }
            else:
                if free_slots:
                    session_state["waiting_for_time"] = True
                    session_state["available_slots"] = free_slots
                    return {
                        "response": f"Great! I have availability on {date.strftime('%A, %B %d')}. {suggest_time_slots(free_slots)} What time works best for you?",
                        "session_state": session_state
                    }
                else:
                    session_state["waiting_for_date"] = True
                    return {
                        "response": f"I'm sorry, but I don't have any free slots on {date.strftime('%A, %B %d')}. Would you like to check another date?",
                        "session_state": session_state
                    }
        elif session_state.get("waiting_for_date"):
            return {
                "response": "I'm still waiting for you to tell me when you'd like to schedule the meeting. You can say things like 'tomorrow', 'this Friday', or 'next week'.",
                "session_state": session_state
            }
        elif session_state.get("waiting_for_time"):
            return {
                "response": "I'm still waiting for you to tell me what time you'd like to meet. You can say things like '3pm', '2:30 PM', or 'morning'.",
                "session_state": session_state
            }
        elif session_state.get("checking_availability"):
            return {
                "response": "I'm still waiting for you to tell me what date you'd like me to check. You can say things like 'tomorrow', 'this Friday', or 'next week'.",
                "session_state": session_state
            }
        else:
            return {
                "response": "I'm here to help with your calendar! You can ask me to:\n• Schedule a meeting (e.g., 'Book a call for tomorrow afternoon')\n• Check availability (e.g., 'Do you have free time this Friday?')\n• Cancel appointments\n\nWhat would you like to do?",
                "session_state": session_state
            } 