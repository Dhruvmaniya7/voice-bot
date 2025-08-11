
### 🎙️ 30 Days of Voice Agents Challenge

This repository chronicles my journey through the **30 Days of Voice Agents Challenge**, an initiative by **Murf AI**. The mission is to dive deep into voice technology by building 30 distinct voice-powered applications, one for each day of the challenge.

-----

### The Goal 🎯

The challenge is focused on hands-on learning. Each day, a new mini-project is developed to explore a specific aspect of voice AI, from backend API integration with FastAPI to frontend audio handling with JavaScript.

-----

### How This Repository is Organized 📂

To keep things clean and modular, every daily project resides in its own dedicated folder. The structure for each day is consistent:

```
day-##/
├── main.py          # Backend server logic (FastAPI)
├── templates/       # Jinja2 HTML pages for the UI
├── static/          # CSS and JavaScript assets
├── requirements.txt # Python package requirements
└── README.md        # A guide for the specific day's project
```

-----

### Core Technologies Used 🛠️

A modern stack was chosen to power these voice agents:

  * **Backend Stack**

      * Python
      * FastAPI & Uvicorn
      * `requests` for HTTP calls
      * `python-dotenv` for environment variable management

  * **Frontend Stack**

      * HTML, CSS, and Bootstrap
      * Vanilla JavaScript, featuring the `MediaRecorder` API for audio capture

  * **AI & Voice APIs**

      * **Murf AI:** Used for generating high-quality Text-to-Speech (TTS).
      * **AssemblyAI:** Used for reliable Speech-to-Text (STT) transcription.

-----

### Getting a Project Running 🚀

You can run any daily project on your local machine with just a few commands.

1.  **Select a project directory:**

    ```bash
    cd day-##/
    ```

2.  **Install the necessary dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Launch the development server:**

    ```bash
    uvicorn main:app --reload
    ```

4.  **See it live** by visiting `http://127.0.0.1:8000` in your web browser.
