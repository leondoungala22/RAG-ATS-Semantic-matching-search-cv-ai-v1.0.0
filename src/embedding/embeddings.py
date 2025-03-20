import os
import sys
import json
import logging
from dotenv import load_dotenv
from langchain_community.document_loaders import JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

# ========================== #
#  ✅ PROJECT ROOT SETUP    #
# ========================== #

# Get the absolute path of the project's root directory (relative to this file)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the project root to the Python path
if project_root not in sys.path:
    sys.path.append(project_root)

# ========================== #
#  ✅ LOAD ENV VARIABLES    #
# ========================== #

load_dotenv()

# ========================== #
#  ✅ LOGGING CONFIGURATION  #
# ========================== #

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ========================== #
#  ✅ PATH CONFIGURATION     #
# ========================== #

CV_JSON_FOLDER = "src/data/cv_json"   # Path where CV JSON files are stored
CHROMA_DB_PATH = "src/data/chromadb"  # Path where ChromaDB stores embeddings

# Ensure directories exist
os.makedirs(CV_JSON_FOLDER, exist_ok=True)
os.makedirs(CHROMA_DB_PATH, exist_ok=True)

# ========================== #
#  ✅ OPENAI API CONFIG      #
# ========================== #

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDINGS_MODEL = os.getenv("OPENAI_EMBEDDINGS_MODEL_DEPLOYMENT", "text-embedding-ada-002")

# ========================== #
#  ✅ FUNCTION DEFINITIONS   #
# ========================== #

def extract_text_from_json(json_data):
    """
    Extracts key fields from JSON and converts them into a single text string.
    """
    extracted_text = ""

    if isinstance(json_data, dict):
        for key, value in json_data.items():
            if isinstance(value, str):
                extracted_text += f"{key.title()}:\n{value}\n\n"
            elif isinstance(value, list):
                extracted_text += f"{key.title()}:\n" + "\n".join([f"- {v}" for v in value if isinstance(v, str)]) + "\n\n"

    return extracted_text.strip()


def load_json_documents():
    """
    Reads JSON files from `src/data/cv_json/`, extracts relevant fields,
    and formats them into plain text.
    """
    logger.info(f"📂 Scanning JSON files in: {CV_JSON_FOLDER}")

    json_files = [os.path.join(CV_JSON_FOLDER, f) for f in os.listdir(CV_JSON_FOLDER) if f.endswith(".json")]

    if not json_files:
        logger.error("❌ No JSON files found. Exiting.")
        return []

    all_documents = []

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            text_content = extract_text_from_json(json_data)

            if not text_content:
                logger.warning(f"⚠️ No valid text extracted from {json_file}. Skipping.")
                continue

            # Create a LangChain Document object
            document = Document(page_content=text_content, metadata={"source": json_file})
            all_documents.append(document)

            logger.info(f"✅ Loaded and processed {json_file}")

        except Exception as e:
            logger.error(f"❌ Failed to process {json_file}: {e}")

    logger.info(f"📜 Total documents loaded: {len(all_documents)}")
    return all_documents


def split_documents(documents):
    """
    Splits long documents into smaller chunks for better vector search.
    """
    logger.info("🔹 Splitting documents into smaller chunks...")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,  # Max tokens per chunk
        chunk_overlap=100,  # Overlap between chunks to maintain context
        separators=["\n\n", "\n", " "]
    )

    try:
        split_docs = text_splitter.split_documents(documents)
        logger.info(f"✅ Split into {len(split_docs)} chunks.")
        return split_docs
    except Exception as e:
        logger.error(f"❌ Error splitting documents: {e}")
        return []


def embed_and_store_documents(split_docs):
    """
    Generates embeddings and stores them in ChromaDB.
    """
    logger.info("🧠 Generating embeddings and storing in ChromaDB...")

    try:
        embeddings = OpenAIEmbeddings(
            model=EMBEDDINGS_MODEL,
            openai_api_key=OPENAI_API_KEY
        )

        # Store in ChromaDB
        vector_store = Chroma.from_documents(
            documents=split_docs,
            embedding=embeddings,
            persist_directory=CHROMA_DB_PATH
        )

        logger.info(f"✅ Successfully stored {len(split_docs)} vector embeddings in ChromaDB.")
    except Exception as e:
        logger.error(f"❌ Error storing embeddings in ChromaDB: {e}")


def main():
    """
    Pipeline to load, split, embed, and store embeddings.
    """
    logger.info("🚀 Starting embedding process...")

    # Step 1: Load JSON documents
    documents = load_json_documents()
    if not documents:
        logger.error("❌ No valid JSON documents found. Exiting.")
        return

    # Step 2: Split documents
    split_docs = split_documents(documents)

    # Step 3: Embed and store in ChromaDB
    embed_and_store_documents(split_docs)

    logger.info("🎯 Embedding process completed successfully!")


if __name__ == "__main__":
    main()
