import os
from dotenv import load_dotenv

load_dotenv()

# Path to Chroma database and job description file
CHROMA_DB_PATH = os.path.join("src", "data", "chromadb")
JOB_DESCRIPTION_PATH = os.path.join("src", "data", "job description", "Job_Description_Italian.txt") # used to test 

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_MAIN")
EMBEDDINGS_MODEL = os.getenv("OPENAI_EMBEDDINGS_MODEL_DEPLOYMENT", "text-embedding-ada-002")
