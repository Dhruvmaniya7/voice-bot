import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

if not ASSEMBLYAI_API_KEY:
    logging.warning("ASSEMBLYAI_API_KEY not found in .env file. Please create one.")