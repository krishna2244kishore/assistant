# Local Development with Public URLs

## Using ngrok for Backend

1. **Install ngrok:**
   ```bash
   # Download from https://ngrok.com/download
   # Or use chocolatey on Windows:
   choco install ngrok
   ```

2. **Start your backend:**
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Create public tunnel:**
   ```bash
   ngrok http 8000
   ```

4. **Use the ngrok URL in your frontend:**
   ```bash
   # Set environment variable
   set BACKEND_URL=https://your-ngrok-url.ngrok.io
   
   # Or update the URL in frontend/app.py temporarily
   ```

## Using Streamlit Cloud for Frontend

1. **Deploy frontend to Streamlit Cloud**
2. **Set BACKEND_URL environment variable to your ngrok URL**
3. **Your frontend will be publicly accessible**

## URLs You'll Get

- **Frontend**: `https://your-app-name.streamlit.app`
- **Backend**: `https://your-ngrok-url.ngrok.io` (or Railway URL)

## Security Notes

- ngrok URLs are temporary and change each time you restart
- For production, use proper hosting services
- Railway URLs are permanent and more suitable for production 