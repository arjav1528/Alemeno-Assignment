import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require",
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
