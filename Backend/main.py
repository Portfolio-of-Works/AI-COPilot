from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
from google.cloud import dialogflowcx_v3 as dialogflow
from google.api_core.client_options import ClientOptions

# --- DATABASE IMPORTS ---
from sqlalchemy.orm import Session
from database import get_db, ChatHistory

# --- CLOUD-SMART AUTHENTICATION ---
if os.path.exists("google_creds.json"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_creds.json"

app = FastAPI(title="AI Co-pilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    text: str
    session_id: str = str(uuid.uuid4())

# --- DIALOGFLOW CONFIGURATION ---
PROJECT_ID = "copilot-493106" 
LOCATION = "global"           
AGENT_ID = "YOUR_AGENT_ID_HERE" # Ensure your real ID is here!

@app.get("/")
async def health_check():
    return {"status": "success", "message": "AI Co-pilot Backend is running!"}

@app.post("/api/chat")
async def chat_with_agent(message: ChatMessage, db: Session = Depends(get_db)):
    try:
        # 1. DIALOGFLOW CONNECTION
        client_options = ClientOptions(api_endpoint="dialogflow.googleapis.com")
        session_client = dialogflow.SessionsClient(client_options=client_options)
        session_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/agents/{AGENT_ID}/sessions/{message.session_id}"

        text_input = dialogflow.TextInput(text=message.text)
        query_input = dialogflow.QueryInput(text=text_input, language_code="zh-cn")
        request = dialogflow.DetectIntentRequest(session=session_path, query_input=query_input)

        response = session_client.detect_intent(request=request)
        ai_reply = response.query_result.response_messages[0].text.text[0]

        # 2. DATABASE RECORDING
        # This creates a new "row" in your GCP PostgreSQL table
        new_record = ChatHistory(
            session_id=message.session_id,
            user_message=message.text,
            ai_response=ai_reply
        )
        db.add(new_record)
        db.commit() # This officially saves it to the cloud!

        return {
            "reply": ai_reply,
            "session_id": message.session_id
        }
        
    except Exception as e:
        print(f"Error: {e}")
        # If Dialogflow or DB fails, we still want to know why
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")