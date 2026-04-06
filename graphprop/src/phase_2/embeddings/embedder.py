import os
from dotenv import load_dotenv
import google.generativeai as genai

# CARGAR .env
load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def get_embedding(text: str):
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text
        )

        return result["embedding"]

    except Exception as e:
        print(f"❌ Error embedding: {e}")
        return None