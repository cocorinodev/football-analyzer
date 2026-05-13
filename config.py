import os
from dotenv import load_dotenv

load_dotenv()

SPORTMONKS_API_TOKEN = os.getenv("SPORTMONKS_API_TOKEN")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Bucharest")

BASE_URL = "https://api.sportmonks.com/v3/football"

if not SPORTMONKS_API_TOKEN:
    raise RuntimeError(
        "Missing SPORTMONKS_API_TOKEN. Add it to your .env file."
    )