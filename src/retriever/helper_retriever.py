import os
import sys
import json
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain.schema import Document
from langchain.retrievers import MultiQueryRetriever
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# Add project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import get_logger

# ========================== #
#  ✅ ENV + CONFIG          #
# ========================== #

load_dotenv()
logger = get_logger("HelperRetriever")

CHROMA_DB_PATH = "src/data/chromadb"
JOB_DESCRIPTION_PATH = "src/data/job description/Job_Description_Italian.txt"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_MAIN")
EMBEDDINGS_MODEL = os.getenv("OPENAI_EMBEDDINGS_MODEL_DEPLOYMENT", "text-embedding-ada-002")

# ========================== #
#  ✅ Load Chroma DB        #
# ========================== #

embeddings = OpenAIEmbeddings(
    model=EMBEDDINGS_MODEL,
    openai_api_key=OPENAI_API_KEY
)

def load_existing_vector_store():
    logger.info("📂 Loading existing Chroma vector store...")
    try:
        vectorstore = Chroma(
            persist_directory=CHROMA_DB_PATH,
            embedding_function=embeddings
        )
        logger.info("✅ Vector store loaded.")
        return vectorstore
    except Exception as e:
        logger.error(f"❌ Could not load vector store: {e}")
        return None

# ========================== #
#  ✅ Main Retriever Class  #
# ========================== #

class HelperRetriever:
    def __init__(self, vectorstore, threshold=0.65):
        self.logger = get_logger("HelperRetriever")
        self.vectorstore = vectorstore
        self.threshold = threshold

        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-4o-mini",
            openai_api_key=OPENAI_API_KEY
        )

        base_retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 20})
        self.retriever = MultiQueryRetriever.from_llm(retriever=base_retriever, llm=self.llm)

    def load_job_description(self, path):
        if not os.path.exists(path):
            self.logger.error(f"❌ Job description not found: {path}")
            return None
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        self.logger.info(f"📄 Loaded job description from: {path}")
        self.logger.debug(f"📝 Job Description:\n{content}")
        return content

    def perform_search(self, query):
        try:
            self.logger.info("🔍 Performing OpenAI-powered multi-query search...")
            documents = self.retriever.invoke(query)

            if not documents:
                self.logger.warning("⚠️ No documents retrieved.")
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

    def rerank_with_openai(self, query, results):
        try:
            self.logger.info("🤖 Re-ranking results using OpenAI LLM to simulate HR filtering...")

            # Step 1: Reranking prompt
            prompt = (
                f"You are an AI HR assistant. Rank the following CVs based on this job description:\n\n"
                f"Job Description:\n{query}\n\n"
                f"Score each from 0.0 to 1.0 based on match to role, skills, experience pay attention to not retrun candidates that are not interrested for the postion avoid also duplicating candidates .\n"
                f"Exclude outdated, irrelevant, or unrelated profiles.\n\n"
                f"Return only lines in this format:\n"
                f"Document ID: <doc_id>, Score: <score>, Reason: <short_reason>\n\n"
            )

            for r in results:
                prompt += f"Document ID: {r['id']}\nContent:\n{r['doc'].page_content}\n\n"

            response = self.llm.invoke(prompt).content.strip()
            self.logger.debug(f"🔁 LLM Raw Response:\n{response}")

            # Step 2: Parse the output
            ids, scores, reasons = [], [], []
            for line in response.splitlines():
                try:
                    if not line.lower().startswith("document id:"):
                        continue
                    parts = line.split(",")
                    doc_id = parts[0].split(":", 1)[1].strip()
                    score = float(parts[1].split(":", 1)[1].strip())
                    reason = parts[2].split(":", 1)[1].strip() if len(parts) > 2 else "N/A"
                    if score >= self.threshold:
                        ids.append(doc_id)
                        scores.append(score)
                        reasons.append(reason)
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not parse line: {line} | {e}")

            # Step 3: Match back to original documents
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

    def format_content(self, content):
        try:
            data = json.loads(content)
            return self.flatten_json(data)
        except:
            return content

    def flatten_json(self, data):
        lines = []
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"{key.title()}: {', '.join(map(str, value))}")
            elif isinstance(value, dict):
                lines.append(f"{key.title()}:\n{self.flatten_json(value)}")
            else:
                lines.append(f"{key.title()}: {value}")
        return "\n".join(lines)

    def display_results(self, results):
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

    def run_pipeline(self, job_path):
        query = self.load_job_description(job_path)
        if not query:
            return

        raw_results = self.perform_search(query)
        filtered_results = self.rerank_with_openai(query, raw_results)
        self.display_results(filtered_results)

# ========================== #
#  ✅ MAIN RUNNER           #
# ========================== #

if __name__ == "__main__":
    vectorstore = load_existing_vector_store()
    if vectorstore:
        retriever = HelperRetriever(vectorstore, threshold=0.65)
        retriever.run_pipeline(JOB_DESCRIPTION_PATH)
