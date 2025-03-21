import os
import sys
import json
from typing import List, Dict, Any, Optional
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain.retrievers import MultiQueryRetriever
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# Ensure the project root is in the Python path.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import get_logger
import config

logger = get_logger("HelperRetriever")


class VectorStoreManager:
    """Manages vector store operations."""
    
    @staticmethod
    def load_existing_vector_store() -> Optional[Chroma]:
        logger.info("📂 Loading existing Chroma vector store...")
        try:
            embeddings = OpenAIEmbeddings(
                model=config.EMBEDDINGS_MODEL,
                openai_api_key=config.OPENAI_API_KEY
            )
            vectorstore = Chroma(
                persist_directory=config.CHROMA_DB_PATH,
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
        self.logger = get_logger("HelperRetriever")
        self.vectorstore = vectorstore
        self.threshold = threshold

        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-4o-mini",
            openai_api_key=config.OPENAI_API_KEY
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
        if not os.path.exists(path):
            self.logger.error(f"❌ Job description not found: {path}")
            return None
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        self.logger.info(f"📄 Loaded job description from: {path}")
        self.logger.debug(f"📝 Job Description:\n{content}")
        return content

    def perform_search(self, query: str) -> List[Dict[str, Any]]:
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
                f"- Do not assign 0.0 unless the CV is completely unrelated.\n"
                f"- Avoid scoring duplicate or near-identical CVs.\n\n"
                f"Return only one line per CV in the format:\n"
                f"Document ID: <doc_id>, Score: <score>, Reason: <short_reason>"
            )
            for r in results:
                prompt += f"\nDocument ID: {r['id']}\nContent:\n{r['doc'].page_content}\n"
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
        try:
            data = json.loads(content)
            return self.flatten_json(data)
        except:
            return content

    def flatten_json(self, data: Dict[str, Any]) -> str:
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
        query = self.load_job_description(job_path)
        if not query:
            return
        raw_results = self.perform_search(query)
        filtered_results = self.rerank_with_openai(query, raw_results)
        self.display_results(filtered_results)


if __name__ == "__main__":
    vectorstore = VectorStoreManager.load_existing_vector_store()
    if vectorstore:
        retriever = HelperRetriever(vectorstore, threshold=0.5)
        retriever.run_pipeline(config.JOB_DESCRIPTION_PATH)
