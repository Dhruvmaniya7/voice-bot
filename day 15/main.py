# main.py

from fastapi import FastAPI, Form, Request, UploadFile, File, Path, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import logging

load_dotenv()

# Import services and schemas AFTER loading .env
from services import assemblyai_service, gemini_service, murf_service
from schemas.chat_schemas import ChatHistoryResponse, AgentChatResponse

# --- Initial Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Dhwani Bot AI Agent")

# --- Static Files and Templates ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- In-memory Datastore ---
chat_histories = {}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Establishes a WebSocket connection and echoes back any message it receives.
    """
    await websocket.accept()
    logger.info("WebSocket connection established.")
    try:
        while True:
            # Wait for a message from the client
            data = await websocket.receive_text()
            logger.info(f"WebSocket received message: '{data}'")
            
            # Echo the received message back to the client
            await websocket.send_text(f"Echo: {data}")
            logger.info(f"WebSocket sent echo message back.")
            
    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket.")
    except Exception as e:
        logger.error(f"An error occurred in the WebSocket connection: {e}")
    finally:
        logger.info("Closing WebSocket connection.")


# --- Base Endpoint ---
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- Voice Service Endpoint ---
@app.get("/voices", response_model=list)
async def get_voices():
    try:
        return murf_service.get_available_voices()
    except Exception as e:
        logger.error(f"Error fetching voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Conversational Agent Endpoints ---
def convert_history_to_dicts(history) -> list[dict]:
    """Helper to convert Gemini's history object to a list of dicts for our schema."""
    if not history:
        return []
    return [{"role": msg.role, "text": msg.parts[0].text} for msg in history]


@app.get("/agent/chat/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    history = chat_histories.get(session_id, [])
    return ChatHistoryResponse(history=convert_history_to_dicts(history))


@app.delete("/agent/chat/{session_id}")
async def clear_chat_history(session_id: str):
    if session_id in chat_histories:
        del chat_histories[session_id]
        logger.info(f"Chat history cleared for session: {session_id}")
    return JSONResponse(content={"message": "Chat history cleared."})


@app.post("/agent/chat/{session_id}")
async def agent_chat(
    session_id: str = Path(..., description="The unique ID for the chat session."),
    audio_file: UploadFile = File(...),
    voiceId: str = Form("en-US-katie")
):
    try:
        # 1. Transcribe User Audio -> Text
        user_query_text = assemblyai_service.transcribe_audio(audio_file)
        logger.info(f"[{session_id}] User Query: {user_query_text}")

        if not user_query_text:
            history = chat_histories.get(session_id, [])
            return AgentChatResponse(history=convert_history_to_dicts(history), audio_url=None)

        # 2. Get LLM Response
        session_history = chat_histories.get(session_id, [])
        llm_response_text, updated_history = gemini_service.get_chat_response(session_history, user_query_text)
        chat_histories[session_id] = updated_history
        logger.info(f"[{session_id}] LLM Response: {llm_response_text}")

        # 3. Generate TTS Audio from LLM Response
        audio_url = murf_service.generate_murf_audio(llm_response_text, voiceId)
        
        return AgentChatResponse(history=convert_history_to_dicts(updated_history), audio_url=audio_url)

    except Exception as e:
        logger.error(f"An error occurred in agent_chat for session {session_id}: {e}", exc_info=True)
        fallback_text = "I'm having trouble connecting. Please try again later."
        history_dicts = convert_history_to_dicts(chat_histories.get(session_id, []))
        
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "history": history_dicts, "audio_url": None, "fallback_text": fallback_text}
        )
    finally:
        await audio_file.close()