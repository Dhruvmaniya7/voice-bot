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
from typing import List, Dict
import base64
import websockets
from datetime import datetime
import re
import ast
import requests

from tavily import TavilyClient
import google.generativeai as genai
import assemblyai as aai
from assemblyai.streaming.v3 import StreamingClient, StreamingClientOptions, StreamingParameters, TurnEvent, StreamingEvents

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = FastAPI()

# --- File Paths and Static/Template Configuration ---
BASE_DIR = PathLib(__file__).resolve().parent
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- CORE LOGIC: GEMINI + TTS STREAMING ---
async def get_llm_response_stream(transcript: str, client_websocket: WebSocket, chat_history: List[dict], active_config: Dict):
    # --- TOOL DEFINITIONS (Session Scoped) ---
    def tavily_search(query: str) -> str:
        api_key = active_config.get("tavily")
        if not api_key: return "Tavily API key is not configured for this session."
        try:
            logging.info(f"TOOL: tavily_search, QUERY: {query}")
            client = TavilyClient(api_key=api_key)
            response = client.search(query=query, search_depth="basic")
            return "\n".join([f"- {res['content']}" for res in response.get('results', [])]) or "No results found."
        # --- FINAL FIX: CATCH SPECIFIC API KEY ERRORS ---
        except Exception as e:
            if "Invalid API key" in str(e):
                logging.error(f"Tavily API Key is invalid: {e}")
                return "My Info Spell has failed, adventurer. The Tavily API key provided is invalid or has expired. Please check it in the settings."
            else:
                return f"An error occurred during search: {str(e)}"

    def calculate(expression: str) -> str:
        try:
            logging.info(f"TOOL: calculate, EXPRESSION: {expression}")
            result = eval(compile(ast.parse(expression.replace('x', '*'), mode='eval'), '<string>', 'eval'))
            return str(result)
        except Exception as e:
            return f"Could not calculate the expression. Error: {e}"

    def set_timer(duration: int, units: str) -> str:
        logging.info(f"TOOL: set_timer, DURATION: {duration} {units}")
        return f"Timer successfully set for {duration} {units}."

    def get_weather(location: str) -> str:
        api_key = active_config.get("weather")
        if not api_key: return "Weather API key is not configured for this session."
        try:
            url = "http://api.weatherapi.com/v1/current.json"
            params = {"key": api_key, "q": location}
            response = requests.get(url, params=params)
            response.raise_for_status() 
            data = response.json()
            loc, curr = data["location"], data["current"]
            return (f"Weather for {loc['name']}, {loc['region']}, {loc['country']}: "
                    f"{curr['condition']['text']}, {curr['temp_c']}°C, humidity {curr['humidity']}%, wind {curr['wind_kph']} kph.")
        except Exception as e:
            return f"Error retrieving weather information: {e}"

    try:
        genai.configure(api_key=active_config.get("gemini"))
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        gemini_model.count_tokens("test") 
    except Exception as e:
        logging.error(f"Failed to configure or use Gemini: {e}")
        await client_websocket.send_text(json.dumps({"type": "error", "message": "Invalid or expired Gemini API Key. Please check your settings."}))
        return

    logging.info(f"USER TRANSCRIPT: '{transcript}'")
    
    murf_api_key = active_config.get("murf")
    murf_uri = f"wss://api.murf.ai/v1/speech/stream-input?api-key={murf_api_key}&sample_rate=44100&channel_type=MONO&format=MP3"

    try:
        async with websockets.connect(murf_uri) as websocket:
            voice_id = "en-US-natalie"
            logging.info(f"Connected to Murf AI using voice: {voice_id}")
            context_id = f"voice-agent-context-{datetime.now().isoformat()}"
            await websocket.send(json.dumps({"voice_config": {"voiceId": voice_id, "style": "Conversational"}, "context_id": context_id}))

            async def receive_and_forward_audio():
                try:
                    while True:
                        response_str = await websocket.recv()
                        response = json.loads(response_str)
                        if "audio" in response and response['audio']:
                            await client_websocket.send_text(json.dumps({"type": "audio", "data": response['audio']}))
                        if response.get("final"):
                            await client_websocket.send_text(json.dumps({"type": "audio_end"}))
                            break
                except websockets.ConnectionClosed:
                    logging.warning("Murf connection closed.")
                    await client_websocket.send_text(json.dumps({"type": "audio_end"}))

            receiver_task = asyncio.create_task(receive_and_forward_audio())
            try:
                available_tools = [calculate, set_timer]
                if active_config.get("tavily"): available_tools.append(tavily_search)
                if active_config.get("weather"): available_tools.append(get_weather)
                
                prompt = f"""You are Diva, a powerful and helpful mage companion.
Your Persona: You were created by the Archmage Dhruv Maniya. You are wise, slightly formal, and always address the user as "youngmaster" or "adventurer". Your purpose is to assist the user on their quests.

Your Tools (Spells):
- tavily_search: Cast 'Info Spell' for real-time information.
- calculate: Use the 'Rune of Calculation' for math.
- set_timer: Invoke the 'Chronos Charm' to set timers.
- get_weather: Whisper to the winds with 'Storm Whisper' for weather data.

**Core Instructions:**
1.  **Analyze Intent:** Understand the user's request from their latest quest: "{transcript}"
2.  **Select & Execute Tool:** If the request matches one of your spells, you MUST call the corresponding tool. Do not ask for permission. Do not explain what you are about to do. Just call the tool.
3.  **Formulate Response from Tool Output:** After you receive the result from the tool, formulate a helpful, in-character response that directly answers the user's question using the data you received. For example, if the tool returns "Weather for London: Sunny, 22°C", you should say something like "The winds whisper to me, adventurer. In London, it is currently Sunny and 22 degrees Celsius."
4.  **Handle Missing Tools:** If a user asks for something you don't have a spell for (e.g., sending an email), politely inform them that you lack that specific magic.
5.  **Handle Transcription Errors:** If the user's quest seems to have a minor transcription error (e.g., 'plus' instead of 'place'), correct it to the most logical term before using a tool.
"""
                chat_history.append({"role": "user", "parts": [prompt]})
                chat = gemini_model.start_chat(history=chat_history[:-1])
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(None, lambda: chat.send_message(prompt, tools=available_tools, tool_config={"function_calling_config": {"mode": "AUTO"}}))
                function_call = next((part.function_call for part in response.candidates[0].content.parts if part.function_call), None)

                if function_call:
                    function_name, function_args = function_call.name, {k: v for k, v in function_call.args.items()}
                    await client_websocket.send_text(json.dumps({"type": "status", "message": f"Diva is casting {function_name}..."}))
                    tool_map = {"tavily_search": tavily_search, "calculate": calculate, "set_timer": set_timer, "get_weather": get_weather}
                    if function_name in tool_map:
                        function_result = await loop.run_in_executor(None, lambda: tool_map[function_name](**function_args))
                        if function_name == "set_timer":
                            duration = function_args.get('duration', 0)
                            units = function_args.get('units', 'seconds')
                            await client_websocket.send_text(json.dumps({"type": "start_timer", "duration_seconds": duration * 60 if 'minute' in units.lower() else duration}))
                    else:
                        function_result = "Unknown spell."
                    chat_history.append(response.candidates[0].content)
                    function_response_content = {"role": "user", "parts": [{"function_response": {"name": function_name, "response": {"result": function_result}}}]}
                    chat_history.append(function_response_content)
                    final_response_stream = await loop.run_in_executor(None, lambda: chat.send_message(function_response_content, stream=True))
                else:
                    final_response_stream = response
                
                sentence_buffer, full_response_text = "", ""
                await client_websocket.send_text(json.dumps({"type": "audio_start"}))
                for chunk in final_response_stream:
                    if hasattr(chunk, 'text') and chunk.text:
                        full_response_text += chunk.text
                        await client_websocket.send_text(json.dumps({"type": "llm_chunk", "data": chunk.text}))
                        sentence_buffer += chunk.text
                        sentences = re.split(r'(?<=[.?!])\s+', sentence_buffer)
                        if len(sentences) > 1:
                            for sentence in sentences[:-1]:
                                if sentence.strip():
                                    await websocket.send(json.dumps({"text": sentence.strip(), "end": False, "context_id": context_id}))
                            sentence_buffer = sentences[-1]
                if sentence_buffer.strip():
                    await websocket.send(json.dumps({"text": sentence_buffer.strip(), "end": True, "context_id": context_id}))
                
                logging.info(f"DIVA'S RESPONSE: {full_response_text}")
                chat_history.append({"role": "model", "parts": [full_response_text]})
                await asyncio.wait_for(receiver_task, timeout=60.0)
            except asyncio.TimeoutError:
                logging.warning("Murf audio receiver timed out gracefully.")
            finally:
                if not receiver_task.done(): receiver_task.cancel()
    except websockets.exceptions.InvalidStatusCode:
        logging.error("Failed to connect to Murf AI, likely due to an invalid API key.")
        await send_client_message(client_websocket, {"type": "error", "message": "Invalid or expired Murf.ai API Key. Please check your settings."})
    except Exception as e:
        logging.error(f"Error in main streaming function: {e}", exc_info=True)
        await send_client_message(client_websocket, {"type": "error", "message": "An unexpected error occurred."})

