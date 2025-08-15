# Dhwani Bot - A Conversational AI Voice Agent

Dhwani Bot is a voice-based conversational AI agent built as part of the **#30DaysOfAIVoiceAgents** challenge. You can speak to it, and it will respond in a natural-sounding voice. The project is built with Python, FastAPI, and utilizes several cutting-edge AI services for its core functionalities.



## Features

* **Voice-to-Text Transcription**: Captures user voice input and accurately transcribes it into text using AssemblyAI.
* **Intelligent Conversation**: Leverages Google's Gemini 1.5 Flash model to understand context and generate human-like responses.
* **Text-to-Speech Synthesis**: Converts the AI's text response back into high-quality, natural-sounding audio using Murf AI.
* **Web-Based Interface**: A clean and simple UI built with FastAPI, HTML, and Tailwind CSS.
* **Selectable Voices**: Users can choose from a variety of AI voices for the bot's responses.
* **Session Management**: Maintains conversation history within a session.

## Tech Stack

* **Backend**: FastAPI, Python
* **Speech-to-Text (STT)**: AssemblyAI
* **Language Model (LLM)**: Google Gemini 1.5 Flash
* **Text-to-Speech (TTS)**: Murf AI
* **Frontend**: HTML, Tailwind CSS, Vanilla JavaScript
* **Deployment**: (Not yet deployed)

## Project Structure

The project follows a modular, service-oriented architecture to keep the code clean and maintainable.

├── main.py                 # FastAPI application entrypoint
├── services/               # Handles logic for external APIs (STT, LLM, TTS)
├── schemas/                # Pydantic models for data validation
├── static/                 # Frontend CSS and JavaScript
├── templates/              # HTML templates
├── .env                    # Environment variables for API keys
├── requirements.txt        # Python dependencies
└── README.md


## How to Run Locally

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/dhwani-bot-ai-agent.git](https://github.com/your-username/dhwani-bot-ai-agent.git)
    cd dhwani-bot-ai-agent
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **Set up your API Keys:**
    * Create a file named `.env` in the project root.
    * Add your API keys to this file:
        ```env
        ASSEMBLYAI_API_KEY="your_assemblyai_key"
        GEMINI_API_KEY="your_gemini_key"
        MURF_API_KEY="your_murf_ai_key"
        ```

4.  **Run the application:**
    ```bash
    uvicorn main:app --reload
    ```
    Open your browser and navigate to `http://127.0.0.1:8000`.

## Project Progress Log

**Day 14: Code Refactoring & GitHub Launch**
* Successfully refactored the entire application from a single script into a scalable, service-oriented architecture.
* Separated concerns by moving external API logic into a `services` directory.
* Implemented Pydantic schemas for robust request/response validation.
* Cleaned up the codebase, added logging, and standardized API key handling.
* The project is now public on GitHub!

*(...previous day logs...)*
