import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, TypedDict, Annotated, Sequence, Literal, Union
from enum import Enum
import pytz
from dateutil import parser, relativedelta

# LangGraph imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize LLM
llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")

# In-memory session storage (replace with a database in production)
sessions = {}

class BookingState(TypedDict):
    """State for the booking agent."""
    messages: Annotated[list[BaseMessage], lambda x, y: x + y]
    session_id: str
    current_step: str
    date: Optional[str]
    time_slot: Optional[str]
    duration: int
    timezone: str
    confirmed: bool
    pending_booking: Optional[Dict[str, Any]]

# Node functions
def greet_user(state: BookingState) -> BookingState:
    """Greet the user and ask how we can help."""
    response = "Hello! I'm your calendar assistant. I can help you schedule meetings or check availability. What would you like to do?"
    state["messages"].append(AIMessage(content=response))
    state["current_step"] = "get_booking_details"
    return state

def get_booking_details(state: BookingState) -> BookingState:
    """Extract booking details from user input."""
    # Get the last user message
    user_message = state["messages"][-1].content if state["messages"] and isinstance(state["messages"][-1], HumanMessage) else ""
    
    # Use LLM to extract booking details
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant that extracts booking details from messages.
        Extract the date, time, and duration for the booking. If any information is missing, ask for it.
        Today's date is {current_date}.
        
        Respond in this format:
        Date: [extracted date or 'not specified']
        Time: [extracted time or 'not specified']
        Duration: [extracted duration in minutes or 'not specified']
        Message: [your message to the user]"""),
        ("human", "{message}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "message": user_message,
        "current_date": datetime.now().strftime("%Y-%m-%d")
    })
    
    # Parse the response
    response_text = response.content
    
    # Update state with extracted information
    for line in response_text.split('\n'):
        if line.startswith("Date:"):
            date_str = line.split(":", 1)[1].strip().lower()
            if date_str != 'not specified':
                try:
                    parsed_date = parser.parse(date_str)
                    state["date"] = parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    pass
        elif line.startswith("Time:"):
            time_str = line.split(":", 1)[1].strip().lower()
            if time_str != 'not specified':
                state["time_slot"] = time_str
        elif line.startswith("Duration:"):
            duration_str = line.split(":", 1)[1].strip().lower()
            if duration_str != 'not specified':
                try:
                    state["duration"] = int(duration_str.split()[0])
                except (ValueError, IndexError):
                    pass
    
    # Add AI response to messages
    message = next((line for line in response_text.split('\n') if line.startswith("Message:")), "").replace("Message:", "").strip()
    state["messages"].append(AIMessage(content=message or "I'll help you with that."))
    
    return state

def check_availability(state: BookingState) -> BookingState:
    """Check calendar availability based on user's request."""
    # In a real implementation, this would check the actual calendar
    # For now, we'll just simulate availability
    state["messages"].append(AIMessage(
        content="I've checked my calendar and I'm available at that time! 🗓️\n\n"
               "Would you like to confirm this booking? (yes/no)"
    ))
    state["current_step"] = "confirm_booking"
    return state

def confirm_booking(state: BookingState) -> BookingState:
    """Ask user to confirm the booking details."""
    user_message = state["messages"][-1].content.lower() if state["messages"] and isinstance(state["messages"][-1], HumanMessage) else ""
    
    if "yes" in user_message or "confirm" in user_message:
        state["confirmed"] = True
        state["pending_booking"] = {
            "date": state.get("date"),
            "time_slot": state.get("time_slot"),
            "duration": state.get("duration", 60)
        }
        state["current_step"] = "finalize_booking"
    else:
        state["messages"].append(AIMessage(
            "No problem! Would you like to provide different details or cancel?"
        ))
    
    return state

def finalize_booking(state: BookingState) -> BookingState:
    """Finalize the booking and provide confirmation."""
    # In a real implementation, this would save the booking to a database
    booking = state["pending_booking"]
    
    state["messages"].append(AIMessage(
        content="✅ Your booking has been confirmed! 🎉\n\n"
               f"📅 Date: {booking.get('date')}\n"
               f"⏰ Time: {booking.get('time_slot')}\n"
               f"⏱️ Duration: {booking.get('duration')} minutes\n\n"
               "Is there anything else I can help you with?"
    ))
    
    # Reset the booking state
    state["current_step"] = "get_booking_details"
    state["date"] = None
    state["time_slot"] = None
    state["confirmed"] = False
    state["pending_booking"] = None
    
    return state

# Router functions
def route_booking_details(state: BookingState) -> str:
    """Route to next node based on booking details."""
    # Check if we have all required information
    if state.get("date") and state.get("time_slot"):
        return "check_availability"
    return "get_booking_details"

def route_confirmation(state: BookingState) -> str:
    """Route based on user's confirmation response."""
    user_message = state["messages"][-1].content.lower() if state["messages"] and isinstance(state["messages"][-1], HumanMessage) else ""
    
    if "yes" in user_message or "confirm" in user_message:
        return "confirmed"
    elif "no" in user_message or "cancel" in user_message:
        return "cancel"
    else:
        return "get_booking_details"

# Create the workflow
def create_booking_workflow():
    """Create the booking workflow using LangGraph."""
    workflow = StateGraph(BookingState)
    
    # Add nodes
    workflow.add_node("greet", greet_user)
    workflow.add_node("get_booking_details", get_booking_details)
    workflow.add_node("check_availability", check_availability)
    workflow.add_node("confirm_booking", confirm_booking)
    workflow.add_node("finalize_booking", finalize_booking)
    
    # Define edges
    workflow.set_entry_point("greet")
    workflow.add_edge("greet", "get_booking_details")
    
    # Conditional routing
    workflow.add_conditional_edges(
        "get_booking_details",
        route_booking_details,
        {
            "check_availability": "check_availability",
            "get_booking_details": "get_booking_details"
        }
    )
    
    workflow.add_edge("check_availability", "confirm_booking")
    
    workflow.add_conditional_edges(
        "confirm_booking",
        route_confirmation,
        {
            "confirmed": "finalize_booking",
            "get_booking_details": "get_booking_details",
            "cancel": END
        }
    )
    
    workflow.add_edge("finalize_booking", END)
    
    return workflow.compile()

# Initialize the workflow
booking_workflow = create_booking_workflow()

def process_user_message(message: str, session_id: str) -> tuple[str, str]:
    """
    Process a user message and return a response and session ID.
    
    Args:
        message: The user's message
        session_id: The current session ID
        
    Returns:
        A tuple of (response_text, session_id)
    """
    try:
        # Initialize or get session
        if session_id not in sessions:
            sessions[session_id] = {
                "messages": [
                    SystemMessage(content="You are a helpful AI assistant that helps users book appointments.")
                ],
                "session_id": session_id,
                "current_step": "greet",
                "date": None,
                "time_slot": None,
                "duration": 60,
                "timezone": "UTC",
                "confirmed": False,
                "pending_booking": None
            }
        
        # Add user message to conversation history
        sessions[session_id]["messages"].append(HumanMessage(content=message))
        
        # Run the workflow
        for output in booking_workflow.stream(sessions[session_id]):
            if "__end__" in output:
                break
            sessions[session_id].update(output)
        
        # Get the last AI message
        messages = sessions[session_id].get("messages", [])
        response = messages[-1].content if messages and isinstance(messages[-1], AIMessage) else "I'm not sure how to respond to that."
        
        return response, session_id
        
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return "I'm sorry, I encountered an error processing your request. Please try again.", session_id
