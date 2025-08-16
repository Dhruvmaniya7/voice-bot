# /services/murf_service.py

import requests
import os
import logging

# This reads the key from your .env file
MURF_API_KEY = os.getenv("MURF_API_KEY")

def get_available_voices() -> list:
    """Fetches the list of available voices from Murf API."""
    if not MURF_API_KEY:
        raise Exception("Voice service API key is not configured.")
    
    url = "https://api.murf.ai/v1/speech/voices"
    headers = {"Accept": "application/json", "api-key": MURF_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to connect to the voice service: {e}")


def generate_murf_audio(text_to_speak: str, voice_id: str) -> str:
    """Generates audio using Murf API and returns the audio URL."""
    if not MURF_API_KEY:
        raise Exception("Text-to-speech service is not configured.")
    
    url = "https://api.murf.ai/v1/speech/generate"
    headers = {"Accept": "application/json", "Content-Type": "application/json", "api-key": MURF_API_KEY}
    payload = {"text": text_to_speak, "voiceId": voice_id, "format": "MP3", "sampleRate": 24000}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        audio_url = data.get("audioFile")
        
        if not audio_url:
            raise Exception("TTS service did not return an audio file.")
            
        return audio_url
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to connect to the text-to-speech service: {e}")