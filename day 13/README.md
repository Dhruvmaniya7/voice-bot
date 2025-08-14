
# Dhwani Bot: A Conversational Voice AI 🗣️✨

Dhwani Voice is a modern, web-based conversational AI that allows you to interact with a powerful language model using only your voice. Ask a question, and get a spoken response back in a voice of your choice. It's designed to be a seamless voice-in, voice-out experience.

This project integrates state-of-the-art APIs for Speech-to-Text, Large Language Models, and Text-to-Speech into a sleek, responsive interface powered by a FastAPI backend.

## ✨ Features

  * **🎤 Voice-to-Text:** Real-time audio transcription powered by **AssemblyAI**.
  * **🧠 Intelligent Responses:** Leverages **Google's Gemini 1.5 Flash** for coherent, context-aware conversational abilities.
  * **🔊 Text-to-Speech:** Generates high-quality, natural-sounding audio responses using **Murf.ai**.
  * **🗣️ Dynamic Voice Selection:** Choose from a variety of voices for the AI's responses.
  * **📜 Session Management:** Remembers your conversation history within a session for contextual follow-up questions.
  * **🌐 Modern Web UI:** A clean, user-friendly interface built with HTML, Tailwind CSS, and Vanilla JavaScript.
  * **🚀 Robust Backend:** Built with **FastAPI** for high performance and asynchronous request handling.
  * **🧼 Clear History:** Easily start a new conversation by clearing the session history.

-----

## 🏗️ Architecture & Tech Stack

Dhwani Voice follows a microservice-oriented architecture where the frontend client communicates with a central FastAPI backend, which in turn orchestrates calls to various external AI services.

**The data flow is as follows:**

1.  **Audio Capture (Frontend):** The user records their voice query in the browser.
2.  **STT (Speech-to-Text):** The audio is sent to the FastAPI backend, which forwards it to **AssemblyAI** for transcription.
3.  **LLM (Language Model):** The transcribed text is sent to the **Google Gemini API**, along with the session's chat history, to generate a relevant response.
4.  **TTS (Text-to-Speech):** The text response from Gemini is sent to the **Murf.ai API** to be converted into an audio file (MP3).
5.  **Response to Client:** The backend returns the URL of the generated audio and the updated chat history to the frontend.
6.  **Playback & Display (Frontend):** The browser plays the audio response and dynamically updates the chat history on the screen.

### Technology Stack

  * **Backend:** Python, FastAPI
  * **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript
  * **Speech-to-Text (STT):** [AssemblyAI](https://www.assemblyai.com/)
  * **Large Language Model (LLM):** [Google Gemini](https://ai.google.dev/)
  * **Text-to-Speech (TTS):** [Murf.ai](https://murf.ai/)
  * **Server:** Uvicorn

-----

## 🛠️ Setup & Installation

Follow these steps to get Dhwani Voice running on your local machine.

### Prerequisites

  * Python 3.8+
  * API Keys from:
      * [AssemblyAI](https://www.assemblyai.com/dashboard/signup)
      * [Google AI Studio (for Gemini)](https://aistudio.google.com/app/apikey)
      * [Murf.ai](https://www.google.com/search?q=https://murf.ai/user/register)

### 1\. Clone the Repository

```bash
https://github.com/Dhruvmaniya7/voice-bot/
cd "day 13"
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
python-dotenv
requests
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

ASSEMBLYAI_API_KEY="your_assemblyai_api_key_here"
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

You should now see the Dhwani Voice interface, ready for you to interact with\!

-----

## 🔗 API Endpoints

The FastAPI backend exposes the following endpoints:

| Method   | Path                       | Description                                                     |
| :------- | :------------------------- | :-------------------------------------------------------------- |
| `GET`    | `/`                        | Serves the main `index.html` page.                              |
| `GET`    | `/voices`                  | Fetches the list of available TTS voices from the Murf.ai API.  |
| `POST`   | `/agent/chat/{session_id}` | The main endpoint for handling a conversational turn.           |
| `GET`    | `/agent/chat/{session_id}` | Retrieves the chat history for a given session.                 |
| `DELETE` | `/agent/chat/{session_id}` | Clears the chat history for a given session.                    |

-----
It's a complete voice-in, voice-out experience, powered by a Python backend and a sleek, modern frontend. The goal was to explore the end-to-end architecture of a modern voice assistant.

**Tech Stack & Architecture:**
🔹 **Backend:** FastAPI
🔹 **Frontend:** Vanilla JS & Tailwind CSS
🔹 **Speech-to-Text:** AssemblyAI
🔹 **LLM:** Google's Gemini 1.5 Flash
🔹 **Text-to-Speech:** Murf.ai



