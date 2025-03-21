import os
import sys
import json
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain.schema import Document
from langchain.retrievers import MultiQueryRetriever
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import get_logger

# ========================== #
#  Configuration             #
# ========================== #

load_dotenv()
logger = get_logger("HelperRetriever")

CHROMA_DB_PATH = "src/data/chromadb"
JOB_DESCRIPTION_PATH = "src/data/job description/Job_Description_Italian.txt"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_MAIN")
EMBEDDINGS_MODEL = os.getenv("OPENAI_EMBEDDINGS_MODEL_DEPLOYMENT", "text-embedding-ada-002")


class VectorStoreManager:
    """Manages vector store operations."""

    @staticmethod
    def load_existing_vector_store() -> Optional[Chroma]:
        """
        Load the existing Chroma vector store.
        
        Returns:
            Chroma: Vector store object if successful, None otherwise
        """
        logger.info("📂 Loading existing Chroma vector store...")
        try:
            embeddings = OpenAIEmbeddings(
                model=EMBEDDINGS_MODEL,
                openai_api_key=OPENAI_API_KEY
            )
            
            vectorstore = Chroma(
                persist_directory=CHROMA_DB_PATH,
                embedding_function=embeddings
            )
            logger.info("✅ Vector store loaded.")
            return vectorstore
        except Exception as e:
            logger.error(f"❌ Could not load vector store: {e}")
            return None


