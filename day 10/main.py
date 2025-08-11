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
from google.generativeai.types import HarmCategory, HarmBlockThreshold
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
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# In-memory datastore for chat histories
chat_histories = {}


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- Original Endpoints (TTS, Echo Bot, etc.) ---
@app.post("/tts")
async def tts(text: str = Form(...), voiceId: str = Form("en-US-natalie")):
    if not MURF_API_KEY:
        return JSONResponse(status_code=500, content={"error": "MURF API key not configured."})
    url = "https://api.murf.ai/v1/speech/generate"
    headers = {"Accept": "application/json", "Content-Type": "application/json", "api-key": MURF_API_KEY}
    payload = {"text": text, "voiceId": voiceId, "format": "MP3", "sampleRate": 24000}
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            audio_url = response_data.get("audioFile")
            if audio_url:
                return JSONResponse(content={"audio_url": audio_url})
            else:
                return JSONResponse(status_code=500, content={"error": "No audio URL in the API response.", "response": response_data})
        else:
            return JSONResponse(status_code=response.status_code, content={"error": "TTS generation failed.", "details": response.text})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "A server error occurred.", "details": str(e)})

@app.get("/voices")
async def get_voices():
    if not MURF_API_KEY:
        return JSONResponse(status_code=500, content={"error": "MURF API key not configured."})
    url = "https://api.murf.ai/v1/speech/voices"
    headers = {"Accept": "application/json", "api-key": MURF_API_KEY}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return JSONResponse(content=response.json())
        else:
            return JSONResponse(status_code=500, content={"error": "Failed to fetch voices.", "details": response.text})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "A server error occurred.", "details": str(e)})

