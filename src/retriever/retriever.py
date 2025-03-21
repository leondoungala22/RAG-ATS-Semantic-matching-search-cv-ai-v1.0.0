import os
import sys
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.retrievers import MultiQueryRetriever, ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

# Ensure the project root is in the Python path.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import get_logger
import config
from retriever.helper_retriever import VectorStoreManager  # Re-use the common vector store loader

logger = get_logger("Retriever")

# Load the common vector store
vector_store = VectorStoreManager.load_existing_vector_store()
if not vector_store:
    logger.error("Vector store could not be loaded.")


class Retriever:
    def __init__(self):
        self.logger = get_logger("Retriever")
        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-4o-mini",
            openai_api_key=config.OPENAI_API_KEY
        )
        base_retriever = vector_store.as_retriever(
            search_type="similarity", search_kwargs={"k": 20}
        )
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
                preview = doc.page_content.strip().replace("\n", " ")[:200]
                self.logger.info(f"\n📄 ID: {doc_id}\n📃 Preview: {preview}\n")
                results.append({"id": doc_id, "doc": doc})
            self.logger.info(f"✅ Retrieved {len(results)} documents.")
            return results
        except Exception as e:
            self.logger.error(f"❌ Retrieval error: {e}")
            return []


if __name__ == "__main__":
    retriever_instance = Retriever()
    sample_query = "Sample job description for testing retrieval."
    retriever_instance.search(sample_query)
