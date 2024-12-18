
# embeddings.py 

import os
import logging
import traceback
from azure.cosmos import CosmosClient, PartitionKey
from langchain.schema import Document
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.azure_cosmos_db_no_sql import AzureCosmosDBNoSqlVectorSearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

# Environment Variables
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
AZURE_DATABASE_SOURCE = os.getenv("AZURE_DATABASE", "cv_database")  # Source database
AZURE_CONTAINER_SOURCE = os.getenv("AZURE_CONTAINER", "cv_collection")  # Source container
AZURE_DATABASE_TARGET = os.getenv("AZURE_TARGET_DATABASE", "vectordb")  # Target vector database
AZURE_CONTAINER_TARGET = os.getenv("AZURE_CONTAINER", "vector_collection")  # Target vector container
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2023-05-15")
EMBEDDINGS_MODEL_DEPLOYMENT = os.getenv("OPENAI_EMBEDDINGS_MODEL_DEPLOYMENT", "text-embedding-ada-002")

# Indexing policies
indexing_policy = {
    "indexingMode": "consistent",
    "includedPaths": [{"path": "/*"}],
    "excludedPaths": [{"path": '/"_etag"/?'}],
    "vectorIndexes": [{"path": "/embedding", "type": "quantizedFlat"}],
}

vector_embedding_policy = {
    "vectorEmbeddings": [
        {
            "path": "/embedding",
            "dataType": "float32",
            "distanceFunction": "cosine",
            "dimensions": 1536,
        }
    ]
}

def validate_env_vars():
    """Ensure required environment variables are set."""
    required_vars = ["COSMOS_ENDPOINT", "COSMOS_KEY", "AZURE_OPENAI_ENDPOINT", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

def fetch_documents_from_source():
    """Fetches documents from the source Cosmos DB container."""
    try:
        logger.info(f"Connecting to source Cosmos DB at {COSMOS_ENDPOINT}...")
        cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
        source_db = cosmos_client.get_database_client(AZURE_DATABASE_SOURCE)
        source_container = source_db.get_container_client(AZURE_CONTAINER_SOURCE)

        logger.info("Fetching documents from source container...")
        documents = list(source_container.read_all_items())
        logger.info(f"Fetched {len(documents)} documents.")
        return documents
    except Exception as e:
        logger.error(f"Error fetching documents from source: {e}")
        logger.error(traceback.format_exc())
        return []

def process_full_documents(documents):
    """
    Processes full documents without splitting them.
    Returns a list of Document objects for compatibility with vector search.
    """
    logger.info("Processing full documents...")
    docs = []
    for doc in documents:
        formatted_text = ""
        for key, value in doc.items():
            if key.startswith("_"):  # Skip metadata fields
                continue
            formatted_text += f"{key.title()}:\n  - {value}\n\n"

        # Retain the source document ID in metadata
        docs.append(Document(page_content=formatted_text, metadata={"id": doc["id"]}))

    logger.info(f"Processed {len(docs)} full documents.")
    return docs

def insert_to_vector_store(documents):
    """Inserts documents into the Azure Cosmos DB NoSQL vector store in the target database."""
    try:
        logger.info(f"Connecting to target Cosmos DB at {COSMOS_ENDPOINT}...")
        cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)

        # Create target database and container if they do not exist
        target_db = cosmos_client.create_database_if_not_exists(id=AZURE_DATABASE_TARGET)
        target_db.create_container_if_not_exists(
            id=AZURE_CONTAINER_TARGET,
            partition_key=PartitionKey(path="/id")
        )

        logger.info(f"Initializing Azure OpenAI embeddings with endpoint: {AZURE_OPENAI_ENDPOINT}...")
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=EMBEDDINGS_MODEL_DEPLOYMENT,
            api_version=OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT.rstrip("/"),
            openai_api_key=OPENAI_API_KEY,
        )

        logger.info("Inserting documents into vector store in target database...")
        
        # Ensure IDs align between source and target
        AzureCosmosDBNoSqlVectorSearch.from_documents(
            documents=documents,
            embedding=embeddings,
            cosmos_client=cosmos_client,
            database_name=AZURE_DATABASE_TARGET,
            container_name=AZURE_CONTAINER_TARGET,
            vector_embedding_policy=vector_embedding_policy,
            indexing_policy=indexing_policy,
            cosmos_container_properties={
                "id": AZURE_CONTAINER_TARGET,
                "partition_key": {"paths": ["/id"], "kind": "Hash"}
            },
            cosmos_database_properties={"id": AZURE_DATABASE_TARGET},
        )

        logger.info("Documents successfully inserted into vector store.")
    except Exception as e:
        logger.error(f"Error inserting documents into vector store: {e}")
        logger.error(traceback.format_exc())

def main():
    """Main function to load documents from source, process them, and store them in the vector database."""
    try:
        validate_env_vars()
        logger.info("Starting the document processing pipeline...")
        documents = fetch_documents_from_source()
        if not documents:
            logger.error("No documents fetched. Exiting.")
            return
        docs = process_full_documents(documents)  # Updated function call
        insert_to_vector_store(docs)
    except EnvironmentError as env_error:
        logger.error(env_error)

if __name__ == "__main__":
    main()
