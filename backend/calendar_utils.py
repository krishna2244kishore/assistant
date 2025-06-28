"""
Calendar utilities for the Calendar Booking Assistant.
Supports both in-memory storage and Google Calendar integration.
"""
import os
import json
import re
from datetime import datetime, date, timedelta, timezone as tz
from typing import List, Dict, Optional, Tuple, Any, Union, Literal, Generator
import logging
from dateutil import parser, tz as dateutil_tz
import pytz
from pydantic import BaseModel, Field, validator
from enum import Enum

# Google Calendar API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEZONE = 'UTC'
DEFAULT_EVENT_DURATION = 60  # minutes
MIN_SLOT_DURATION = 15  # minutes
MAX_SLOT_DURATION = 1440  # 24 hours
MAX_EVENTS_RESULTS = 250

# In-memory storage as fallback
EVENT_STORE = {}

# Google Calendar settings
GOOGLE_CALENDAR_ENABLED = os.environ.get('GOOGLE_CALENDAR_ENABLED', 'false').lower() == 'true'
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Models
class EventStatus(str, Enum):
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"

class EventAttendee(BaseModel):
    email: str
    display_name: Optional[str] = None
    response_status: Optional[str] = None

class CalendarEvent(BaseModel):
    """Represents a calendar event with validation."""
    id: Optional[str] = None
    title: str = "Meeting"
    description: Optional[str] = None
    start: datetime
    end: datetime
    timezone: str = DEFAULT_TIMEZONE
    attendees: List[EventAttendee] = []
    location: Optional[str] = None
    status: EventStatus = EventStatus.CONFIRMED
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    creator: Optional[Dict[str, str]] = None
    organizer: Optional[Dict[str, str]] = None
    
    @validator('start', 'end', pre=True)
    def parse_datetime(cls, value):
        if isinstance(value, str):
            try:
                return parser.parse(value)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid datetime format: {value}") from e
        return value
    
    @validator('end')
    def validate_end_after_start(cls, v, values):
        if 'start' in values and v <= values['start']:
            raise ValueError("End time must be after start time")
        return v
    
    def to_google_event(self) -> Dict[str, Any]:
        """Convert to Google Calendar API event format."""
        return {
            'summary': self.title,
            'description': self.description,
            'start': {
                'dateTime': self.start.isoformat(),
                'timeZone': self.timezone,
            },
            'end': {
                'dateTime': self.end.isoformat(),
                'timeZone': self.timezone,
            },
            'attendees': [{
                'email': attendee.email,
                'displayName': attendee.display_name,
                'responseStatus': attendee.response_status or 'needsAction'
            } for attendee in self.attendees],
            'location': self.location,
            'status': self.status.value,
        }
    
    @classmethod
    def from_google_event(cls, event: Dict[str, Any]) -> 'CalendarEvent':
        """Create from Google Calendar API event format."""
        start = event.get('start', {})
        end = event.get('end', {})
        
        return cls(
            id=event.get('id'),
            title=event.get('summary', 'Meeting'),
            description=event.get('description'),
            start=parse_google_datetime(start),
            end=parse_google_datetime(end),
            timezone=start.get('timeZone', DEFAULT_TIMEZONE),
            attendees=[
                EventAttendee(
                    email=a.get('email'),
                    display_name=a.get('displayName'),
                    response_status=a.get('responseStatus')
                ) for a in event.get('attendees', [])
            ],
            location=event.get('location'),
            status=EventStatus(event.get('status', 'confirmed')),
            created=parser.parse(event.get('created')) if event.get('created') else None,
            updated=parser.parse(event.get('updated')) if event.get('updated') else None,
            creator=event.get('creator'),
            organizer=event.get('organizer')
        )

class TimeSlot(BaseModel):
    """Represents an available time slot."""
    start: datetime
    end: datetime
    available: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'start': self.start.isoformat(),
            'end': self.end.isoformat(),
            'available': self.available
        }

