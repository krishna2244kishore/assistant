# Deployment Guide

## 🚀 Quick Deployment

### Backend (Railway)

1. **Push your code to GitHub**
2. **Go to [railway.app](https://railway.app)**
3. **Sign in with GitHub**
4. **Create new project → Deploy from GitHub repo**
5. **Select your repository**
6. **Railway will automatically detect the Procfile and deploy**

### Frontend (Streamlit Cloud)

1. **Go to [share.streamlit.io](https://share.streamlit.io)**
2. **Sign in with GitHub**
3. **Connect your repository**
4. **Configure:**
   - **Main file path**: `frontend/app.py`
   - **Python version**: 3.11
   - **Requirements file**: `frontend/requirements.txt`

### Connect Frontend to Backend

1. **Get your Railway backend URL** (e.g., `https://your-app-name.railway.app`)
2. **In Streamlit Cloud, go to Settings → Secrets**
3. **Add:**
   ```
   BACKEND_URL = "https://your-app-name.railway.app"
   ```

## 📁 Project Structure

```
tailor_talk/
├── backend/
│   ├── main.py          # FastAPI server
│   ├── agent.py         # AI agent logic
│   └── requirements.txt # Backend dependencies
├── frontend/
│   ├── app.py           # Streamlit app
│   └── requirements.txt # Frontend dependencies
├── requirements.txt     # Root dependencies (for Railway)
├── Procfile            # Railway deployment config
├── runtime.txt         # Python version
└── DEPLOYMENT.md       # This file
```

## 🔧 Local Development

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

## 🌐 URLs

- **Frontend**: `https://your-app-name.streamlit.app`
- **Backend**: `https://your-app-name.railway.app`

## 🐛 Troubleshooting

### Railway Issues
- **Nixpacks build failed**: Make sure you have `requirements.txt` and `Procfile` in the root
- **Import errors**: Check that all imports use absolute paths (e.g., `from backend.agent import ...`)

### Streamlit Issues
- **Backend connection failed**: Check that `BACKEND_URL` environment variable is set correctly
- **Module not found**: Make sure all dependencies are in `frontend/requirements.txt`

## 📝 Environment Variables

### Backend (Railway)
- `PORT`: Automatically set by Railway

### Frontend (Streamlit Cloud)
- `BACKEND_URL`: Your Railway backend URL

## 🔄 Updates

After making changes:
1. **Push to GitHub**
2. **Railway will auto-deploy**
3. **Streamlit Cloud will auto-deploy**
4. **Test both URLs** 