# main.py
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import requests
import os
import shutil
import assemblyai as asai

# Load environment variables from .env
load_dotenv()

app = FastAPI()

# Get AssemblyAI API key from environment variables
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

# Set the AssemblyAI API key
if ASSEMBLYAI_API_KEY:
    asai.settings.api_key = ASSEMBLYAI_API_KEY
else:
    print("Warning: ASSEMBLYAI_API_KEY not found in .env file.")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

MURF_API_KEY = os.getenv("MURF_API_KEY")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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

@app.post("/upload-audio")
async def upload_audio(audio_file: UploadFile = File(...)):
    # This endpoint is now obsolete as we're transcribing directly
    file_path = os.path.join(UPLOADS_DIR, audio_file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        file_size = os.path.getsize(file_path)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Could not save file: {e}"})
    finally:
        await audio_file.close()

    file_url = f"/uploads/{audio_file.filename}"

    return {
        "filename": audio_file.filename,
        "content_type": audio_file.content_type,
        "size": file_size, 
        "file_url": file_url,
    }

@app.post("/transcribe/file")
async def transcribe_audio_file(audio_file: UploadFile = File(...)):
    if not ASSEMBLYAI_API_KEY:
        return JSONResponse(status_code=500, content={"error": "AssemblyAI API key not configured."})

    try:
        transcriber = asai.Transcriber()

        transcript = transcriber.transcribe(audio_file.file)

        if transcript.status == asai.TranscriptStatus.error:
            raise Exception(transcript.error)

        return {"transcript": transcript.text}
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Transcription failed.", "details": str(e)})
    finally:
        await audio_file.close()