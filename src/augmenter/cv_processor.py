
#cv_processor.py 

import os
import sys

# Get the absolute path of the project's root directory (relative to this file)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the project root to the Python path
if project_root not in sys.path:
    sys.path.append(project_root)



import json
import os
import re
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
from utils.logger import get_logger
import fitz
from uuid import uuid4
from azure.cosmos import CosmosClient, PartitionKey
from prompts.prompt_templates import get_create_structured_cv_prompt_template_text
from win32com import client
from DataTools import DataTool
import base64
import shutil
from azure.storage.blob import BlobServiceClient
import mysql.connector
from mysql.connector import Error




# Load environment variables
load_dotenv()
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Configure logging
log = get_logger("CVProcessor")


class CVProcessor:
    
    def __init__(self, model="claude-3-5-haiku-20241022"):
        """
        Initializes the CVProcessor with the specified Anthropic Claude model,
        Azure Cosmos DB connection, and MySQL connection.
        """
        self.model = model
        log.info("CVProcessor initialized with model: %s", model)

        # Azure Cosmos DB connection using the URI and database name from the .env file
        cosmos_uri = os.getenv("COSMOS_ENDPOINT")
        cosmos_key = os.getenv("COSMOS_KEY")
        db_name = os.getenv("AZURE_DATABASE")
        container_name = os.getenv("AZURE_CONTAINER")

        if not cosmos_uri or not cosmos_key or not db_name or not container_name:
            log.critical("Azure Cosmos DB connection details are missing in the .env file.")
            raise RuntimeError("Azure Cosmos DB connection details are required.")

        try:
            log.info("Connecting to Azure Cosmos DB...")
            # Connect to Azure Cosmos DB
            self.client = CosmosClient(cosmos_uri, credential=cosmos_key)

            # Ensure database and container exist
            self.database = self.client.create_database_if_not_exists(db_name)
            self.container = self.database.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path="/id"),
                offer_throughput=400  # Adjust throughput as needed
            )
            log.info("Successfully connected to Azure Cosmos DB.")
        except Exception as e:
            log.critical(f"Failed to connect to Azure Cosmos DB: {e}")
            raise RuntimeError("Azure Cosmos DB connection failed.")

        # Connect to MySQL and ensure 'attachments' table exists
        try:
            log.info("Connecting to MySQL database...")
            self.mysql_conn = mysql.connector.connect(
                user=os.getenv('MYSQL_USER_LOCAL'),
                password=os.getenv('MYSQL_PASSWORD_LOCAL'),
                host=os.getenv('MYSQL_HOST_LOCAL'),
                port=os.getenv('MYSQL_PORT_LOCAL')
            )
            self.ensure_attachments_table_exists()  # Ensure the attachments table exists
            log.info("Successfully connected to MySQL database and ensured the 'attachments' table exists.")
        except Exception as e:
            log.critical(f"Failed to connect to MySQL database: {e}")
            raise RuntimeError("MySQL connection failed.")



    def test_connection(self):
        """
        Test the Azure Cosmos DB connection.
        """
        try:
            items = list(self.container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True))
            log.info(f"Azure Cosmos DB connection is active. Retrieved {len(items)} items.")
        except Exception as e:
            log.critical(f"Azure Cosmos DB connection test failed: {e}")
            raise RuntimeError("Azure Cosmos DB connection is not active.")
        


    def ensure_attachments_table_exists(self):
        """
        Ensures that the 'cv_attachment' database and the 'attachments' table exist in MySQL.
        Creates the database and the table if they do not exist.
        """
        try:
            cursor = self.mysql_conn.cursor()

            # Create the database if it doesn't exist
            db_name = 'cv_attachment'
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            log.info(f"Database '{db_name}' ensured to exist.")

            # Reconnect to the newly created database if necessary
            self.mysql_conn.database = db_name

            # Create the attachments table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attachments (
                    id VARCHAR(255) PRIMARY KEY,
                    pdf LONGBLOB NOT NULL
                )
            """)
            log.info("Ensured the 'attachments' table exists in MySQL.")
        except Error as e:
            log.error(f"Error ensuring attachments table exists in MySQL: {e}")
            raise RuntimeError(f"Error ensuring attachments table exists in MySQL: {e}")
        finally:
            cursor.close()




    def process_cvs_in_folder(self, pdf_folder):
        """
        Processes all PDF files in a folder and saves structured CVs to Azure Cosmos DB.
        """
        pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]

        for filename in pdf_files:
            try:
                log.info(f"Processing file: {filename}")
                pdf_path = os.path.join(pdf_folder, filename)
                extracted_text = self.extract_text_from_pdf(pdf_path)

                if not extracted_text.strip():
                    raise ValueError("No text extracted from PDF")

                # Ensure the cv_path is provided to the create_structured_cv function
                structured_cv = self.create_structured_cv(extracted_text, filename, pdf_path)

                if "error" in structured_cv:
                    raise ValueError(f"Error creating structured CV for file '{filename}'")

                log.info(f"Successfully processed and saved CV from file: {filename}")
            except Exception as e:
                log.warning(f"Warning or error encountered for file '{filename}': {e}. Moving to rejected folder.")
                self.process_and_move_rejected(pdf_path, str(e))





    def extract_text_from_pdf(self, pdf_path):
        """
        Extracts text from a PDF file, combining text from all pages.
        """
        try:
            log.info("Extracting text from PDF: %s", pdf_path)
            doc = fitz.open(pdf_path)
            text = "".join(page.get_text() for page in doc)
            doc.close()
            log.info("Successfully extracted text from PDF: %s", pdf_path)
            return text.strip()
        except Exception as e:
            log.error("Error extracting text from PDF %s: %s", pdf_path, e)
            raise RuntimeError(f"Error extracting text from PDF: {e}")
    
        
    


    def save_to_cosmos(self, content, cv_path):
        """
        Saves the structured CV content into Azure Cosmos DB, and the PDF content into MySQL database.

        Args:
            content (dict): The structured content to be saved.
            cv_path (str): The path of the CV file to be saved as binary in MySQL.
        """
        try:
            # Insert the CV content into the Cosmos DB container
            result = self.container.create_item(body=content)
            log.info(f"Successfully inserted CV into Azure Cosmos DB with ID: {result['id']}")

            # Save the CV PDF into MySQL database
            self.save_pdf_to_mysql(result['id'], cv_path)

        except Exception as e:
            log.error(f"Error inserting CV into Azure Cosmos DB: {e}")
            raise RuntimeError(f"Error saving CV to Azure Cosmos DB: {e}")


    def save_pdf_to_mysql(self, cv_id, pdf_path):
        """
        Saves the CV PDF as binary data into the MySQL attachments table.

        Args:
            cv_id (str): The ID of the CV to maintain a relational link with Cosmos DB.
            pdf_path (str): The path of the CV PDF file to save.
        """
        try:
            cursor = self.mysql_conn.cursor()

            # Check if the CV ID already exists in the MySQL table
            cursor.execute("SELECT COUNT(*) FROM attachments WHERE id = %s", (cv_id,))
            result = cursor.fetchone()
            if result[0] > 0:
                log.info(f"CV with ID '{cv_id}' already exists in MySQL. Skipping insertion to avoid duplicate.")
                return  # Skip insertion if record already exists

            # Insert the attachment into MySQL as binary
            with open(pdf_path, 'rb') as file:
                binary_data = file.read()

            cursor.execute("INSERT INTO attachments (id, pdf) VALUES (%s, %s)", (cv_id, binary_data))
            self.mysql_conn.commit()
            log.info(f"Successfully saved attachment for CV ID: {cv_id} into MySQL database.")
        except mysql.connector.Error as e:
            log.error(f"Failed to save attachment to MySQL: {e}")
            raise RuntimeError("Error saving attachment to MySQL database.")
        finally:
            cursor.close()






        



    def extract_username_from_url(self, github_url):
        """
        Extracts the GitHub username from a given profile URL.
        """
        log.info("Extracting GitHub username from URL: %s", github_url)
        match = re.match(r"https?://github\.com/([^/]+)/?", github_url)
        username = match.group(1) if match else None
        if username:
            log.debug("Extracted GitHub username: %s", username)
        else:
            log.warning("Unable to extract GitHub username from URL: %s", github_url)
        return username
    
    def extract_github_url(self, text):
        """
        Extracts the GitHub profile URL from the text.
        """
        log.info("Extracting GitHub URL from text")
        github_urls = re.findall(r'https?://github\.com/\S+', text)
        if github_urls:
            log.debug("Found GitHub URL: %s", github_urls[0].strip())
            return github_urls[0].strip()
        return None
    

    def sanitize_and_validate_json(self, response):
        """
        Sanitizes and validates the JSON-like response, ensuring proper key-value structure
        and valid JSON format.
        """
        try:
            # Step 1: Parse the input string as a JSON object (assuming it is valid JSON-like text)
            response_dict = json.loads(response)

            # Step 2: Validate and structure the parsed data
            structured_response = self.validate_and_structure_json(response_dict)

            # Step 3: Return the properly formatted and validated JSON
            return structured_response

        except json.JSONDecodeError as e:
            # If JSON decoding fails, log and raise an error
            raise ValueError(f"Error decoding JSON response: {e}")

        except Exception as e:
            # If any other error occurs during validation or sanitization
            raise ValueError(f"Error sanitizing and validating JSON: {e}")
    
    
    def validate_and_structure_json(self, data):
        """
        Recursively validate and structure JSON-like data, ensuring all keys are quoted
        and values are properly formatted. Keys with empty values (None, [], "", etc.) are ignored.
        """
        if isinstance(data, dict):
            # Recursively process each key-value pair in the dictionary
            structured_data = {}
            for key, value in data.items():
                # Ensure the key is quoted
                if not isinstance(key, str):
                    raise ValueError(f"Invalid key: {key} is not a string.")

                # Recursively handle the value
                validated_value = self.validate_and_structure_json(value)

                # Skip keys with empty values
                if validated_value not in (None, [], "","null", {}):
                    structured_data[key] = validated_value
            return structured_data

        elif isinstance(data, list):
            # Recursively validate each item in the list, ignoring empty values
            validated_list = [self.validate_and_structure_json(item) for item in data if item not in (None, [], "")]
            return validated_list if validated_list else None

        elif isinstance(data, str):
            # Return the string if it is not empty
            return data.strip() if data.strip() else None

        elif data is None:
            # Skip None values
            return None

        else:
            # Return other types (numbers, booleans, etc.) as is
            return data

    def call_anthropic(self, prompt, max_tokens=8000):
        """
        Calls the Anthropic Claude API with the given prompt and sanitizes the JSON response using the custom sanitizer.
        """
        try:
            # Log prompt length and warn if it's too long
            log.info("Calling Anthropic API with prompt of length %d characters", len(prompt))
            if len(prompt) > 20000:
                log.warning("Prompt length exceeds recommended size; truncating.")
                prompt = prompt[:20000] + "\n[Prompt truncated due to length.]"

            # Call the Anthropic API
            response = anthropic_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.2,
                system="Respond to the request and extract structured data.",
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            )

            # Combine response blocks into a single string
            full_response = "".join(block.text for block in response.content).strip()
            #log.debug("Full Anthropic API response:\n%s", full_response)  # Log first 500 characters for debugging

            # Apply custom sanitization for the response
            sanitized_json = self.sanitize_and_validate_json(full_response)
            log.info("Successfully sanitized and validated JSON response.")
            return sanitized_json

        except Exception as e:
            log.error("Error calling Anthropic API: %s", e)
            raise RuntimeError(f"Anthropic API call failed: {e}")
    

    def fetch_github_projects(self, github_url):
        """
        Fetches all public projects from the candidate's GitHub profile with detailed metadata.
        """
        if not github_url:
            log.warning("No GitHub URL provided; skipping project fetching.")
            return []

        username = self.extract_username_from_url(github_url)
        if not username:
            log.warning("No GitHub username extracted; skipping project fetching.")
            return []

        log.info("Fetching GitHub projects for user: %s", username)
        api_url = f"https://api.github.com/users/{username}/repos"
        headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}", "Accept": "application/vnd.github.v3+json"}
        projects = []
        page = 1

        while True:
            try:
                response = requests.get(api_url, headers=headers, params={"page": page, "per_page": 100})
                if response.status_code != 200:
                    log.error("Failed to fetch GitHub repos: %s", response.text)
                    break

                repos = response.json()
                if not repos:
                    log.info("No more repositories found for user: %s", username)
                    break

                for repo in repos:
                    projects.append({
                        "repository_name": repo.get("name"),
                        "description": repo.get("description") or "No description provided",
                        "repository_url": repo.get("html_url"),
                    })
                page += 1
            except Exception as e:
                log.error("Error while fetching GitHub projects: %s", e)
                break

        log.info("Total GitHub projects fetched: %d", len(projects))
        return projects

    


    def create_structured_cv(self, extracted_text, filename, cv_path):
        """
        Generates a structured CV and saves it to Azure Cosmos DB.

        Args:
            extracted_text (str): The extracted text from the CV PDF.
            filename (str): The name of the file being processed.
            cv_path (str): The file path to the actual CV being processed.

        Returns:
            dict: The structured CV or an error message.
        """
        if not extracted_text.strip():
            log.warning(f"Extracted text is empty for file '{filename}'. Skipping processing.")
            self.process_and_move_rejected(cv_path, "Empty CV text")
            return {"error": "Empty CV text"}

        # Extract GitHub URL and fetch public projects if available
        github_url = self.extract_github_url(extracted_text)
        github_projects = self.fetch_github_projects(github_url) if github_url else []

        # Prepare the prompt for the API call, ensuring GitHub projects are always included as JSON.
        prompt = get_create_structured_cv_prompt_template_text().format(
            extracted_text=extracted_text,
            github_projects_text=json.dumps(github_projects, ensure_ascii=False, indent=2) if github_projects else "[]"
        )

        log.info("Creating structured CV from extracted text")
        try:
            response = self.call_anthropic(prompt)
            if not response or "error" in response:
                log.warning(f"Skipping invalid CV after processing: '{filename}'")
                self.process_and_move_rejected(cv_path, "Invalid CV format")
                return {"error": "Invalid CV data"}

            # Generate or use existing CV ID to maintain a relational link
            cv_id = response.get('id', str(uuid4()))
            response['id'] = cv_id

            # Save the structured CV to Cosmos DB
            try:
                self.save_to_cosmos(response, cv_path)
            except Exception as e:
                log.error(f"Failed to save CV to Cosmos DB: {e}")
                self.process_and_move_rejected(cv_path, "Failed to save CV to Cosmos DB")
                return {"error": "Error saving CV to Cosmos DB"}

            # Save the CV attachment to MySQL
            try:
                self.save_pdf_to_mysql(cv_id, cv_path)
            except Exception as e:
                log.error(f"Failed to save attachment to MySQL: {e}")
                # Removing from Cosmos DB to maintain consistency if saving in MySQL fails
                self.container.delete_item(item=cv_id, partition_key=cv_id)
                self.process_and_move_rejected(cv_path, "Failed to save attachment to MySQL")
                return {"error": "Error saving attachment to MySQL"}

            log.info(f"Successfully processed and saved CV from file: {filename}")
            return response

        except Exception as e:
            log.error(f"Error creating structured CV for file '{filename}': {e}")
            self.process_and_move_rejected(cv_path, str(e))
            return {"error": f"Structured CV creation failed: {str(e)}"}




        



    def process_and_move_rejected(self, file_path, error_msg=None):
        """
        Move CV to the rejected folder if any issues or warnings occur during processing.

        Args:
            file_path (str): The path of the file to move.
            error_msg (str): The error message describing why the file was rejected.
        """
        rejected_folder = "src/data/cv/Rejected formats CVs"
        if not os.path.exists(rejected_folder):
            log.info(f"Rejected folder does not exist. Creating directory: {rejected_folder}")
        os.makedirs(rejected_folder, exist_ok=True)  # Ensure the folder exists before moving files

        try:
            rejected_path = os.path.join(rejected_folder, os.path.basename(file_path))
            shutil.move(file_path, rejected_path)
            log.warning(f"Moved rejected file '{file_path}' to {rejected_folder} due to error: {error_msg}")
        except Exception as e:
            log.error(f"Failed to move rejected file '{file_path}' due to: {e}")














 





if __name__ == "__main__":
    log.info("Starting CV processing pipeline.")

    try:
        processor = CVProcessor()
        dataTools = DataTool()
    except Exception as e:
        log.critical(f"Initialization failed: {e}")
        raise

    folder_path = "src/data/cv"

    try:
        log.info("Converting .doc files to .pdf...")
        dataTools.convert_doc_to_pdf(folder_path)
        log.info("Conversion completed.")
    except Exception as e:
        log.error(f"Conversion error: {e}")

    try:
        log.info("Processing PDFs for structured CV generation...")
        processor.process_cvs_in_folder(folder_path)
        log.info("PDF processing completed.")
    except Exception as e:
        log.error(f"Processing error: {e}")

    log.info("Pipeline execution finished.")