# Helper functions
def parse_google_datetime(dt_dict: Dict[str, str]) -> datetime:
    """Parse datetime from Google Calendar API format."""
    if 'dateTime' in dt_dict:
        dt = parser.parse(dt_dict['dateTime'])
        if dt.tzinfo is None:
            tz = dateutil_tz.gettz(dt_dict.get('timeZone', DEFAULT_TIMEZONE))
            dt = dt.replace(tzinfo=tz)
        return dt
    elif 'date' in dt_dict:
        return parser.parse(dt_dict['date']).replace(tzinfo=dateutil_tz.UTC)
    raise ValueError("Invalid datetime format in Google Calendar event")

def get_google_calendar_service() -> Any:
    """
    Get an authorized Google Calendar API service instance with improved error handling.
    
    Returns:
        googleapiclient.discovery.Resource or None: Authorized Calendar API service instance
                                                 or None if not available
    """
    if not GOOGLE_CALENDAR_AVAILABLE or not GOOGLE_CALENDAR_ENABLED:
        logger.warning("Google Calendar API is not enabled or available")
        return None
    
    creds = None
    token_path = os.environ.get('GOOGLE_TOKEN_PATH', 'token.json')
    credentials_path = os.environ.get('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    
    try:
        # Try to load existing credentials
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        # If no valid credentials, try to refresh or get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired credentials")
                creds.refresh(Request())
            else:
                logger.info("No valid credentials found, starting OAuth flow")
                if not os.path.exists(credentials_path):
                    logger.error(f"Credentials file not found at {credentials_path}")
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
        
        # Build and return the service
        return build('calendar', 'v3', credentials=creds, cache_discovery=False)
    
    except Exception as e:
        logger.error(f"Error initializing Google Calendar service: {str(e)}", exc_info=True)
        return None
    
    # Load credentials from token.json if it exists
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_file(token_path, SCOPES)
        except Exception as e:
            logger.warning(f"Error loading credentials: {e}")
    
    # If there are no valid credentials, try to log in or refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                return None
        else:
            if not os.path.exists(credentials_path):
                logger.warning(f"Google credentials file not found at {credentials_path}")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                logger.error(f"Error during Google OAuth flow: {e}")
                return None
    
    try:
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Error creating Calendar service: {e}")
        return None

def create_event(event: CalendarEvent, calendar_id: str = None) -> Dict[str, Any]:
    """
    Create a new calendar event.
    
    Args:
        event: CalendarEvent object representing the event to create
        calendar_id: Calendar ID (default: primary calendar)
        
    Returns:
        Dict containing event details and status
    """
    if not calendar_id:
        calendar_id = CALENDAR_ID
    
    service = get_google_calendar_service()
    if not service:
        logger.error("Failed to create event: Google Calendar service not available")
        return {"success": False, "error": "Calendar service not available"}
    
    try:
        # Convert to Google Calendar API format
        event_body = event.to_google_event()
        
        # Create the event
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            sendUpdates='all'
        ).execute()
        
        logger.info(f"Created event: {created_event.get('htmlLink')}")
        return {
            "success": True,
            "event_id": created_event.get('id'),
            "html_link": created_event.get('htmlLink'),
            "event": created_event
        }
    except HttpError as e:
        error_msg = f"Error creating event: {e}"
        logger.error(error_msg, exc_info=True)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error creating event: {e}"
        logger.error(error_msg, exc_info=True)
        return {"success": False, "error": error_msg}

def get_events(
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    calendar_id: str = None,
    timezone: str = DEFAULT_TIMEZONE,
    max_results: int = 100
) -> List[CalendarEvent]:
    """
    Get events from the calendar within a date range.
    
    Args:
        start_date: Start date/time (inclusive)
        end_date: End date/time (exclusive)
        calendar_id: Calendar ID (default: primary calendar)
        timezone: Timezone for the date range
        max_results: Maximum number of events to return
        
    Returns:
        List of CalendarEvent objects
    """
    if not calendar_id:
        calendar_id = CALENDAR_ID
    
    service = get_google_calendar_service()
    if not service:
        logger.error("Failed to get events: Google Calendar service not available")
        return []
    
    try:
        # Parse dates if they're strings
        if isinstance(start_date, str):
            start_date = parser.parse(start_date)
        if isinstance(end_date, str):
            end_date = parser.parse(end_date)
        
        # Ensure timezone awareness
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=dateutil_tz.gettz(timezone))
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=dateutil_tz.gettz(timezone))
        
        # Format for API
        time_min = start_date.isoformat()
        time_max = end_date.isoformat()
        
        # Get events from the calendar
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=min(max_results, MAX_EVENTS_RESULTS),
            singleEvents=True,
            orderBy='startTime',
            timeZone=timezone
        ).execute()
        
        # Convert to CalendarEvent objects
        events = events_result.get('items', [])
        return [CalendarEvent.from_google_event(event) for event in events]
    
    except HttpError as e:
        logger.error(f"Error getting events: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting events: {e}", exc_info=True)
        return []

