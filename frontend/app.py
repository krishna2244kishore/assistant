import streamlit as st
import requests
import uuid
from typing import Optional, Dict, List
import time
import os

# Page configuration
st.set_page_config(
    page_title="📅 Calendar Booking Assistant",
    page_icon="📅",
    layout="centered"
)

# Custom CSS for better UI
st.markdown("""
    <style>
    .stApp {
        max-width: 800px;
        margin: 0 auto;
    }
    .stChatInput {
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 700px;
        z-index: 100;
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .stChatMessage {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        max-width: 80%;
    }
    .stChatMessage[data-testid="stChatMessage"] {
        width: fit-content;
    }
    .stChatMessage[data-testid="stChatMessage"]:has(> div > div > .user-message) {
        margin-left: auto;
        background-color: #007bff;
        color: white;
        border-bottom-right-radius: 0;
    }
    .stChatMessage[data-testid="stChatMessage"]:has(> div > div > .assistant-message) {
        background-color: #f0f2f6;
        border-bottom-left-radius: 0;
    }
    .quick-actions {
        display: flex;
        gap: 0.5rem;
        margin: 1rem 0;
        flex-wrap: wrap;
    }
    .quick-actions button {
        flex: 1;
        min-width: 120px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "backend_session_state" not in st.session_state:
    st.session_state.backend_session_state = {}

# Configuration - Support both local and deployed environments
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def test_backend_connection():
    """Test if backend is reachable"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

def send_message(message: str) -> Optional[str]:
    """Send message to backend and return response"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={
                "text": message,  # Changed from "message" to "text"
                "session_state": st.session_state.backend_session_state
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            # Update the backend session state
            st.session_state.backend_session_state = data.get("session_state", {})
            return data.get("response")
            
        st.error(f"Error {response.status_code}: {response.text}")
        return None
        
    except Exception as e:
        st.error(f"Failed to connect to backend: {str(e)}")
        return None

def display_welcome_message():
    """Display welcome message and quick actions"""
    st.markdown("""
    # 📅 Calendar Booking Assistant
    
    Hi there! I can help you schedule meetings and check availability. Here are some things you can ask me:
    """)
    
    st.markdown("<div class='quick-actions'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📅 Book a meeting", use_container_width=True):
            st.session_state.user_input = "I'd like to book a meeting"
    with col2:
        if st.button("🕒 Check availability", use_container_width=True):
            st.session_state.user_input = "What's my availability tomorrow?"
    with col3:
        if st.button("📋 View upcoming", use_container_width=True):
            st.session_state.user_input = "Show my upcoming appointments"
    
    st.markdown("</div>", unsafe_allow_html=True)

def main():
    """Main application function"""
    # Check backend connection status
    if not test_backend_connection():
        st.error("⚠️ Backend is not running. Please start the backend server first.")
        if st.button("🔄 Try to start backend"):
            try:
                import subprocess
                subprocess.Popen(
                    ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
                    cwd="c:\\Users\\kisho\\tailor_talk"
                )
                st.success("✅ Backend started! Please refresh the page.")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to start backend: {str(e)}")
        return
    
    # Main app interface
    st.title("📅 Calendar Booking Assistant")
    
    # Display welcome message if no messages yet
    if not st.session_state.messages:
        display_welcome_message()
    
    # Display chat messages
    for message in st.session_state.messages:
        if not isinstance(message, dict):
            # Skip or log non-dict items
            continue
        role = message["role"]
        content = message["content"]
        with st.chat_message(role):
            st.markdown(f"<div class='{role}-message'>{content}</div>", unsafe_allow_html=True)
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Get assistant response
        with st.spinner("🤔 Thinking..."):
            response = send_message(prompt)
            
        if response:
            # Add assistant response to chat
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
    
    # Add clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.backend_session_state = {}  # Also clear backend session state
        st.rerun()
    
    # Add some space at the bottom for better mobile experience
    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
