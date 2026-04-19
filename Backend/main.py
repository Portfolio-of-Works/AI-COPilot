from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
import os
import json
import asyncio
from google.cloud import dialogflowcx_v3 as dialogflow
from google.api_core.client_options import ClientOptions
from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool
from pydantic import Field
from fastapi.openapi.utils import get_openapi

# DATABASE IMPORTS
from sqlalchemy.orm import Session
from database import get_db, ChatHistory

# CLOUD-SMART AUTHENTICATION
if os.path.exists("google_creds.json"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_creds.json"

app = FastAPI(
    title="AI Co-pilot Hybrid API",
    servers=[{"url": "https://copilot-backend-1027738760886.us-central1.run.app"}]
)

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

# --- CONFIGURATIONS ---

# 1. Dialogflow Configuration
PROJECT_ID = "copilot-493106"
LOCATION = "global"
AGENT_ID = "9bf63739-2aa0-4b65-9d6d-3ceef70bff7c"
client_options = ClientOptions(api_endpoint="dialogflow.googleapis.com")
session_client = dialogflow.SessionsClient(client_options=client_options)

# 2. Vertex AI Configuration
genai_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location="us-central1"
)

@app.get("/")
async def health_check():
    return {"status": "success", "message": "Hybrid Backend is running!"}

# ==========================================
# ENGINE A: The Fast Route (Dialogflow)
# ==========================================
@app.post("/api/chat")
async def chat_with_agent(message: ChatMessage, db: Session = Depends(get_db)):
    """
    This endpoint talks ONLY to Dialogflow. It expects Dialogflow to check the
    Data Store and return quickly. If Dialogflow returns the secret code
    '[TRIGGER_DEEP_SEARCH]', the frontend will know to call Engine B.
    """
    try:
        session_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/agents/{AGENT_ID}/sessions/{message.session_id}"
        text_input = dialogflow.TextInput(text=message.text)
        query_input = dialogflow.QueryInput(text=text_input, language_code="zh-cn")
        request = dialogflow.DetectIntentRequest(session=session_path, query_input=query_input)

        response = session_client.detect_intent(request=request)
        ai_reply = response.query_result.response_messages[0].text.text[0]

        # Only record to the database if it's a REAL answer, not the secret code
        if ai_reply != "[TRIGGER_DEEP_SEARCH]":
            new_record = ChatHistory(
                session_id=message.session_id,
                user_message=message.text,
                ai_response=ai_reply
            )
            db.add(new_record)
            db.commit()

        return {
            "reply": ai_reply,
            "session_id": message.session_id
        }

    except Exception as e:
        print(f"Dialogflow Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# ==========================================
# ENGINE B: The Slow/Stream Route (Vertex AI)
# ==========================================
@app.post("/api/stream-chat")
async def stream_chat(message: ChatMessage, db: Session = Depends(get_db)):
    """
    This endpoint is triggered by the frontend ONLY when Dialogflow fails.
    It performs a deep Google Search and streams the response back word-by-word.
    """
    async def event_generator():
        full_ai_response = ""
        try:
            # 1. Trigger the Vertex AI Streaming method with Google Search
            response_stream = genai_client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=f"Using Google Search, provide a highly detailed, comprehensive professional response in Simplified Chinese for: {message.text}",
                config=GenerateContentConfig(
                    temperature=0.2,
                    tools=[Tool(google_search=GoogleSearch())]
                )
            )

            # 2. Yield each chunk as soon as it's generated
            for chunk in response_stream:
                if chunk.text:
                    text_chunk = chunk.text
                    full_ai_response += text_chunk
                    
                    # Package chunk in JSON to prevent SSE formatting breaks
                    safe_payload = json.dumps({"text": text_chunk}, ensure_ascii=False)
                    yield f"data: {safe_payload}\n\n"
                    
                    await asyncio.sleep(0.01) # Small buffer

            # 3. Signal completion
            yield "data: [DONE]\n\n"

            # 4. Save the full streaming interaction to the Database silently
            new_record = ChatHistory(
                session_id=message.session_id,
                user_message=message.text,
                ai_response=full_ai_response
            )
            db.add(new_record)
            db.commit()

        except Exception as e:
            print(f"Streaming Error: {e}")
            error_payload = json.dumps({"error": str(e)})
            yield f"data: {error_payload}\n\n"

    # Return the special FastAPI StreamingResponse
    return StreamingResponse(event_generator(), media_type="text/event-stream")