def parse_datetime(dt_str: str, timezone: str = DEFAULT_TIMEZONE) -> datetime:
    """
    Parse a datetime string with timezone support and improved error handling.
    
    Args:
        dt_str: Datetime string to parse (can be in various formats)
        timezone: Timezone to use if not specified in dt_str
        
    Returns:
        datetime: Timezone-aware datetime object
        
    Raises:
        ValueError: If the datetime string cannot be parsed
    """
    if not dt_str:
        raise ValueError("Empty datetime string provided")
        
    try:
        # Try to parse with timezone info first
        dt = parser.parse(dt_str)
        
        # If no timezone info, use the provided timezone
        if dt.tzinfo is None:
            tz = dateutil_tz.gettz(timezone)
            if tz is None:
                logger.warning(f"Unknown timezone '{timezone}', falling back to UTC")
                tz = dateutil_tz.UTC
            dt = dt.replace(tzinfo=tz)
        
        return dt
    except (ValueError, TypeError, OverflowError) as e:
        logger.error(f"Error parsing datetime '{dt_str}': {e}", exc_info=True)
        raise ValueError(f"Invalid datetime format: {dt_str}") from e

def format_datetime(
    dt: Union[datetime, str], 
    timezone: str = DEFAULT_TIMEZONE, 
    format_str: str = '%Y-%m-%d %I:%M %p %Z',
    include_tz: bool = True
) -> str:
    """
    Format datetime to a human-readable string with robust timezone handling.
    
    Args:
        dt: Datetime object or ISO format string
        timezone: Timezone to use if dt is naive or to convert to
        format_str: Format string for datetime (strftime format)
        include_tz: Whether to include timezone in the output
        
    Returns:
        str: Formatted datetime string
        
    Raises:
        ValueError: If the datetime cannot be formatted
    """
    if not dt:
        raise ValueError("No datetime provided")
        
    try:
        # Parse if input is a string
        if isinstance(dt, str):
            dt = parse_datetime(dt, timezone)
        
        # Ensure we have a timezone-aware datetime
        if dt.tzinfo is None:
            tz = dateutil_tz.gettz(timezone) or dateutil_tz.UTC
            dt = dt.replace(tzinfo=tz)
        else:
            # Convert to target timezone if needed
            if timezone.upper() != dt.tzinfo.tzname(dt).upper():
                target_tz = dateutil_tz.gettz(timezone) or dateutil_tz.UTC
                dt = dt.astimezone(target_tz)
        
        # Format the datetime
        formatted = dt.strftime(format_str)
        
        # Add timezone if not included in format
        if include_tz and '%Z' not in format_str and '%z' not in format_str:
            tz_name = dt.strftime('%Z')
            if tz_name:
                formatted = f"{formatted} {tz_name}"
        
        return formatted
        
    except Exception as e:
        logger.error(f"Error formatting datetime {dt}: {e}", exc_info=True)
        raise ValueError(f"Could not format datetime: {e}") from e

