from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

# 1. Initialize the FastAPI application
app = FastAPI(title="AI Co-pilot API")

# 2. Configure CORS (Cross-Origin Resource Sharing)
# This allows your React frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Note: We will restrict this to your GCP bucket URL later for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Define the data structure we expect from React
class ChatMessage(BaseModel):
    text: str
    session_id: str = str(uuid.uuid4()) # Creates a unique ID if one isn't provided

# 4. Health Check Endpoint (To verify the server is alive)
@app.get("/")
async def health_check():
    return {"status": "success", "message": "AI Co-pilot Backend is running!"}

# 5. The Main Chat Endpoint (Where React will send user messages)
@app.post("/api/chat")
async def chat_with_agent(message: ChatMessage):
    # TODO: In the next phase, we will insert the Google Dialogflow CX connection code right here.
    
    # For now, we return a mock response to prove React and Python are talking
    simulated_reply = f"【来自 Python 后端】我收到了你的问题：'{message.text}'。Dialogflow 引擎正在接入中..."
    
    return {
        "reply": simulated_reply,
        "session_id": message.session_id
    }