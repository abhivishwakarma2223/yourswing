# Swing Backend

Backend API for the swing trading application. Built using Python, FastAPI, and PostgreSQL.

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create your `.env` file or use the provided default for local development.

4. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```