async def get_free_slots(
    date_str: str,
    duration_minutes: int = DEFAULT_EVENT_DURATION,
    timezone: str = DEFAULT_TIMEZONE,
    calendar_id: str = None,
    working_hours: Tuple[int, int] = (9, 17),  # 9 AM to 5 PM by default
    slot_interval: int = 30,  # 30-minute slots by default
    buffer_minutes: int = 15,  # Buffer between events
    include_all_day: bool = False,
    max_slots: int = 20
) -> List[Dict[str, Any]]:
    """
    Get available time slots for a given date with comprehensive time slot calculation.
    
    Args:
        date_str: Date in YYYY-MM-DD format or natural language
        duration_minutes: Duration of the desired slot in minutes (default: 60)
        timezone: Timezone for the slots (default: UTC)
        calendar_id: Calendar ID to check (default: primary calendar)
        working_hours: Tuple of (start_hour, end_hour) in 24h format
        slot_interval: Interval between slots in minutes (default: 30)
        buffer_minutes: Buffer time between events in minutes (default: 15)
        include_all_day: Whether to include all-day events in the check
        max_slots: Maximum number of slots to return (default: 20)
        
    Returns:
        List of available time slots with start/end times and additional metadata
    """
    try:
        # Validate inputs
        if duration_minutes < MIN_SLOT_DURATION or duration_minutes > MAX_SLOT_DURATION:
            raise ValueError(f"Duration must be between {MIN_SLOT_DURATION} and {MAX_SLOT_DURATION} minutes")
            
        if slot_interval < 1:
            raise ValueError("Slot interval must be at least 1 minute")
            
        # Parse the date
        if isinstance(date_str, str):
            parsed_date = parse_datetime(date_str, timezone)
        else:
            parsed_date = date_str
            
        if not parsed_date:
            raise ValueError("Could not parse date")
            
        # Convert to target timezone
        tz = dateutil_tz.gettz(timezone) or dateutil_tz.UTC
        parsed_date = parsed_date.astimezone(tz)
        date_obj = parsed_date.date()
        
        # Get start and end of working day in the specified timezone
        work_start = parsed_date.replace(
            hour=working_hours[0], 
            minute=0, 
            second=0, 
            microsecond=0
        )
        work_end = parsed_date.replace(
            hour=working_hours[1], 
            minute=0, 
            second=0, 
            microsecond=0
        )
        
        # Adjust for timezone if needed
        if work_start.tzinfo is None:
            work_start = work_start.replace(tzinfo=tz)
        if work_end.tzinfo is None:
            work_end = work_end.replace(tzinfo=tz)
        
        # Get existing events for the day
        events = get_events(work_start, work_end, calendar_id, timezone)
        
        # Generate all possible slots within working hours
        slot_duration = timedelta(minutes=slot_interval)
        buffer_td = timedelta(minutes=buffer_minutes)
        duration_td = timedelta(minutes=duration_minutes)
        
        slots = []
        current = work_start
        
        while current + duration_td <= work_end:
            slot_end = current + duration_td
            
            # Check if this slot overlaps with any events
            is_available = True
            for event in events:
                # Skip all-day events if not including them
                if not include_all_day and isinstance(event, dict) and 'date' in event.get('start', {}):
                    continue
                    
                event_start = parse_google_datetime(event['start']) if isinstance(event, dict) else event.start
                event_end = parse_google_datetime(event['end']) if isinstance(event, dict) else event.end
                
                # Add buffer to event times
                event_start = event_start - buffer_td
                event_end = event_end + buffer_td
                
                # Check for overlap
                if (event_start < slot_end and event_end > current):
                    is_available = False
                    break
            
            if is_available:
                slots.append(TimeSlot(
                    start=current,
                    end=slot_end,
                    available=True
                ))
                
                # Stop if we've reached the maximum number of slots
                if len(slots) >= max_slots:
                    break
            
            current += slot_duration
        
        # Convert to list of dicts for JSON serialization
        return [{
            'start': slot.start.isoformat(),
            'end': slot.end.isoformat(),
            'formatted_start': format_datetime(slot.start, timezone),
            'formatted_end': format_datetime(slot.end, timezone),
            'duration_minutes': duration_minutes,
            'timezone': timezone
        } for slot in slots]
        
    except Exception as e:
        logger.error(f"Error in get_free_slots: {e}", exc_info=True)
        return []