@app.post("/tts/echo")
async def tts_echo(audio_file: UploadFile = File(...), voiceId: str = Form("en-US-katie")):
    if not ASSEMBLYAI_API_KEY or not MURF_API_KEY:
        return JSONResponse(status_code=500, content={"error": "API keys not configured."})

    try:
        transcriber = aai.Transcriber()
        saved_name = f"echo_{int(time.time())}_{uuid.uuid4().hex}_{audio_file.filename}"
        save_path = os.path.join(UPLOADS_DIR, saved_name)
        with open(save_path, "wb") as out_f:
            shutil.copyfileobj(audio_file.file, out_f)

        transcript = transcriber.transcribe(save_path)

        try:
            os.remove(save_path)
        except Exception:
            pass

        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(transcript.error)
        
        transcribed_text = transcript.text
        
        if not transcribed_text:
            return JSONResponse(status_code=400, content={"error": "Transcription returned no text. Please speak clearly."})

        murf_url = "https://api.murf.ai/v1/speech/generate"
        murf_headers = {"Accept": "application/json", "Content-Type": "application/json", "api-key": MURF_API_KEY}
        murf_payload = {"text": transcribed_text, "voiceId": voiceId, "format": "MP3", "sampleRate": 24000}
        
        murf_response = requests.post(murf_url, json=murf_payload, headers=murf_headers)
        murf_response.raise_for_status() 
        
        murf_audio_url = murf_response.json().get("audioFile")

        if not murf_audio_url:
            return JSONResponse(status_code=500, content={"error": "No audio URL in the Murf API response."})

        return JSONResponse(content={
            "transcript": transcribed_text,
            "echo_audio_url": murf_audio_url
        })
        
    except requests.exceptions.RequestException as e:
        return JSONResponse(status_code=500, content={"error": "Murf API request failed.", "details": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Echo generation failed.", "details": str(e)})
    finally:
        await audio_file.close()

@app.post("/llm/query")
async def llm_query(request: Request, text: str = Form(None), audio_file: UploadFile = File(None), voiceId: str = Form("en-US-katie")):
    if not GEMINI_API_KEY:
        return JSONResponse(status_code=500, content={"error": "GEMINI API key not configured."})

    def murf_tts(text_to_speak, voice_id):
        if not MURF_API_KEY:
            raise RuntimeError("MURF API key not configured.")
        murf_url = "https://api.murf.ai/v1/speech/generate"
        murf_headers = {"Accept": "application/json", "Content-Type": "application/json", "api-key": MURF_API_KEY}
        murf_payload = {"text": text_to_speak, "voiceId": voice_id, "format": "MP3", "sampleRate": 24000}
        murf_response = requests.post(murf_url, json=murf_payload, headers=murf_headers)
        murf_response.raise_for_status()
        murf_audio_url = murf_response.json().get("audioFile")
        if not murf_audio_url:
            raise RuntimeError("No audioFile returned from Murf.")
        return murf_audio_url

    try:
        if audio_file is not None:
            if not ASSEMBLYAI_API_KEY or not MURF_API_KEY or not GEMINI_API_KEY:
                return JSONResponse(status_code=500, content={"error": "One or more required API keys are not configured."})

            unique_name = f"llm_input_{int(time.time())}_{uuid.uuid4().hex}_{audio_file.filename}"
            save_path = os.path.join(UPLOADS_DIR, unique_name)
            with open(save_path, "wb") as out_f:
                shutil.copyfileobj(audio_file.file, out_f)

            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(save_path)

            try:
                os.remove(save_path)
            except Exception:
                pass

            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"Transcription failed: {transcript.error}")

            transcribed_text = transcript.text

            if not transcribed_text:
                return JSONResponse(status_code=400, content={"error": "Transcription returned no text. Please speak clearly."})

            llm_response_text = None
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                llm_obj = model.generate_content(transcribed_text)
                llm_response_text = llm_obj.text
            except Exception:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
                    payload = {"contents": [{"parts": [{"text": transcribed_text}]}]}
                    resp = requests.post(url, json=payload)
                    resp.raise_for_status()
                    resp_json = resp.json()
                    llm_response_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                except Exception as e:
                    raise Exception(f"Failed to call Gemini API: {e}")

            if not llm_response_text:
                return JSONResponse(status_code=500, content={"error": "LLM returned empty response."})

            murf_audio_url = murf_tts(llm_response_text, voiceId)

            return JSONResponse(content={
                "llm_response_text": llm_response_text,
                "llm_audio_url": murf_audio_url
            })

        elif text is not None:
            pass
        else:
            return JSONResponse(status_code=400, content={"error": "No `text` or `audio_file` provided."})

    except requests.exceptions.RequestException as e:
        return JSONResponse(status_code=500, content={"error": "External API request failed.", "details": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "An unexpected error occurred.", "details": str(e)})
    finally:
        if audio_file is not None:
            try:
                await audio_file.close()
            except Exception:
                pass


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

    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_file.file)

        if transcript.status == aai.TranscriptStatus.error:
            return JSONResponse(status_code=500, content={"error": f"Transcription failed: {transcript.error}"})

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

        murf_url = "https://api.murf.ai/v1/speech/generate"
        murf_headers = {"Accept": "application/json", "Content-Type": "application/json", "api-key": MURF_API_KEY}
        murf_payload = {"text": llm_response_text, "voiceId": voiceId, "format": "MP3", "sampleRate": 24000}
        
        murf_response = requests.post(murf_url, json=murf_payload, headers=murf_headers)
        murf_response.raise_for_status() 
        
        murf_data = murf_response.json()
        audio_url = murf_data.get("audioFile")

        if not audio_url:
            return JSONResponse(status_code=500, content={"error": "Murf API did not return an audio file."})

        history_dicts = [{"role": msg.role, "text": msg.parts[0].text} for msg in chat.history]

        return JSONResponse(content={
            "history": history_dicts,
            "audio_url": audio_url
        })
        
    except Exception as e:
        print(f"An error occurred in agent_chat: {e}")
        return JSONResponse(status_code=500, content={"error": f"An unexpected error occurred: {str(e)}"})
    finally:
        await audio_file.close()