# --- FastAPI Endpoints ---
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

async def send_client_message(ws: WebSocket, message: dict):
    try:
        if ws.client_state.name == 'CONNECTED':
            await ws.send_text(json.dumps(message))
    except (ConnectionError, WebSocketDisconnect, RuntimeError):
        logging.warning("Could not send message to a closed or closing client.")

@app.websocket("/ws")
async def websocket_audio_streaming(websocket: WebSocket):
    await websocket.accept()
    main_loop = asyncio.get_running_loop()
    
    final_config = {}
    client = None
    llm_task = None
    
    try:
        config_message_str = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        config_message = json.loads(config_message_str)
        if config_message.get("type") == "config":
            user_keys = config_message.get("keys", {})
            final_config = {
                "gemini": user_keys.get("gemini") or config.GEMINI_API_KEY,
                "assemblyai": user_keys.get("assemblyai") or config.ASSEMBLYAI_API_KEY,
                "murf": user_keys.get("murf") or config.MURF_API_KEY,
                "weather": user_keys.get("weather") or config.WEATHER_API_KEY,
                "tavily": user_keys.get("tavily") or config.TAVILY_API_KEY
            }
            essential_keys = ["gemini", "assemblyai", "murf"]
            missing_keys = [key for key in essential_keys if not final_config.get(key)]
            if missing_keys:
                error_msg = f"Essential API key(s) missing: {', '.join(missing_keys)}. Please set them in the settings."
                await send_client_message(websocket, {"type": "error", "message": error_msg})
                raise ValueError(error_msg)
            
            logging.info("Essential keys are present. Final merged configuration created.")
        else:
            raise ValueError("First message was not a configuration message.")

        aai_key = final_config.get("assemblyai")
        client = StreamingClient(StreamingClientOptions(api_key=aai_key))
        chat_history = []
        last_processed_transcript = ""

        def on_turn(self, event: TurnEvent):
            nonlocal last_processed_transcript, llm_task
            transcript_text = event.transcript.strip()
            if event.end_of_turn and event.turn_is_formatted and transcript_text and transcript_text != last_processed_transcript:
                last_processed_transcript = transcript_text
                logging.info(f"Final formatted turn: '{transcript_text}'")
                transcript_message = {"type": "transcription", "text": transcript_text, "end_of_turn": True}
                asyncio.run_coroutine_threadsafe(send_client_message(websocket, transcript_message), main_loop)
                if llm_task and not llm_task.done(): llm_task.cancel()
                llm_task = asyncio.run_coroutine_threadsafe(get_llm_response_stream(transcript_text, websocket, chat_history, final_config), main_loop)
        
        client.on(StreamingEvents.Turn, on_turn)
        client.connect(StreamingParameters(sample_rate=16000, format_turns=True))
        await send_client_message(websocket, {"type": "status", "message": "Connected! Ready for adventure!"})
        
        while True:
            message = await websocket.receive()
            if "bytes" in message and message['bytes']:
                client.stream(message['bytes'])
            elif "text" in message and json.loads(message['text']).get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except (WebSocketDisconnect, RuntimeError):
        logging.info("Client disconnected gracefully.")
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        logging.error(error_msg, exc_info=True)
        await send_client_message(websocket, {"type": "error", "message": "An unexpected server error occurred. Please check the logs."})
    
    finally:
        if llm_task and not llm_task.done():
            llm_task.cancel()
        if client:
            client.disconnect()
        logging.info("Cleaned up connection resources.")
        if websocket.client_state.name != 'DISCONNECTED':
            await websocket.close()