def book_event(
    start_datetime: Union[str, datetime],
    end_datetime: Union[str, datetime],
    title: str = "Meeting",
    description: Optional[str] = None,
    timezone: str = DEFAULT_TIMEZONE,
    calendar_id: str = None,
    attendees: List[Dict[str, str]] = None,
    location: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Book an event in the calendar with comprehensive error handling.
    
    Args:
        start_datetime: Start time (ISO string or datetime object)
        end_datetime: End time (ISO string or datetime object)
        title: Event title (default: "Meeting")
        description: Event description (optional)
        timezone: Timezone for the event (default: UTC)
        calendar_id: Calendar ID (default: primary calendar)
        attendees: List of attendee dicts with 'email' key
        location: Event location (optional)
        **kwargs: Additional event properties
        
    Returns:
        Dict containing event details and status
    """
    try:
        # Parse and validate datetimes
        start_dt = parse_datetime(start_datetime, timezone) if isinstance(start_datetime, str) else start_datetime
        end_dt = parse_datetime(end_datetime, timezone) if isinstance(end_datetime, str) else end_datetime
        
        if not start_dt or not end_dt:
            raise ValueError("Invalid start or end datetime")
            
        if end_dt <= start_dt:
            raise ValueError("End time must be after start time")
        
        # Create CalendarEvent instance
        event = CalendarEvent(
            title=title,
            description=description,
            start=start_dt,
            end=end_dt,
            timezone=timezone,
            location=location,
            **kwargs
        )
        
        # Add attendees if provided
        if attendees:
            event.attendees = [
                EventAttendee(
                    email=attendee.get('email'),
                    display_name=attendee.get('display_name'),
                    response_status=attendee.get('response_status')
                ) for attendee in attendees if attendee.get('email')
            ]
        
        # Try to use Google Calendar if available
        service = get_google_calendar_service()
        if service and GOOGLE_CALENDAR_ENABLED:
            try:
                # Create event in Google Calendar
                created_event = service.events().insert(
                    calendarId=calendar_id or 'primary',
                    body=event.to_google_event(),
                    sendUpdates='all',
                    conferenceDataVersion=1 if kwargs.get('conferenceData') else 0
                ).execute()
                
                logger.info(f"Event created in Google Calendar: {created_event.get('htmlLink')}")
                return {
                    'success': True,
                    'message': 'Event created successfully',
                    'event_id': created_event.get('id'),
                    'html_link': created_event.get('htmlLink'),
                    'event': {
                        'id': created_event.get('id'),
                        'summary': created_event.get('summary', title),
                        'start': created_event['start'].get('dateTime', start_dt.isoformat()),
                        'end': created_event['end'].get('dateTime', end_dt.isoformat()),
                        'htmlLink': created_event.get('htmlLink', ''),
                        'status': 'confirmed',
                        'provider': 'google'
                    }
                }
                
            except Exception as e:
                logger.warning(f"Error creating Google Calendar event: {e}")
                logger.info("Falling back to in-memory storage")
        
        # Fall back to in-memory storage
        event_id = str(uuid.uuid4())
        event_dict = {
            'id': event_id,
            'summary': title,
            'description': description,
            'start': start_dt.isoformat(),
            'end': end_dt.isoformat(),
            'timezone': timezone,
            'location': location,
            'attendees': attendees or [],
            'status': 'confirmed',
            'provider': 'local',
            **kwargs
        }
        
        EVENT_STORE[event_id] = event_dict
        
        logger.info(f"Booked in-memory event: {title} from {start_dt} to {end_dt}")
        
        return {
            'success': True,
            'message': 'Event created in local storage',
            'event_id': event_id,
            'html_link': None,
            'event': event_dict
        }
        
    except ValueError as ve:
        error_msg = f"Validation error: {ve}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': str(ve),
            'message': 'Invalid event details',
            'provider': 'local'
        }
    except Exception as e:
        error_msg = f"Unexpected error creating event: {e}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to create event',
            'provider': 'local'
        }

def suggest_available_times(
    date_str: str,
    timezone: str = DEFAULT_TIMEZONE,
    duration_minutes: int = DEFAULT_EVENT_DURATION,
    num_suggestions: int = 3,
    calendar_id: str = None,
    working_hours: Tuple[int, int] = (9, 17),  # 9 AM to 5 PM by default
    buffer_minutes: int = 15,  # Buffer between events
    min_lead_time: int = 30,  # Minimum minutes from now until first suggestion
    max_days_ahead: int = 14  # Maximum days ahead to look for availability
) -> List[Dict[str, Any]]:
    """
    Suggest available meeting times with intelligent time slot generation.
    
    Args:
        date_str: Date in YYYY-MM-DD format or natural language
        timezone: Timezone for the suggestions (default: UTC)
        duration_minutes: Duration of each time slot in minutes (default: 60)
        num_suggestions: Number of time slots to suggest (default: 3)
        calendar_id: Calendar ID to check (default: primary calendar)
        working_hours: Tuple of (start_hour, end_hour) in 24h format
        buffer_minutes: Buffer time between events in minutes (default: 15)
        min_lead_time: Minimum minutes from now until first suggestion (default: 30)
        max_days_ahead: Maximum days ahead to look for availability (default: 14)
        
    Returns:
        List of available time slots with metadata
    """
    try:
        # Parse the input date
        if isinstance(date_str, str):
            base_date = parse_datetime(date_str, timezone)
        else:
            base_date = date_str
            
        if not base_date:
            raise ValueError("Invalid date format")
            
        # Convert to target timezone
        tz = dateutil_tz.gettz(timezone) or dateutil_tz.UTC
        now = datetime.now(tz)
        
        # If the requested date is today, adjust start time to be at least min_lead_time from now
        if base_date.date() == now.date():
            min_start_time = now + timedelta(minutes=min_lead_time)
            if min_start_time.hour >= working_hours[1]:
                # If it's already past working hours, start from next day
                base_date = base_date + timedelta(days=1)
                base_date = base_date.replace(hour=working_hours[0], minute=0, second=0, microsecond=0)
            else:
                # Round up to nearest 15 minutes
                rounded_minute = ((min_start_time.minute // 15) + 1) * 15
                if rounded_minute >= 60:
                    min_start_time = min_start_time.replace(hour=min_start_time.hour + 1, minute=0)
                else:
                    min_start_time = min_start_time.replace(minute=rounded_minute)
        
        # Get free slots for the day
        all_suggestions = []
        current_date = base_date
        days_checked = 0
        
        while len(all_suggestions) < num_suggestions and days_checked < max_days_ahead:
            # Get free slots for the current day
            free_slots = get_free_slots(
                date_str=current_date.strftime('%Y-%m-%d'),
                duration_minutes=duration_minutes,
                timezone=timezone,
                calendar_id=calendar_id,
                working_hours=working_hours,
                buffer_minutes=buffer_minutes,
                max_slots=num_suggestions * 2  # Get extra slots in case some are filtered out
            )
            
            # Filter out slots that are in the past if it's today
            if current_date.date() == now.date():
                free_slots = [
                    slot for slot in free_slots 
                    if parse_datetime(slot['start'], timezone) > now
                ]
            
            # Add date info to each slot
            for slot in free_slots:
                slot_start = parse_datetime(slot['start'], timezone)
                slot_end = parse_datetime(slot['end'], timezone)
                
                all_suggestions.append({
                    'start': slot_start.isoformat(),
                    'end': slot_end.isoformat(),
                    'formatted_start': format_datetime(slot_start, timezone, '%a, %b %d %I:%M %p'),
                    'formatted_end': format_datetime(slot_end, timezone, '%I:%M %p %Z'),
                    'date': slot_start.strftime('%Y-%m-%d'),
                    'duration_minutes': duration_minutes,
                    'timezone': timezone,
                    'time': f"{format_datetime(slot_start, timezone, '%-I:%M %p')} - {format_datetime(slot_end, timezone, '%-I:%M %p')}"
                })
            
            # Move to next day
            current_date += timedelta(days=1)
            days_checked += 1
        
        # Sort by start time and take the requested number of suggestions
        all_suggestions.sort(key=lambda x: x['start'])
        return all_suggestions[:num_suggestions]
        
    except ValueError as ve:
        logger.error(f"Validation error in suggest_available_times: {ve}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Error in suggest_available_times: {e}", exc_info=True)
        return []
