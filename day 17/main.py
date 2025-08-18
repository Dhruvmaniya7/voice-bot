import os
import logging
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import aiohttp
import asyncio
import json

# --- INITIAL SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")
load_dotenv()

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/tts")
async def tts(text: str = Form(...), voiceId: str = Form(...)):
    if not MURF_API_KEY:
        logger.error("MURF_API_KEY not configured.")
        return JSONResponse(status_code=500, content={"error": "Text-to-Speech service not configured."})

    url = "https://api.murf.ai/v1/speech/generate"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "api-key": MURF_API_KEY
    }
    payload = {
        "text": text,
        "voiceId": voiceId,
        "format": "MP3",
        "sampleRate": 24000
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        audio_url = response_data.get("audioFile")
        if audio_url:
            logger.info("TTS audio generated.")
            return JSONResponse(content={"audio_url": audio_url})
        else:
            logger.error(f"TTS API response did not contain an audio URL. Response: {response_data}")
            return JSONResponse(status_code=500, content={"error": "No audio URL in the API response."})
    except requests.exceptions.RequestException as e:
        logger.error(f"TTS API request failed: {e}")
        return JSONResponse(status_code=500, content={"error": "TTS generation failed.", "details": str(e)})


# --- Universal Streaming Setup ---

ASSEMBLYAI_STREAM_URL = "wss://streaming.assemblyai.com/v3/ws"

async def send_audio(ws, websocket):
    try:
        while True:
            data = await websocket.receive_bytes()
            await ws.send_bytes(data)
    except WebSocketDisconnect:
        pass

async def receive_transcript(ws, websocket):
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                response = json.loads(msg.data)

                # Log relevant transcript details to the terminal
                transcript = response.get("transcript", "")
                end_of_turn = response.get("end_of_turn", False)
                turn_order = response.get("turn_order", "N/A")
                session_id = response.get("session_id")

                if session_id:
                    logger.info(f"Session started: {session_id}")

                logger.info(f"Turn {turn_order} | Transcript: {transcript} (end_of_turn={end_of_turn})")

                # Optional: log when session closes if provided by API
                if response.get("type") == "session_closed":
                    logger.info("Streaming session closed")

                # Send the full Universal Streaming turn object to frontend
                await websocket.send_text(json.dumps(response))
    except Exception as e:
        logger.error(f"Error receiving transcript: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted for real-time transcription.")

    if not ASSEMBLYAI_API_KEY:
        logger.error("AssemblyAI API key not configured. Closing WebSocket.")
        await websocket.close(code=1008, reason="Server configuration error: Missing API key.")
        return

    logger.info(f"Connecting to AssemblyAI stream URL: {ASSEMBLYAI_STREAM_URL}")

    params = {
        "sample_rate": 16000,
        "format_turns": "true",
    }
    ws_headers = {
        "Authorization": ASSEMBLYAI_API_KEY,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                ASSEMBLYAI_STREAM_URL,
                headers=ws_headers,
                params=params,
                autoping=True
            ) as ws:
                logger.info("Connected to AssemblyAI WebSocket streaming service.")
                audio_task = asyncio.create_task(send_audio(ws, websocket))
                transcript_task = asyncio.create_task(receive_transcript(ws, websocket))

                done, pending = await asyncio.wait(
                    [audio_task, transcript_task],
                    return_when=asyncio.FIRST_EXCEPTION
                )

                for task in pending:
                    task.cancel()

    except Exception as e:
        logger.error(f"WebSocket transcription error: {e}")
        await websocket.close(code=1011, reason="Transcription error or disconnection.")
