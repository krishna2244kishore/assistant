from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from agent import process_user_message

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    text = data.get("text", "")
    session_state = data.get("session_state", {})
    
    result = process_user_message(text, session_state)
    
    # Return both the response and the updated session state
    return {
        "response": result["response"],
        "session_state": result.get("session_state", {})
    }

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