class HelperRetriever:
    """Main retriever class for CV matching and ranking."""
    
    def __init__(self, vectorstore: Chroma, threshold: float = 0.5):
        """
        Initialize the retriever with a vector store.
        
        Args:
            vectorstore: The Chroma vector store to use for retrieval
            threshold: Minimum score threshold for reranking results (default: 0.5)
        """
        self.logger = get_logger("HelperRetriever")
        self.vectorstore = vectorstore
        self.threshold = threshold

        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-4o-mini",
            openai_api_key=OPENAI_API_KEY
        )

        self.base_retriever = vectorstore.as_retriever(
            search_type="similarity", 
            search_kwargs={"k": 20}
        )
        
        self.retriever = MultiQueryRetriever.from_llm(
            retriever=self.base_retriever, 
            llm=self.llm
        )

    def load_job_description(self, path: str) -> Optional[str]:
        """
        Load job description from a file.
        
        Args:
            path: Path to the job description file
            
        Returns:
            str: Job description content if successful, None otherwise
        """
        if not os.path.exists(path):
            self.logger.error(f"❌ Job description not found: {path}")
            return None
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        self.logger.info(f"📄 Loaded job description from: {path}")
        self.logger.debug(f"📝 Job Description:\n{content}")
        return content

    def perform_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Perform search using multi-query retriever.
        
        Args:
            query: Job description or search query
            
        Returns:
            List of result dictionaries with document info and scores
        """
        try:
            self.logger.info("🔍 Performing OpenAI-powered multi-query search...")
            documents = self.retriever.invoke(query)

            if not documents:
                self.logger.warning("⚠️ Multi-query returned 0 documents. Trying fallback...")
                documents = self.base_retriever.invoke(query)

            if not documents:
                self.logger.warning("⚠️ Still no results after fallback.")
                return []

            results = []
            self.logger.info(f"✅ Retrieved {len(documents)} documents before reranking.")

            for i, doc in enumerate(documents):
                doc_id = doc.metadata.get("source", f"doc_{i}")
                preview = doc.page_content.strip().replace("\n", " ")[:200]
                self.logger.info(f"\n--- Document #{i + 1} ---")
                self.logger.info(f"📄 ID: {doc_id}")
                self.logger.info(f"📃 Preview: {preview}")
                self.logger.info(f"🟢 Score: 1.0000 (pre-reranking)\n")
                results.append({"id": doc_id, "doc": doc, "score": 1.0})
                
            return results

        except Exception as e:
            self.logger.error(f"❌ Error during search: {e}")
            return []

    def rerank_with_openai(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rerank results using OpenAI LLM.
        
        Args:
            query: Original job description or query
            results: List of initial search results
            
        Returns:
            Reranked and filtered list of results with scores and reasons
        """
        try:
            if not results:
                self.logger.warning("⚠️ Skipping reranking – no documents to process.")
                return []

            self.logger.info("🤖 Re-ranking results using OpenAI LLM to simulate HR filtering...")

            prompt = (
                f"You are an AI HR assistant helping a recruiter select the most suitable CVs for the following job description:\n\n"
                f"Job Description:\n{query}\n\n"
                f"Your task is to evaluate and score each CV based on how well it aligns with the job description above.\n\n"
                f"Instructions:\n"
                f"- Prioritize CVs that clearly match the required skills, experience, certifications, and education.\n"
                f"- Strongly prefer candidates with direct and recent experience relevant to the role.\n"
                f"- Soft skills like motivation, communication, leadership, and initiative can increase relevance.\n"
                f"- If a candidate shows transferable skills and strong motivation, they can still be considered.\n"
                f"- Assign a relevance score between 0.0 and 1.0:\n"
                f"  • 1.0 = Excellent fit\n"
                f"  • 0.8 = Very good match\n"
                f"  • 0.5 = Acceptable but partial match\n"
                f"  • Below 0.3 = Weak or irrelevant profile\n"
                f"- Do not assign 0.0 unless the CV is completely unrelated.\n"
                f"- Avoid scoring duplicate or near-identical CVs.\n\n"
                f"Return only one line per CV in the format:\n"
                f"Document ID: <doc_id>, Score: <score>, Reason: <short_reason>"
            )

            for r in results:
                prompt += f"Document ID: {r['id']}\nContent:\n{r['doc'].page_content}\n\n"

            response = self.llm.invoke(prompt).content.strip()
            self.logger.debug(f"🔁 LLM Raw Response:\n{response}")

            ids, scores, reasons, seen = [], [], [], set()
            for line in response.splitlines():
                try:
                    if not line.lower().startswith("document id:"):
                        continue
                    parts = line.split(",")
                    doc_id = parts[0].split(":", 1)[1].strip()
                    score = float(parts[1].split(":", 1)[1].strip())
                    reason = parts[2].split(":", 1)[1].strip() if len(parts) > 2 else "N/A"
                    if score >= self.threshold and doc_id not in seen:
                        ids.append(doc_id)
                        scores.append(score)
                        reasons.append(reason)
                        seen.add(doc_id)
                except Exception as e:
                    self.logger.warning(f"⚠️ Skipped line: {line} | {e}")

            filtered = []
            for i, doc_id in enumerate(ids):
                match = next((r for r in results if r["id"] == doc_id), None)
                if match:
                    match["score"] = scores[i]
                    match["reason"] = reasons[i]
                    filtered.append(match)

            self.logger.info(f"✅ Re-ranked and selected {len(filtered)} candidates above threshold {self.threshold}.")
            return filtered

        except Exception as e:
            self.logger.error(f"❌ Error during reranking: {e}")
            return results  # fallback

    def format_content(self, content: str) -> str:
        """
        Format document content for display.
        
        Args:
            content: Document content string, possibly in JSON format
            
        Returns:
            Formatted string representation
        """
        try:
            data = json.loads(content)
            return self.flatten_json(data)
        except:
            return content

    def flatten_json(self, data: Dict[str, Any]) -> str:
        """
        Convert nested JSON to flattened string representation.
        
        Args:
            data: Dictionary (possibly nested) to flatten
            
        Returns:
            Flattened string representation
        """
        lines = []
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"{key.title()}: {', '.join(map(str, value))}")
            elif isinstance(value, dict):
                lines.append(f"{key.title()}:\n{self.flatten_json(value)}")
            else:
                lines.append(f"{key.title()}: {value}")
        return "\n".join(lines)

    def display_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Display formatted results to the logger.
        
        Args:
            results: List of result dictionaries to display
        """
        self.logger.info(f"📊 Displaying {len(results)} top matched CV(s):")
        for i, r in enumerate(results, start=1):
            doc_id = r["id"]
            score = r.get("score", 1.0)
            reason = r.get("reason", "N/A")
            doc = r["doc"]

            self.logger.info(f"\n{'='*30} CV #{i} {'='*30}")
            self.logger.info(f"🆔 Document ID: {doc_id}")
            self.logger.info(f"📈 Score: {score:.4f}")
            self.logger.info(f"💡 Why Selected: {reason}")

            formatted = self.format_content(doc.page_content)
            self.logger.info(f"📄 CV Content:\n{formatted}")

    def run_pipeline(self, job_path: str) -> None:
        """
        Run the entire retrieval and ranking pipeline.
        
        Args:
            job_path: Path to the job description file
        """
        query = self.load_job_description(job_path)
        if not query:
            return

        raw_results = self.perform_search(query)
        filtered_results = self.rerank_with_openai(query, raw_results)
        self.display_results(filtered_results)


# ========================== #
#  Main Execution            #
# ========================== #

if __name__ == "__main__":
    vectorstore = VectorStoreManager.load_existing_vector_store()
    if vectorstore:
        retriever = HelperRetriever(vectorstore, threshold=0.5)
        retriever.run_pipeline(JOB_DESCRIPTION_PATH)