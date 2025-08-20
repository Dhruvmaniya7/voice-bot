import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

if not ASSEMBLYAI_API_KEY:
    logging.warning("ASSEMBLYAI_API_KEY not found in .env file. Please create one.")


from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
from pathlib import Path as PathLib
import json
import asyncio
import config
from typing import Type

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


# --- Gemini Model Initialization ---
if config.GEMINI_API_KEY:
    genai.configure(api_key=config.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None
    logging.warning("Gemini model not initialized. GEMINI_API_KEY is missing.")


# --- Function to get streaming response from Gemini ---
async def get_llm_response_stream(transcript: str):
    """Sends transcript to Gemini and prints the streaming response to the console."""
    if not gemini_model:
        logging.error("Cannot get LLM response because Gemini model is not initialized.")
        return

    logging.info(f"Sending to Gemini: '{transcript}'")
    try:
        def generate_sync():
            return gemini_model.generate_content(transcript, stream=True)

        loop = asyncio.get_running_loop()
        response_stream = await loop.run_in_executor(None, generate_sync)

        full_response = ""
        print("\n--- GEMINI STREAMING RESPONSE ---")
        for chunk in response_stream:
            if chunk.text:
                full_response += chunk.text
                print(chunk.text, end="", flush=True)
        
        print("\n--- END OF GEMINI STREAM ---")
        logging.info(f"Final Gemini Response: {full_response}")

    except Exception as e:
        logging.error(f"Error getting Gemini response: {e}")


# --- FastAPI Routes ---
@app.get("/")
async def home(request: Request):
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_audio_streaming(websocket: WebSocket):
    """Handles the WebSocket connection for real-time audio streaming and transcription."""
    await websocket.accept()
    
    # --- MODIFIED: Get a reference to the main event loop ---
    main_loop = asyncio.get_running_loop()
    
    if not config.ASSEMBLYAI_API_KEY:
        logging.error("ASSEMBLYAI_API_KEY not configured")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "AssemblyAI API key not configured on the server."
        }))
        await websocket.close(code=1000)
        return

    transcription_queue = asyncio.Queue()

    client = StreamingClient(
        StreamingClientOptions(api_key=config.ASSEMBLYAI_API_KEY)
    )

    def on_begin(self: Type[StreamingClient], event: BeginEvent):
        logging.info(f"Transcription session started: {event.id}")

    def on_turn(self: Type[StreamingClient], event: TurnEvent):
        transcript_text = event.transcript
        
        if event.end_of_turn and event.turn_is_formatted:
            logging.info(f"Final formatted turn: '{transcript_text}'")
            
            # --- MODIFIED: Use thread-safe call to schedule the coroutine ---
            asyncio.run_coroutine_threadsafe(
                get_llm_response_stream(transcript_text), 
                main_loop
            )

            try:
                transcription_queue.put_nowait({
                    "type": "transcription",
                    "text": transcript_text,
                    "end_of_turn": True
                })
            except asyncio.QueueFull:
                logging.warning("Transcription queue is full. A transcript might be lost.")
    
    def on_terminated(self: Type[StreamingClient], event: TerminationEvent):
        logging.info(f"Transcription session terminated. Audio duration: {event.audio_duration_seconds}s")

    def on_error(self: Type[StreamingClient], error: StreamingError):
        logging.error(f"AssemblyAI streaming error: {error}")
        try:
            transcription_queue.put_nowait({
                "type": "error",
                "message": f"Transcription error: {error}"
            })
        except asyncio.QueueFull:
            logging.warning("Transcription queue is full while reporting an error.")

    client.on(StreamingEvents.Begin, on_begin)
    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Termination, on_terminated)
    client.on(StreamingEvents.Error, on_error)

    async def send_transcriptions():
        while True:
            try:
                message = await transcription_queue.get()
                await websocket.send_text(json.dumps(message))
                transcription_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error sending transcription: {e}")
                break

    sender_task = asyncio.create_task(send_transcriptions())

    try:
        client.connect(
            StreamingParameters(
                sample_rate=16000,
                format_turns=True,
            )
        )
        logging.info("Connected to AssemblyAI with turn detection enabled.")
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Connected to transcription service."
        }))

        while True:
            message = await websocket.receive()
            if "bytes" in message:
                pcm_data = message["bytes"]
                client.stream(pcm_data)
            elif message.get("text") == "EOF":
                logging.info("Client sent EOF. Closing transcription session.")
                break

    except WebSocketDisconnect:
        logging.info("Client disconnected from WebSocket.")
    except Exception as e:
        logging.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        sender_task.cancel()
        try:
            client.disconnect(terminate=True)
        except Exception as e:
            logging.error(f"Error disconnecting from AssemblyAI: {e}")
        if websocket.client_state.name != 'DISCONNECTED':
            try:
                await websocket.close()
            except Exception as e:
                logging.error(f"Error closing WebSocket: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)