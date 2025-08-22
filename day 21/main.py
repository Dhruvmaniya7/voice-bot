import os
from dotenv import load_dotenv
import logging
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path as PathLib
import json
import asyncio
import config
from typing import Type
import base64
import websockets
from datetime import datetime
import re # Import regular expressions

import assemblyai as aai
from assemblyai.streaming.v3 import (
    BeginEvent,
    StreamingClient,
    StreamingClientOptions,
    StreamingError,
    StreamingEvents,
    StreamingParameters,
    TerminationEvent,
    TurnEvent,
)
import google.generativeai as genai

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = FastAPI()

# --- Directories and Templates ---
BASE_DIR = PathLib(__file__).resolve().parent
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Create uploads folder on startup ---
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# --- Gemini Model Initialization ---
if config.GEMINI_API_KEY:
    genai.configure(api_key=config.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None
    logging.warning("Gemini model not initialized. GEMINI_API_KEY is missing.")


# --- MODIFIED Gemini function that streams to Murf AND back to client ---
async def get_llm_response_stream(transcript: str, client_websocket: WebSocket):
    if not transcript or not transcript.strip():
        logging.warning("Empty transcript received, skipping Gemini and Murf.")
        return

    if not gemini_model:
        logging.error("Cannot get LLM response because Gemini model is not initialized.")
        return

    logging.info(f"Sending to Gemini: '{transcript}'")
    
    murf_uri = f"wss://api.murf.ai/v1/speech/stream-input?api-key={config.MURF_API_KEY}&sample_rate=44100&channel_type=MONO&format=WAV"
    
    try:
        async with websockets.connect(murf_uri) as websocket:
            logging.info("Successfully connected to Murf AI for streaming.")
            
            config_msg = {
                "voice_config": {"voiceId": "en-US-darnell", "style": "Conversational"},
                "context_id": "day21-streaming-context"
            }
            await websocket.send(json.dumps(config_msg))
            logging.info("Murf voice and context config sent.")

            async def receive_and_forward_audio():
                chunk_count = 1
                while True:
                    try:
                        response_str = await websocket.recv()
                        response = json.loads(response_str)

                        if "audio" in response and response['audio']:
                            base64_chunk = response['audio']
                            # Send audio data to the client
                            await client_websocket.send_text(
                                json.dumps({"type": "audio", "data": base64_chunk})
                            )
                            logging.info(f"Sent audio chunk {chunk_count} to client.")
                            chunk_count += 1

                        if response.get("final"):
                            logging.info("Murf confirms final audio chunk received.")
                            await client_websocket.send_text(json.dumps({"type": "audio_end"}))
                            logging.info("Sent audio_end signal to client.")
                            break
                    except websockets.ConnectionClosed:
                        logging.info("Murf connection closed.")
                        break
            
            receiver_task = asyncio.create_task(receive_and_forward_audio())

            def generate_sync():
                return gemini_model.generate_content(transcript, stream=True)

            loop = asyncio.get_running_loop()
            gemini_response_stream = await loop.run_in_executor(None, generate_sync)

            sentence_buffer = ""
            print("\n--- GEMINI STREAMING RESPONSE ---")
            for chunk in gemini_response_stream:
                if chunk.text:
                    sentence_buffer += chunk.text
                    print(chunk.text, end="", flush=True)
                    
                    sentences = re.split(r'(?<=[.?!])\s+', sentence_buffer)
                    
                    if len(sentences) > 1:
                        for sentence in sentences[:-1]:
                            if sentence.strip():
                                text_msg = {"text": sentence.strip(), "end": False}
                                await websocket.send(json.dumps(text_msg))
                        sentence_buffer = sentences[-1]

            if sentence_buffer.strip():
                text_msg = {"text": sentence_buffer.strip(), "end": True}
                await websocket.send(json.dumps(text_msg))

            print("\n--- END OF GEMINI STREAM ---\n")

            await receiver_task

    except Exception as e:
        logging.error(f"Error in LLM/TTS streaming function: {e}", exc_info=True)


# --- FastAPI Routes ---
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

async def send_client_message(ws: WebSocket, message: dict):
    """Helper function to send JSON messages to the client."""
    await ws.send_text(json.dumps(message))

@app.websocket("/ws")
async def websocket_audio_streaming(websocket: WebSocket):
    await websocket.accept()
    main_loop = asyncio.get_running_loop()
    
    if not config.ASSEMBLYAI_API_KEY:
        logging.error("ASSEMBLYAI_API_KEY not configured")
        await send_client_message(websocket, {"type": "error", "message": "AssemblyAI API key not configured on the server."})
        await websocket.close(code=1000)
        return

    client = StreamingClient(StreamingClientOptions(api_key=config.ASSEMBLYAI_API_KEY))

    def on_turn(self: Type[StreamingClient], event: TurnEvent):
        transcript_text = event.transcript
        
        if event.end_of_turn and event.turn_is_formatted:
            logging.info(f"Final formatted turn: '{transcript_text}'")
            
            # Send the final transcription to the client UI
            transcript_message = {
                "type": "transcription",
                "text": transcript_text,
                "end_of_turn": True
            }
            asyncio.run_coroutine_threadsafe(send_client_message(websocket, transcript_message), main_loop)

            # Start the Gemini -> Murf -> Client audio stream
            asyncio.run_coroutine_threadsafe(get_llm_response_stream(transcript_text, websocket), main_loop)
    
    def on_begin(self: Type[StreamingClient], event: BeginEvent): logging.info(f"Transcription session started.")
    def on_terminated(self: Type[StreamingClient], event: TerminationEvent): logging.info(f"Transcription session terminated.")
    def on_error(self: Type[StreamingClient], error: StreamingError): logging.error(f"AssemblyAI streaming error: {error}")

    client.on(StreamingEvents.Begin, on_begin)
    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Termination, on_terminated)
    client.on(StreamingEvents.Error, on_error)

    try:
        client.connect(StreamingParameters(sample_rate=16000, format_turns=True))
        await send_client_message(websocket, {"type": "status", "message": "Connected to transcription service."})

        # CORRECTED CODE BLOCK
        while True:
            message = await websocket.receive()
            if "bytes" in message:
                client.stream(message["bytes"])
            # The "elif" for "EOF" has been removed.
            
    except WebSocketDisconnect:
        logging.info("Client disconnected.")
    except Exception as e:
        logging.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        client.disconnect()
        if websocket.client_state.name != 'DISCONNECTED':
            await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)