import os
import sys
import json
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.retrievers import MultiQueryRetriever, ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

# Project root setup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import get_logger

# ========================== #
#  ✅ ENV & CONFIG          #
# ========================== #

load_dotenv()
logger = get_logger("Retriever")

CHROMA_DB_PATH = "src/data/chromadb"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_MAIN")
EMBEDDINGS_MODEL = os.getenv("OPENAI_EMBEDDINGS_MODEL_DEPLOYMENT", "text-embedding-ada-002")

# ========================== #
#  ✅ Load Vector Store     #
# ========================== #

logger.info("🔐 Loading Chroma vector store...")
embeddings = OpenAIEmbeddings(model=EMBEDDINGS_MODEL, openai_api_key=OPENAI_API_KEY)

vector_store = Chroma(
    persist_directory=CHROMA_DB_PATH,
    embedding_function=embeddings
)

logger.info("✅ Vector store loaded successfully!")

# ========================== #
#  ✅ Retriever Class       #
# ========================== #

class Retriever:
    def __init__(self):
        self.logger = get_logger("Retriever")
        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-4o-mini",  # or gpt-3.5-turbo
            openai_api_key=OPENAI_API_KEY
        )

        base_retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 20})

        self.multi_query_retriever = MultiQueryRetriever.from_llm(
            retriever=base_retriever,
            llm=self.llm
        )

        compressor = LLMChainExtractor.from_llm(self.llm)

        self.compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=self.multi_query_retriever
        )

    def search(self, query: str):
        try:
            self.logger.info("🔍 Performing retrieval with OpenAI-powered compression...")
            documents = self.compression_retriever.invoke(query)

            results = []
            for i, doc in enumerate(documents):
                doc_id = doc.metadata.get("source", f"doc_{i}")
                preview = doc.page_content[:200].replace("\n", " ")
                self.logger.info(f"\n📄 ID: {doc_id}\n📃 Preview: {preview}\n")
                results.append({"id": doc_id, "doc": doc})

            self.logger.info(f"✅ Retrieved {len(results)} documents.")
            return results

        except Exception as e:
            self.logger.error(f"❌ Retrieval error: {e}")
            return []
