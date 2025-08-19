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

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = FastAPI()

# --- Directories and Templates ---
BASE_DIR = PathLib(__file__).resolve().parent
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- FastAPI Routes ---
@app.get("/")
async def home(request: Request):
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_audio_streaming(websocket: WebSocket):
    """Handles the WebSocket connection for real-time audio streaming and transcription."""
    await websocket.accept()
    
    # --- API Key Check ---
    if not config.ASSEMBLYAI_API_KEY:
        logging.error("ASSEMBLYAI_API_KEY not configured")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "AssemblyAI API key not configured on the server."
        }))
        await websocket.close(code=1000)
        return

    transcription_queue = asyncio.Queue()

    # --- AssemblyAI Streaming Client Setup ---
    client = StreamingClient(
        StreamingClientOptions(api_key=config.ASSEMBLYAI_API_KEY)
    )

    # --- Event Handlers for AssemblyAI Client ---
    def on_begin(self: Type[StreamingClient], event: BeginEvent):
        logging.info(f"Transcription session started: {event.id}")

    # --- MODIFIED SECTION TO SHOW ONLY FINAL, FORMATTED TRANSCRIPT ---
    def on_turn(self: Type[StreamingClient], event: TurnEvent):
        """Handles turn detection events."""
        transcript_text = event.transcript
        
        # Only send the message if the turn has ended AND it has been formatted.
        if event.end_of_turn and event.turn_is_formatted:
            logging.info(f"Final formatted turn: '{transcript_text}'")
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

    # Register event handlers
    client.on(StreamingEvents.Begin, on_begin)
    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Termination, on_terminated)
    client.on(StreamingEvents.Error, on_error)

    # --- Background task to send messages from queue to client ---
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
        # Connect to AssemblyAI
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

        # --- Main loop to receive audio data ---
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
        # --- Cleanup ---
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