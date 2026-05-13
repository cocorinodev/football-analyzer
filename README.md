# Predict

Predict is a small, focused Python utility that fetches football data from SportMonks, runs a compact prediction routine, and prints concise, human-friendly results. It is intended as a simple local tool you can run and adapt.

## Features
- Fetches match and team data from SportMonks.
- Runs a lightweight prediction pipeline (`predictor.py`).
- Formats results for terminal output and simple exports (`formatter.py`).

## Requirements
- Python 3.8 or newer
- See `requirements.txt` for dependencies (`requests`, `python-dotenv`, `schedule`, `colorama`).

## Installation
1. Clone the repository and change into the project folder:

```bash
Add a .env file in the same folder 
Add this to .env
SPORTMONKS_API_TOKEN= your token
TIMEZONE=Europe/Bucharest

Create an account at sportmonks.com(14 days free trial) and add the api to ".env"
```

```pip install -r requirements.txt```

```bash
git clone <repository-url>
cd predict
```

## Usage
Run the main program:

python3 main.py

Check `main.py` for any available options or entry points.

## Project structure
- `main.py` — Program entry point and orchestration.
- `config.py` — Configuration and environment helpers.
- `football_api.py` — SportMonks API wrapper and data helpers.
- `predictor.py` — Prediction logic and rules.
- `formatter.py` — Output formatting utilities.
- `requirements.txt` — Runtime dependencies.
- `.env` — Local environment variables (kept out of source control).

## Notes
- Respect SportMonks API rate limits and terms when running frequent requests.
- This repository does not include a license file. Add one if you intend to open-source the project.

## Contributing
Open an issue to discuss changes or submit a pull request with improvements.
