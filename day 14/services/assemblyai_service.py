# /services/assemblyai_service.py

import os
import assemblyai as aai
from fastapi import UploadFile
import logging

# Configure the AssemblyAI API key
# This reads the key from your .env file
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY
else:
    logging.warning("ASSEMBLYAI_API_KEY not found. Transcription will fail.")

def transcribe_audio(audio_file: UploadFile) -> str:
    """Transcribes the given audio file using the AssemblyAI API."""
    if not aai.settings.api_key:
        raise Exception("Speech-to-text service is not configured.")

    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_file.file)

        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")

        return transcript.text or ""
    except Exception as e:
        logging.error(f"An error occurred during transcription: {e}")
        raise