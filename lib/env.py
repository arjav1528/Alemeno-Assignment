import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require",
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
