# Tailor Talk - AI Calendar Booking Assistant

A smart calendar booking assistant that helps schedule and manage appointments.

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tailor_talk
   ```

2. **Install dependencies**
   ```bash
   # Install backend dependencies
   pip install -r backend/requirements.txt
   
   # Install frontend dependencies
   pip install -r frontend/requirements.txt
   
   # Install the package in development mode
   pip install -e .
   ```

3. **Set up environment variables**
   - Copy `.env.example` to `.env`
   - Update the values in `.env` as needed

## Running the Application

### Backend Server

```bash
# From the project root directory
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

### Frontend

```bash
# From the project root directory
streamlit run frontend/app.py
```

The frontend will be available at `http://localhost:8501`

## Project Structure

```
tailor_talk/
├── backend/              # Backend FastAPI application
│   ├── __init__.py
│   ├── main.py           # FastAPI app and routes
│   ├── agent.py          # Core AI logic
│   └── requirements.txt  # Backend dependencies
├── frontend/             # Streamlit frontend
│   ├── app.py            # Streamlit application
│   └── requirements.txt  # Frontend dependencies
├── .env                  # Environment variables
└── README.md             # This file
```

## API Documentation

Once the backend is running, you can access:

- Interactive API docs: `http://localhost:8000/docs`
- Alternative API docs: `http://localhost:8000/redoc`

## Troubleshooting

- **Backend not starting**: Ensure all dependencies are installed and port 8000 is available.
- **Frontend connection issues**: Check that the backend is running and accessible from the frontend URL.
- **CORS errors**: Verify that the CORS origins in `backend/main.py` match your frontend URL.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
