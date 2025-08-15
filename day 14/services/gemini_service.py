# /services/gemini_service.py

import os
import google.generativeai as genai
import logging
from typing import List, Dict

# Configure the Gemini API key
# This reads the key from your .env file
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logging.warning("GEMINI_API_KEY not found. LLM will fail.")

def get_chat_response(session_history: List[Dict], user_query: str) -> (str, List[Dict]):
    """Gets a response from the Gemini LLM."""
    
    # THE INCORRECT CHECK HAS BEEN REMOVED FROM HERE

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        chat = model.start_chat(history=session_history)
        response = chat.send_message(user_query)
        
        return response.text, chat.history
    except Exception as e:
        # This block will now correctly handle errors, including missing API keys.
        logging.error(f"An error occurred with the Gemini API: {e}")
        raise