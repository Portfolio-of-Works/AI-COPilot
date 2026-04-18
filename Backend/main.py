from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
from google.cloud import dialogflowcx_v3 as dialogflow
from google.api_core.client_options import ClientOptions
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, grounding
from pydantic import Field
from fastapi.openapi.utils import get_openapi

# --- DATABASE IMPORTS ---
from sqlalchemy.orm import Session
from database import get_db, ChatHistory

# --- CLOUD-SMART AUTHENTICATION ---
if os.path.exists("google_creds.json"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_creds.json"

app = FastAPI(
    title="AI Co-pilot API",
    servers=[{"url": "https://copilot-backend-1027738760886.us-central1.run.app"}]
)

# --- 2. Force OpenAPI 3.0.0 for Dialogflow ---
def custom_openapi():
    if app.openapi_schema: return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title, version=app.version, routes=app.routes, servers=app.servers
    )
    openapi_schema["openapi"] = "3.0.0" 
    app.openapi_schema = openapi_schema
    return app.openapi_schema
app.openapi = custom_openapi

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
LOCATION = "us-central1"           
AGENT_ID = "9bf63739-2aa0-4b65-9d6d-3ceef70bff7c"

@app.get("/")
async def health_check():
    return {"status": "success", "message": "AI Co-pilot Backend is running!"}

client_options = ClientOptions(api_endpoint="us-central1-dialogflow.googleapis.com")
session_client = dialogflow.SessionsClient(client_options=client_options)

@app.post("/api/chat")
async def chat_with_agent(message: ChatMessage, db: Session = Depends(get_db)):
    try:
        # 1. DIALOGFLOW CONNECTION
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
    
# 1. Define the Tool Request Schema
class InternetSearchRequest(BaseModel):
    query: str = Field(..., description="The accounting concept or rule to search for on the internet, e.g., '什么是固定资产折旧'")

# 2. Define the Tool Response Schema
class InternetSearchResponse(BaseModel):
    search_result: str = Field(..., description="The summary of the internet search results.")

vertexai.init(project="copilot-493106", location="us-central1")
search_tool = Tool.from_dict({"google_search": {}})
model = GenerativeModel("gemini-2.5-flash")

# 3. Create the Tool Endpoint
@app.post("/api/tool/search", response_model=InternetSearchResponse, summary="Internet Search Tool", description="Searches the internet for general accounting definitions when the internal manual does not contain the answer.")
async def internet_search_tool(request: InternetSearchRequest):
    user_query = request.query
    
    try:
        print(f"Playbook requested internet search for: {user_query}")
        response = model.generate_content(
            f"Search and define: {user_query}",
            tools=[search_tool],
            generation_config={"temperature": 0.0,
                               "max_output_tokens": 400,},
            
        )
        return InternetSearchResponse(search_result=response.text)
        
        return InternetSearchResponse(search_result=final_answer)
    except Exception as e:
        return InternetSearchResponse(search_result="Search timed out.")