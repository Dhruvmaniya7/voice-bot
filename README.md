-----

# DIVA: A Real-Time Conversational Voice AI 🗣️✨

DIVA is a modern, web-based conversational AI that enables a truly seamless, real-time voice interaction with a powerful language model. It's designed as a full-duplex system, allowing you to speak at any time—even while the AI is responding—for a natural, fluid conversation.

This project showcases an advanced architecture using WebSockets to stream data end-to-end: from your microphone to the transcription service, to the language model, to the text-to-speech engine, and finally, back to your speakers.

## ✨ Features

  * **🔴 Full Duplex & Barge-In:** The standout feature. You can interrupt the AI at any point, and it will stop speaking and listen, just like a real conversation.
  * **🎤 Real-Time Voice-to-Text:** Live audio from your microphone is streamed via WebSockets for instant transcription.
  * **🔊 Streaming Text-to-Speech:** Generates high-quality audio from **Murf.ai** and plays it back *as it's being generated*, resulting in a much faster response time.
  * **🧠 Intelligent Responses:** Leverages **Google's Gemini** for coherent, context-aware conversational abilities.
  * **📜 Session Management:** Remembers your conversation history within a session for contextual follow-up questions.
  * **🚀 Robust & Asynchronous Backend:** Built with **FastAPI** and **WebSockets** for high-performance, bidirectional communication.
  * **🌐 Modern Web UI:** A clean, user-friendly interface built with HTML, Tailwind CSS, and Vanilla JavaScript.
  * **🧼 Clear History:** Easily start a new conversation by clearing the session history.

-----

## 🏗️ Architecture & Tech Stack

DIVA uses a streaming-first architecture built around WebSockets. This allows for low-latency, real-time communication between the client and the server, which is essential for features like barge-in.

**The real-time data flow is as follows:**

1.  **WebSocket Connection:** The frontend establishes a persistent WebSocket connection with the FastAPI backend.
2.  **Audio Streaming (Client → Server):** The user speaks, and the browser captures the audio and streams it in chunks to the backend over the WebSocket.
3.  **Real-Time STT (Speech-to-Text):** The backend immediately forwards the incoming audio stream to a real-time transcription service.
4.  **LLM Processing:** The transcribed text is sent to the **Google Gemini API** along with the chat history. The LLM generates a response, which can also be streamed back word-by-word.
5.  **Streaming TTS (Text-to-Speech):** The text response from Gemini is streamed to the **Murf.ai API** to be converted into audio chunks.
6.  **Audio Streaming (Server → Client):** The backend receives the audio chunks from Murf.ai and sends them back to the frontend over the WebSocket *without waiting for the full audio to be generated*.
7.  **Live Playback & Interruption:** The browser plays the audio chunks as they arrive. The frontend is always listening, so if the user speaks, it sends an interrupt signal to the backend to stop the current playback and process the new input.

### Technology Stack

  * **Backend:** Python, FastAPI
  * **Real-Time Communication:** WebSockets
  * **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript
  * **Speech-to-Text (STT):** A real-time transcription service (e.g., AssemblyAI, Deepgram)
  * **Large Language Model (LLM):** [Google Gemini](https://ai.google.dev/)
  * **Text-to-Speech (TTS):** [Murf.ai](https://murf.ai/) (Streaming API)
  * **Server:** Uvicorn

-----

## \#\# Project Structure

The project follows a modular structure to keep the code clean and maintainable.

```
├── main.py               # FastAPI application and WebSocket endpoint
├── services/             # Handles logic for external APIs (STT, LLM, TTS)
├── schemas/              # Pydantic models for data validation
├── static/               # Frontend CSS and JavaScript
├── templates/            # HTML templates
├── .env                  # Environment variables for API keys
├── requirements.txt      # Python dependencies
└── README.md
```

-----

## 🛠️ Setup & Installation

Follow these steps to get DIVA running on your local machine.

### Prerequisites

  * Python 3.8+
  * API Keys from:
      * A real-time transcription service (e.g., AssemblyAI)
      * [Google AI Studio (for Gemini)](https://aistudio.google.com/app/apikey)
      * [Murf.ai](https://murf.ai/)

### 1\. Clone the Repository

```bash
git clone https://github.com/Dhruvmaniya7/voice-bot/
cd voice-bot
```

### 2\. Create and Activate a Virtual Environment

  * **On macOS/Linux:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
  * **On Windows:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

### 3\. Install Dependencies

Create a `requirements.txt` file in the root directory with the following content:

```text
fastapi
uvicorn[standard]
websockets
python-dotenv
requests
# Add your specific STT and LLM SDKs
assemblyai 
google-generativeai
jinja2
python-multipart
```

Then, run the installation command:

```bash
pip install -r requirements.txt
```

### 4\. Set Up Environment Variables

Create a file named `.env` in the root of your project directory and add your API keys.

```env
# .env file

TRANSCRIPTION_API_KEY="your_stt_api_key_here"
GEMINI_API_KEY="your_google_gemini_api_key_here"
MURF_API_KEY="your_murf_api_key_here"
```

-----

## 🚀 Running the Application

1.  Start the FastAPI server using Uvicorn:

    ```bash
    uvicorn main:app --reload
    ```

    The `--reload` flag automatically restarts the server when you make changes to the code.

2.  Open your web browser and navigate to:

    **`http://127.0.0.1:8000`**

You should now see the DIVA interface, ready for a real-time conversation\!
