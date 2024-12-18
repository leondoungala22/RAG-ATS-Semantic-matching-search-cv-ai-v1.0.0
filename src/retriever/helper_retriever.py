# helper_retriever.py

import os
import sys
import mysql.connector
from retriever.retriever import Retriever
from utils.logger import get_logger
from azure.cosmos import CosmosClient
import base64
import json
from dotenv import load_dotenv
import openai
import numpy as np 


# Get the absolute path of the project's root directory (relative to this file)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the project root to the Python path
if project_root not in sys.path:
    sys.path.append(project_root)



class CVRetrieverApp:
    def __init__(self):
        """
        Initializes the CVRetrieverApp instance with Cosmos DB, Retriever, and MySQL connection.
        """
        self.logger = get_logger("CVRetrieverApp")
        self._initialize_cosmos_client()
        self._initialize_mysql_client()
        self.retriever = Retriever()

        # Load environment variables
        load_dotenv()
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY_MAIN')
        if not self.OPENAI_API_KEY:
            self.logger.error("OpenAI API key not found in environment variables.")
            raise ValueError("OpenAI API key is required.")

        openai.api_key = self.OPENAI_API_KEY

    def _initialize_cosmos_client(self):
        """
        Initializes the Cosmos DB client using environment variables.
        """
        try:
            self.logger.info("Initializing Cosmos DB client...")
            cosmos_endpoint = os.getenv("COSMOS_ENDPOINT")
            cosmos_key = os.getenv("COSMOS_KEY")
            self.database_name = os.getenv("AZURE_DATABASE", "cv_database")
            self.container_name = os.getenv("AZURE_CONTAINER", "cv_collection")
            self.cosmos_client = CosmosClient(cosmos_endpoint, credential=cosmos_key)
            self.logger.info("Cosmos DB client initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Cosmos DB client: {e}")
            raise

    def _initialize_mysql_client(self):
        """
        Initializes the MySQL client connection.
        """
        try:
            self.logger.info("Initializing MySQL client...")
            self.mysql_conn = mysql.connector.connect(
                user=os.getenv('MYSQL_USER_LOCAL'),
                password=os.getenv('MYSQL_PASSWORD_LOCAL'),
                host=os.getenv('MYSQL_HOST_LOCAL'),
                database=os.getenv('MYSQL_DB_TEST_NAME_LOCAL')
            )
            self.logger.info("MySQL client initialized successfully.")
        except mysql.connector.Error as e:
            self.logger.error(f"Failed to initialize MySQL client: {e}")
            raise

    def load_job_description(self, path):
        """
        Loads the job description from a specified file path.
        :param path: The file path to the job description.
        :return: The loaded job description text.
        """
        if not os.path.exists(path):
            self.logger.error(f"Job description file not found: {path}")
            return None
        
        with open(path, "r") as file:
            query = file.read().strip()
            if not query:
                self.logger.error("Job description file is empty.")
                return None
            self.logger.info("Loaded job description query successfully.")
            return query
        

    def perform_similarity_search(self, query):
        """
        Performs a similarity search using the Retriever and applies a dynamic threshold.
        :param query: The query to perform the similarity search on.
        :return: A list of filtered search results.
        """
        self.logger.info("Performing similarity search...")
        
        # Get the search results, which include 'score' for each result
        results = self.retriever.perform_similarity_search(query)
        
        # Extract the scores from the results
        scores = [result.get('score', 0) for result in results]
        
        if not scores:
            self.logger.warning("No results found.")
            return []
        
        # Compute the mean and standard deviation of the scores
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        
        # Calculate the dynamic threshold
        threshold = mean_score - (0.5 * std_score)  # Adjust the multiplier as needed
        self.logger.info(f"Dynamic threshold set at: {threshold:.4f}")
        
        # Filter the results based on the dynamic threshold
        filtered_results = [
            result for result in results if result.get('score', 0) >= threshold
        ]
        
        # Optionally, sort the filtered results by score in descending order
        filtered_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return filtered_results


    def display_results(self, filtered_results):
        """
        Displays and queries results from Cosmos DB.
        :param filtered_results: The filtered similarity search results.
        """
        if filtered_results:
            self.logger.info(f"{len(filtered_results)} result(s) :")
            for i, result in enumerate(filtered_results, start=1):
                document_id = result['id']
                score = result.get('score', 'N/A')
                
                self.logger.info(f"\n{'-' * 30} Result {i} {'-' * 30}")
                self.logger.info(f"Document ID: {document_id}")
                self.logger.info(f"Similarity Score: {score}")
                
                # Query Cosmos DB for the full document
                document = self.query_document_by_id(document_id)

                if document:
                    # Dynamically format the document into a readable CV format
                    formatted_cv = self.format_document_dynamically(document)
                    self.logger.info(f"Formatted CV:\n{formatted_cv}")
                else:
                    self.logger.warning(f"No document found for ID: {document_id}")
                self.logger.info(f"{'-' * 72}\n")
        else:
            self.logger.info("No results found.")


    def query_document_by_id(self, document_id):
        """
        Queries a document by its ID from Cosmos DB.
        :param document_id: The ID of the document to be queried.
        :return: The document if found, otherwise None.
        """
        try:
            container = self.cosmos_client.get_database_client(self.database_name).get_container_client(self.container_name)
            document = container.read_item(item=document_id, partition_key=document_id)
            return document
        except Exception as e:
            self.logger.error(f"Failed to query document by ID {document_id}: {e}")
            return None

    def run(self):
        """
        Main execution function.
        """
        try:
            job_description_path = os.path.join("src/data/job description/Job_Description_Italian.txt")
            query = self.load_job_description(job_description_path)
            if not query:
                return
            
            filtered_results = self.perform_similarity_search(query)
            self.display_results(filtered_results)
        except Exception as e:
            self.logger.error(f"Error in execution: {e}")

    def format_document_dynamically(self, document, indent_level=0):
        """
        Dynamically formats a NoSQL document into a real-life CV format.
        Args:
            document (dict): The NoSQL document retrieved from the database.
            indent_level (int): Current indentation level for nested structures.
        Returns:
            str: A formatted CV as a string.
        """
        formatted_lines = []
        indent = "  " * indent_level  # Indentation for nested levels

        for key, value in document.items():
            if key.startswith("_"):  # Skip system keys like _rid, _etag, etc.
                continue

            if isinstance(value, dict):  # If the value is a dictionary, process it recursively
                formatted_lines.append(f"{indent}{key.capitalize()}:")
                formatted_lines.append(self.format_document_dynamically(value, indent_level + 1))
            elif isinstance(value, list):  # If the value is a list, process each element
                formatted_lines.append(f"{indent}{key.capitalize()}:")
                for item in value:
                    if isinstance(item, dict):  # Nested dictionary in a list
                        formatted_lines.append(self.format_document_dynamically(item, indent_level + 1))
                    else:
                        formatted_lines.append(f"{indent}  - {item}")
            else:  # For simple key-value pairs
                formatted_lines.append(f"{indent}{key.capitalize()}: {value}")

        return "\n".join(formatted_lines)


    def get_candidate_cv(self, candidate_id):
        """
        Retrieves the CV as base64-encoded data from the MySQL attachments table.

        Args:
            candidate_id (str): The ID of the CV to retrieve.

        Returns:
            str: The base64-encoded string of the CV PDF.
        """
        cursor = None
        try:
            if not hasattr(self, 'mysql_conn') or not self.mysql_conn.is_connected():
                self._initialize_mysql_client()
                
            cursor = self.mysql_conn.cursor()
            cursor.execute("SELECT pdf FROM attachments WHERE id = %s", (candidate_id,))
            result = cursor.fetchone()
            if result:
                # Encode the binary data to base64 to facilitate viewing in the browser
                return base64.b64encode(result[0]).decode('utf-8')
            else:
                self.logger.warning(f"No CV found for ID: {candidate_id}")
                return None
        except mysql.connector.Error as e:
            self.logger.error(f"Failed to retrieve attachment from MySQL: {e}")
            raise RuntimeError("Error retrieving attachment from MySQL database.")
        finally:
            if cursor is not None:
                cursor.close()
