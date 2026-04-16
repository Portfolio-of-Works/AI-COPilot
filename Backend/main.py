from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
from google.cloud import dialogflowcx_v3 as dialogflow
from google.api_core.client_options import ClientOptions

# Only look for the local key if the file actually exists.
# If running in Cloud Run, Google handles this automatically!
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
AGENT_ID = "9bf63739-2aa0-4b65-9d6d-3ceef70bff7c" 

@app.get("/")
async def health_check():
    return {"status": "success", "message": "AI Co-pilot Backend is running!"}

@app.post("/api/chat")
async def chat_with_agent(message: ChatMessage):
    try:
        # 1. Set up the Dialogflow Client (Pointed to the global endpoint)
        client_options = ClientOptions(api_endpoint="dialogflow.googleapis.com")
        session_client = dialogflow.SessionsClient(client_options=client_options)

        # 2. Define the exact path to your current conversation session
        session_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/agents/{AGENT_ID}/sessions/{message.session_id}"

        # 3. Package the user's text into the format Dialogflow expects
        text_input = dialogflow.TextInput(text=message.text)
        query_input = dialogflow.QueryInput(text=text_input, language_code="zh-cn")

        # 4. Create the request
        request = dialogflow.DetectIntentRequest(
            session=session_path,
            query_input=query_input
        )

        # 5. Send the request to Google and wait for the AI to think
        response = session_client.detect_intent(request=request)
        
        # 6. Extract the AI's actual text reply from the complex response object
        ai_reply = response.query_result.response_messages[0].text.text[0]

        return {
            "reply": ai_reply,
            "session_id": message.session_id
        }
        
    except Exception as e:
        print(f"Dialogflow Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to AI Engine")