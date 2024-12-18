import os
import sys
import openai
import numpy as np
import requests
from sklearn.metrics.pairwise import cosine_similarity  # Added import for cosine_similarity
import json
# Get the absolute path of the project's root directory (relative to this file)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the project root to the Python path
if project_root not in sys.path:
    sys.path.append(project_root)

from azure.cosmos import CosmosClient, PartitionKey
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.azure_cosmos_db_no_sql import AzureCosmosDBNoSqlVectorSearch
from dotenv import load_dotenv
from utils.logger import get_logger  
from anthropic import Anthropic 


# Load environment variables from a .env file
load_dotenv()


class Retriever:
    """
    A class to manage vector search operations using Azure Cosmos DB and Azure OpenAI embeddings.

    This class provides methods for initializing connections to Azure Cosmos DB,
    configuring Azure OpenAI embeddings, and performing similarity searches on vectorized data.
    """
    threshold = 0.65

    def __init__(self):
        """
        Initialize the Retriever with environment variables and necessary configurations.

        Loads environment variables to configure Azure Cosmos DB and Azure OpenAI embeddings.
        Logs the initialization process and sets up a vector search client.
        """
        # Set up logging
        self.logger = get_logger("Retriever")
        self.logger.info("Initializing Retriever...")

        # Load required environment variables
        self.cosmos_endpoint = os.getenv("COSMOS_ENDPOINT")
        self.cosmos_key = os.getenv("COSMOS_KEY")
        self.azure_database_target = os.getenv("AZURE_TARGET_DATABASE", "vectordb")
        self.azure_container_target = os.getenv("AZURE_TARGET_CONTAINER", "cv_collection")
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")  # Azure OpenAI key
        self.openai_api_key_main = os.getenv("OPENAI_API_KEY_MAIN")  # OpenAI key for re-ranking
        self.openai_api_version = os.getenv("OPENAI_API_VERSION", "2023-05-15")
        self.embeddings_model_deployment = os.getenv("OPENAI_EMBEDDINGS_MODEL_DEPLOYMENT", "text-embedding-ada-002")
       
        self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        

       
        # Initialize the vector search client
        self.vector_search = self.initialize_vector_search()

    def initialize_vector_search(self):
        """
        Initialize the vector search connection and configure the embedding and indexing policies.

        Returns:
            AzureCosmosDBNoSqlVectorSearch: Configured vector search client.
        """
        try:
            # Log the connection to Cosmos DB
            self.logger.info(f"Connecting to Cosmos DB at {self.cosmos_endpoint}...")
            cosmos_client = CosmosClient(self.cosmos_endpoint, credential=self.cosmos_key)

            # Initialize Azure OpenAI embeddings
            self.logger.info("Initializing Azure OpenAI embeddings...")
            embeddings = AzureOpenAIEmbeddings(
                azure_deployment=self.embeddings_model_deployment,
                api_version=self.openai_api_version,
                azure_endpoint=self.azure_openai_endpoint.rstrip("/"),
                openai_api_key=self.openai_api_key,  # Use Azure OpenAI key here
            )

            # Configure the vector search client
            self.logger.info("Initializing vector search client...")
            vector_search = AzureCosmosDBNoSqlVectorSearch(
                cosmos_client=cosmos_client,
                embedding=embeddings,
                database_name=self.azure_database_target,
                container_name=self.azure_container_target,
                vector_embedding_policy={
                    "vectorEmbeddings": [
                        {
                            "path": "/embedding",
                            "dataType": "float32",
                            "distanceFunction": "cosine",
                            "dimensions": 1536,
                        }
                    ]
                },
                indexing_policy={
                    "indexingMode": "consistent",
                    "includedPaths": [{"path": "/*"}],
                    "excludedPaths": [{"path": '/"_etag"/?'}],
                    "vectorIndexes": [{"path": "/embedding", "type": "quantizedFlat"}],
                },
                cosmos_container_properties={"partition_key": PartitionKey(path="/id")},
                cosmos_database_properties={"id": self.azure_database_target},
            )

            return vector_search

        except Exception as e:
            # Log and raise errors during initialization
            self.logger.error(f"Error initializing vector search: {e}")
            raise




    def perform_similarity_search(self, query, threshold=threshold):
        """
        Perform a similarity search using the vector search client and re-rank the results.
        
        Args:
            query (str): The query string to search for similar results.
            threshold (float): Minimum score threshold for filtering results.

        Returns:
            list: A list of dictionaries containing document IDs and their relevance scores.
        """
        try:
            self.logger.info("Performing similarity search...")

            # Retrieve initial results from the vector search
            initial_results = self.vector_search.similarity_search_with_score(query, k=20)

            # Format initial results
            structured_documents = self.format_initial_results(initial_results)

            # Extract content and metadata
            cv_contents = [doc['content'] for doc in structured_documents]
            cv_ids = [doc['id'] for doc in structured_documents]

            # Re-rank the results
            self.logger.info("Re-ranking results using Anthropic LLM...")
            ids, scores = self.rerank_results(query, cv_contents, cv_ids, threshold=threshold)

            # Log the re-ranked results
            self.logger.debug(f"Re-ranked IDs: {ids}")
            self.logger.debug(f"Re-ranked Scores: {scores}")

            if not ids or not scores:
                self.logger.warning("No results found after re-ranking.")
                return []

            # Combine IDs and scores into dictionaries
            reranked_results = [
                {"id": doc_id, "score": score} for doc_id, score in zip(ids, scores)
            ]

            # Sort by score in descending order
            reranked_results.sort(key=lambda x: x['score'], reverse=True)
            self.logger.info(f"Top relevant results: {reranked_results}")

            # Limit to the top 10 results
            top_results = reranked_results[:10]
            self.logger.info(f"Returning top {len(top_results)} relevant results.")

            return top_results

        except Exception as e:
            self.logger.error(f"Error during similarity search: {e}")
            raise









    

    def format_initial_results(self, initial_results):
        """
        Formats the initial results into a JSON-safe structured format for optimized embeddings.
        
        Args:
            initial_results (list): The raw initial results from the vector search.

        Returns:
            list: A list of dictionaries with structured content and metadata in JSON format.
        """
        import json 
        try:
            structured_documents = []

            for result in initial_results:
                content = result[0].page_content
                metadata = result[0].metadata
                document_id = metadata.get("id", "Unknown")

                # Construct a JSON-safe representation of the document
                document_data = {
                    "Document ID": document_id,
                    "Content": content,
                    "Metadata": metadata
                }

                # Serialize the entire document to a JSON string
                structured_content = json.dumps(document_data, ensure_ascii=False, indent=4)

                structured_documents.append({
                    "content": structured_content,
                    "id": document_id
                })

            return structured_documents

        except Exception as e:
            self.logger.error(f"Error formatting initial results: {e}")
            raise







    




    def rerank_results(self, query, documents, doc_ids, threshold=threshold):
        """
        Re-rank the search results using Anthropic LLM based on document JSON descriptions.

        Args:
            query (str): The query string.
            documents (list): List of document contents in JSON format.
            doc_ids (list): List of document IDs.
            threshold (float): Minimum score threshold for filtering results.

        Returns:
            tuple: A tuple containing a list of filtered document IDs and a list of corresponding scores.
        """
        try:
            # Prepare input for the Anthropic LLM
            prompt = (
                "You are an HR AI assistant for an ATS system. Your task is to re-rank candidate CVs based on their relevance to the following query or job description:\n\n"
                f"Job Description: {query}\n\n"
                "Relevance should be determined by analyzing how well each CV aligns with the skills, qualifications, experience , studies and studie level , and job responsibilities etc ... mentioned in the job description.\n\n"
                f"The threshold for relevance is {threshold:.1f}. Candidates who do not meet this threshold should not be top-ranked, regardless of other factors.\n\n"
                "Assign a relevance score between 0 and 1 (4-decimal precision) to each CV. CVs with higher scores are more relevant to the query or job description.\n\n"
                "Output only the document IDs and scores in the following format:\n"
                "Document ID: [id], Score: [score]\n\n"
                "Do not include any explanations, comments, or additional information. "
                "Here are the CVs:\n\n"
            )

            # Add documents with their IDs to the prompt
            for doc_id, document in zip(doc_ids, documents):
                prompt += f"Document ID: {doc_id}\nContent:\n{document}\n\n"

            # Call the Anthropic LLM
            ids, scores = self.call_anthropic_llm(prompt)

            # Guard against empty responses
            if not ids or not scores:
                self.logger.warning("No results returned from the LLM.")
                return [], []

            # Filter results based on the threshold
            filtered_ids = []
            filtered_scores = []

            for doc_id, score in zip(ids, scores):
                if score >= threshold:
                    filtered_ids.append(doc_id)
                    filtered_scores.append(round(score, 4))  # Round to 4 decimal places

            # Log filtered results
            self.logger.debug(f"Filtered IDs: {filtered_ids}")
            self.logger.debug(f"Filtered Scores: {filtered_scores}")

            return filtered_ids, filtered_scores

        except Exception as e:
            self.logger.error(f"Error during LLM-based re-ranking: {e}")
            raise


















    def call_anthropic_llm(self, prompt):
        """
        Call Anthropic's Claude model with the given prompt to compute relevance scores.

        Args:
            prompt (str): The prompt containing the query and documents.

        Returns:
            tuple: Two lists, one for document IDs and the other for their respective scores.
        """
        try:
            # Send the prompt to Anthropic's Claude model
            message = self.anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",  # Replace with the correct model name
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract the response content
            response_content = message.content
            if isinstance(response_content, list):  # Handle if response is a list
                response_content = response_content[0]

            # Log the raw response for debugging
            self.logger.debug(f"Raw response from Anthropic LLM:\n{response_content}")

            # Parse the response to extract IDs and scores
            ids = []
            scores = []
            for line in response_content.text.splitlines():
                # Parse lines formatted as "Document ID: Score"
                try:
                    doc_id, score_str = line.split(": ")
                    doc_id = doc_id.strip()
                    score = round(float(score_str.strip()), 4)  # Ensure scores are four-decimal floats
                    if 0 <= score <= 1:  # Validate the score range
                        ids.append(doc_id)
                        scores.append(score)
                    else:
                        self.logger.warning(f"Invalid score for Document ID {doc_id}: {score}")
                except ValueError as e:
                    self.logger.warning(f"Failed to parse line: {line}. Error: {e}")


            return ids, scores

        except Exception as e:
            self.logger.error(f"Error calling Anthropic LLM: {e}")
            raise




    def query_document_by_id(self, client, database_name, container_name, document_id, logger):
        """
        Queries the Cosmos DB for a specific document by ID.

        Args:
            client (CosmosClient): The Cosmos DB client.
            database_name (str): Name of the database.
            container_name (str): Name of the container.
            document_id (str): The document ID to query.
            logger (Logger): Logger instance.

        Returns:
            dict: The document retrieved from the database.
        """
        try:
            logger.info(f"Querying document with ID: {document_id}")
            database = client.get_database_client(database_name)
            container = database.get_container_client(container_name)

            # Query Cosmos DB for the document by ID
            query = f"SELECT * FROM c WHERE c.id = '{document_id}'"
            items = list(container.query_items(query=query, enable_cross_partition_query=True))

            if items:
                return items[0]
            else:
                logger.warning(f"No document found with ID: {document_id}")
                return None
        except Exception as e:
            logger.error(f"Error querying document with ID {document_id}: {e}")
            return None