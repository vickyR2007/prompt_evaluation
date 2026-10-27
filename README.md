# Prompt Evaluation Studio

1. Copy `.env` and replace the placeholder with your Groq API key.
2. From this directory run:

   ```bash
   python -m pip install -r requirements.txt
   streamlit run app.py
   ```

The app supports five domains and three difficulty levels. Each submission receives six 0–10 component scores, normalized to an overall score out of 100, written feedback, an optimized prompt, and session-based progress tracking.
