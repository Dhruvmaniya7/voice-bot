from fastapi import FastAPI, Form, Request, UploadFile, File, Path
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import requests
import os
import shutil
import assemblyai as aai
import google.generativeai as genai
import uuid
import time

# Load environment variables from .env
load_dotenv()

app = FastAPI()

# Get API keys from environment variables
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Set the AssemblyAI API key
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY
else:
    print("Warning: ASSEMBLYAI_API_KEY not found in .env file.")

# Configure Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY not found in .env file. The LLM endpoints will not function.")

# Check for Murf API key
if not MURF_API_KEY:
    print("Warning: MURF_API_KEY not found in .env file. TTS functionality will be limited.")

# Serve static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In-memory datastore for chat histories
chat_histories = {}


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- Helper Function for Murf TTS ---
def generate_murf_audio(text_to_speak: str, voice_id: str):
    """Generates audio using Murf API and returns the audio URL."""
    if not MURF_API_KEY:
        raise Exception("MURF_API_KEY not configured.")
    
    url = "https://api.murf.ai/v1/speech/generate"
    headers = {"Accept": "application/json", "Content-Type": "application/json", "api-key": MURF_API_KEY}
    payload = {"text": text_to_speak, "voiceId": voice_id, "format": "MP3", "sampleRate": 24000}
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
    
    data = response.json()
    audio_url = data.get("audioFile")
    if not audio_url:
        raise Exception("Murf API did not return an audio file.")
    return audio_url


@app.get("/voices")
async def get_voices():
    if not MURF_API_KEY:
        return JSONResponse(status_code=500, content={"error": "MURF API key not configured."})
    url = "https://api.murf.ai/v1/speech/voices"
    headers = {"Accept": "application/json", "api-key": MURF_API_KEY}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except requests.exceptions.RequestException as e:
        return JSONResponse(status_code=502, content={"error": "Failed to connect to the voice service.", "details": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "A server error occurred while fetching voices.", "details": str(e)})


# --- Conversational Agent Endpoints ---

@app.get("/agent/chat/{session_id}")
async def get_chat_history(session_id: str):
    history = chat_histories.get(session_id, [])
    history_dicts = [{"role": msg.role, "text": msg.parts[0].text} for msg in history]
    return JSONResponse(content={"history": history_dicts})


@app.delete("/agent/chat/{session_id}")
async def clear_chat_history(session_id: str):
    if session_id in chat_histories:
        del chat_histories[session_id]
    return JSONResponse(content={"message": "Chat history cleared."})


@app.post("/agent/chat/{session_id}")
async def agent_chat(
    session_id: str = Path(..., description="The unique ID for the chat session."),
    audio_file: UploadFile = File(...),
    voiceId: str = Form("en-US-katie")
):
    if not (GEMINI_API_KEY and ASSEMBLYAI_API_KEY and MURF_API_KEY):
        return JSONResponse(status_code=500, content={"error": "One or more API keys are not configured."})

    user_query_text = ""
    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_file.file)

        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")

        user_query_text = transcript.text
        if not user_query_text:
            history = chat_histories.get(session_id, [])
            history_dicts = [{"role": msg.role, "text": msg.parts[0].text} for msg in history]
            return JSONResponse(content={"history": history_dicts, "audio_url": ""})

        session_history = chat_histories.get(session_id, [])
        model = genai.GenerativeModel('gemini-1.5-flash')
        chat = model.start_chat(history=session_history)
        response = chat.send_message(user_query_text)
        llm_response_text = response.text
        chat_histories[session_id] = chat.history  

        audio_url = generate_murf_audio(llm_response_text, voiceId)

        history_dicts = [{"role": msg.role, "text": msg.parts[0].text} for msg in chat.history]
        return JSONResponse(content={"history": history_dicts, "audio_url": audio_url})

    except Exception as e:
        print(f"An error occurred in agent_chat: {e}") 

        fallback_text = "I'm having trouble connecting right now. Please try again later."
        fallback_audio_url = None
        try:
            fallback_audio_url = generate_murf_audio(fallback_text, voiceId)
        except Exception as tts_e:
            print(f"Could not generate fallback audio: {tts_e}")

        current_history = chat_histories.get(session_id, [])
        history_dicts = [{"role": msg.role, "text": msg.parts[0].text} for msg in current_history]
        if user_query_text: 
            history_dicts.append({"role": "user", "text": user_query_text})
        history_dicts.append({"role": "model", "text": fallback_text})

        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "history": history_dicts,
                "audio_url": fallback_audio_url
            }
        )
    finally:
        await audio_file.close()