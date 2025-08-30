-----

# DIVA: Your Real-Time Conversational AI Mage 🔮✨

Welcome, adventurer\! Meet **DIVA** (Dhruv's Intelligent Voice Assistant), your powerful and friendly mage companion. DIVA listens, responds with warmth, and chats in real-time—all within your browser. She's here to assist you on your quests for knowledge and productivity with a sprinkle of magic\!

This project is built on a cutting-edge, streaming-first architecture, allowing for a truly seamless and natural voice-in, voice-out experience. You can even interrupt DIVA while she’s speaking, and she will gracefully stop to listen.

\<br/\>
\<p align="center"\>
\<em\>(Here is the perfect spot to add a GIF of your awesome UI in action\!)\</em\>
\</p\>
\<p align="center"\>
\<img src="[https://i.imgur.com/your-demo-gif-url.gif](https://www.google.com/search?q=https://i.imgur.com/your-demo-gif-url.gif)" alt="DIVA UI Demo"\>
\</p\>
\<br/\>

## ✨ Features You'll Love

  * **🗣️ Full-Duplex & Barge-In:** Engage in fluid conversation and interrupt the AI at any point. DIVA will immediately stop speaking and start listening.
  * **⚡ Real-Time Streaming:** End-to-end WebSocket communication ensures minimal latency from your microphone to the AI and back to your speakers.
  * **🔮 Powerful Mage Spells (Tool Use):** DIVA can cast spells to help you with real-world tasks:
      * **🔮 Info Spell:** For real-time web searches and news, powered by **Tavily AI**.
      * **🧮 Rune of Calculation:** To solve any mathematical expression.
      * **⏳ Chronos Charm:** To set timers for your adventures.
      * **🌦️ Weather Whisper:** For live weather updates from across the realm.
  * **🧠 Intelligent & Context-Aware:** Leverages **Google's Gemini 1.5 Flash** for coherent, context-aware conversational abilities and intelligent tool selection.
  * **🔊 Streaming Text-to-Speech:** Generates high-quality, natural-sounding audio from **Murf.ai** and plays it back *as it's being generated*, for almost instant responses.
  * **⚙️ Smart & Secure Configuration:** A sleek settings sidebar allows you to use your own API keys, which are stored securely only in your browser's local storage.
  * **📜 Session Management:** Remembers your conversation history for contextual follow-up questions.
  * **🌐 Modern & Responsive UI:** A beautiful, responsive interface built with Tailwind CSS that looks great on both desktop and mobile.

## 🏗️ Architecture Overview

DIVA uses a streaming-first architecture built around WebSockets. This allows for low-latency, real-time communication between the client and the server, which is essential for a natural conversational flow.

```mermaid
flowchart TD
    A[🎤 User Speaks] --> B[FastAPI Backend];
    B --> C[AssemblyAI STT];
    C --> D[Transcript Stream];
    D --> E{Gemini LLM};
    E --> F[Murf TTS];
    F --> G[Frontend: Play Audio + Show Text];
    E -->|Persona/Weather/Web Search/Timer/Calculator| B;
```

**The real-time data flow is as follows:**

1.  **Client Connects:** The browser establishes a WebSocket connection and sends its stored API key configuration to the server.
2.  **Audio Streaming (Client → Server):** The user speaks, and the browser captures the audio, streaming it in chunks to the FastAPI backend.
3.  **Real-Time STT (Server → AssemblyAI):** The backend immediately forwards the audio stream to **AssemblyAI** for live transcription.
4.  **LLM & Tool-Use (Server ↔ Gemini):** The final transcript is sent to the **Google Gemini API**. The LLM analyzes the request, decides if a "spell" (tool) is needed, executes it, and formulates a response.
5.  **Streaming TTS (Server → Murf.ai):** The text response from Gemini is streamed to the **Murf.ai API** to be converted into audio chunks.
6.  **Audio Streaming (Server → Client):** The backend receives audio chunks from Murf.ai and sends them back to the frontend over the WebSocket *without waiting for the full audio to be generated*.
7.  **Live Playback & Interruption:** The browser plays the audio chunks as they arrive. If the user speaks again, the frontend stops playback and begins sending new audio, restarting the loop.

### Tech Stack

| Component                | Technology                                                                                                                                                                                                    |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Backend** | \<img src="[https://img.shields.io/badge/Python-3776AB?style=for-the-badge\&logo=python\&logoColor=white](https://www.google.com/search?q=https://img.shields.io/badge/Python-3776AB%3Fstyle%3Dfor-the-badge%26logo%3Dpython%26logoColor%3Dwhite)" /\> \<img src="[https://img.shields.io/badge/FastAPI-009688?style=for-the-badge\&logo=fastapi\&logoColor=white](https://www.google.com/search?q=https://img.shields.io/badge/FastAPI-009688%3Fstyle%3Dfor-the-badge%26logo%3Dfastapi%26logoColor%3Dwhite)" /\> |
| **Real-Time Communication** | \<img src="[https://img.shields.io/badge/WebSockets-010101?style=for-the-badge](https://www.google.com/search?q=https://img.shields.io/badge/WebSockets-010101%3Fstyle%3Dfor-the-badge)" /\>                                                                                                                               |
| **Frontend** | \<img src="[https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge\&logo=html5\&logoColor=white](https://www.google.com/search?q=https://img.shields.io/badge/HTML5-E34F26%3Fstyle%3Dfor-the-badge%26logo%3Dhtml5%26logoColor%3Dwhite)" /\> \<img src="[https://img.shields.io/badge/Tailwind\_CSS-38B2AC?style=for-the-badge\&logo=tailwind-css\&logoColor=white](https://www.google.com/search?q=https://img.shields.io/badge/Tailwind_CSS-38B2AC%3Fstyle%3Dfor-the-badge%26logo%3Dtailwind-css%26logoColor%3Dwhite)" /\> \<img src="[https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge\&logo=javascript\&logoColor=black](https://www.google.com/search?q=https://img.shields.io/badge/JavaScript-F7DF1E%3Fstyle%3Dfor-the-badge%26logo%3Djavascript%26logoColor%3Dblack)" /\> |
| **Speech-to-Text (STT)** | \<img src="[https://img.shields.io/badge/AssemblyAI-FFB302?style=for-the-badge](https://www.google.com/search?q=https://img.shields.io/badge/AssemblyAI-FFB302%3Fstyle%3Dfor-the-badge)" /\>                                                                                                                                |
| **Large Language Model (LLM)** | \<img src="[https://img.shields.io/badge/Google\_Gemini-8E75B9?style=for-the-badge](https://www.google.com/search?q=https://img.shields.io/badge/Google_Gemini-8E75B9%3Fstyle%3Dfor-the-badge)" /\>                                                                                                                            |
| **Text-to-Speech (TTS)** | \<img src="[https://img.shields.io/badge/Murf.ai-5D5FEF?style=for-the-badge](https://www.google.com/search?q=https://img.shields.io/badge/Murf.ai-5D5FEF%3Fstyle%3Dfor-the-badge)" /\>                                                                                                                                   |
| **Tools & APIs** | \<img src="[https://img.shields.io/badge/Tavily\_AI-000000?style=for-the-badge](https://www.google.com/search?q=https://img.shields.io/badge/Tavily_AI-000000%3Fstyle%3Dfor-the-badge)" /\> \<img src="[https://img.shields.io/badge/WeatherAPI-37A5E6?style=for-the-badge](https://www.google.com/search?q=https://img.shields.io/badge/WeatherAPI-37A5E6%3Fstyle%3Dfor-the-badge)" /\>                                                    |

## 📁 Project Structure

Here’s a look at the project's file structure, keeping everything neat and organized.

\<p align="center"\>
\<img src="[https://i.imgur.com/8d5f75.png](https://www.google.com/search?q=https://i.imgur.com/8d5f75.png)" alt="Project File Structure" width="300"\>
\</p\>

## 🛠️ Setup & Installation

Follow these steps to conjure DIVA on your local machine.

### Prerequisites

  * Python 3.8+
  * API Keys from:
      * [AssemblyAI](https://www.assemblyai.com/dashboard/signup)
      * [Google AI Studio (for Gemini)](https://aistudio.google.com/app/apikey)
      * [Murf.ai](https://murf.ai/)
      * [Tavily AI](https://tavily.com/) (Optional, for web search)
      * [WeatherAPI](https://www.weatherapi.com/) (Optional, for weather)

### 1\. Clone the Repository

```bash
git clone https://github.com/Dhruvmaniya7/voice-bot.git
cd "voice-bot/day 27"
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

Install all required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4\. Set Up Environment Variables

Create a file named `.env` in the `day 27` directory. This file will serve as a **fallback** if keys are not provided in the UI.

```env
# .env file

GEMINI_API_KEY="your_google_gemini_api_key_here"
ASSEMBLYAI_API_KEY="your_assemblyai_api_key_here"
MURF_API_KEY="your_murf_api_key_here"
WEATHER_API_KEY="your_weatherapi_key_here"
TAVILY_API_KEY="your_tavily_api_key_here"
```

## 🚀 Running the Application

1.  Start the FastAPI server using Uvicorn:

    ```bash
    uvicorn main:app --reload
    ```

    The `--reload` flag automatically restarts the server when you make changes to the code.

2.  Open your web browser and navigate to:

    **`http://127.0.0.1:8000`**

You should now see the DIVA interface, ready for a real-time conversation\!

### Deployment Note

If you deploy this application on a free-tier service (like Render, Heroku, etc.), please be aware that the app may "sleep" after a period of inactivity. The first request after it has slept might be slow as the server "wakes up." This is normal for free-tier deployments.
