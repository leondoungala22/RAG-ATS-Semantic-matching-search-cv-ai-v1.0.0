import os
import sys

# Get the absolute path of the project's root directory (relative to this file)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the project root to the Python path
if project_root not in sys.path:
    sys.path.append(project_root)

import json
import fitz  # PyMuPDF for PDF text extraction
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
from utils.logger import get_logger
from uuid import uuid4
import shutil

# Load environment variables
load_dotenv()
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Configure logging
log = get_logger("CVProcessor")

# Local storage paths
LOCAL_JSON_STORAGE = "src/data/cv_json"
REJECTED_FOLDER = "src/data/cv_rejected"

# Ensure directories exist
os.makedirs(LOCAL_JSON_STORAGE, exist_ok=True)
os.makedirs(REJECTED_FOLDER, exist_ok=True)


class CVProcessor:
    def __init__(self, model="claude-3-5-haiku-20241022"):
        """
        Initializes the CVProcessor with the specified Anthropic Claude model.
        """
        self.model = model
        log.info("CVProcessor initialized with model: %s", model)

    def process_cvs_in_folder(self, pdf_folder):
        """
        Processes all PDF files in a folder and saves structured CVs as JSON files locally.
        """
        pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
        
        log.info(f"Found {len(pdf_files)} PDF files in {pdf_folder}: {pdf_files}")

        if not pdf_files:
            log.warning("No PDF files found. Please check the folder path and file extensions.")

        for filename in pdf_files:
            try:
                log.info(f"Processing file: {filename}")
                pdf_path = os.path.join(pdf_folder, filename)
                extracted_text = self.extract_text_from_pdf(pdf_path)

                if not extracted_text.strip():
                    raise ValueError("No text extracted from PDF")

                structured_cv = self.create_structured_cv(extracted_text, filename, pdf_path)

                if "error" in structured_cv:
                    raise ValueError(f"Error creating structured CV for file '{filename}'")

                log.info(f"Successfully processed and saved CV from file: {filename}")

            except Exception as e:
                log.warning(f"Error with file '{filename}': {e}. Moving to rejected folder.")
                self.process_and_move_rejected(pdf_path, str(e))

    def extract_text_from_pdf(self, pdf_path):
        """
        Extracts text from a PDF file.
        """
        try:
            log.info(f"Extracting text from PDF: {pdf_path}")
            doc = fitz.open(pdf_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            
            log.info(f"Extracted {len(text)} characters from {pdf_path}")

            if not text.strip():
                log.warning(f"No text extracted from {pdf_path}. The PDF might be a scanned document.")

            return text.strip()
        except Exception as e:
            log.error(f"Error extracting text from PDF {pdf_path}: {e}")
            raise RuntimeError(f"Error extracting text from PDF: {e}")

    def create_structured_cv(self, extracted_text, filename, pdf_path):
        """
        Calls Anthropic AI to generate a structured CV and saves it locally as JSON.
        """
        log.info(f"Creating structured CV for {filename}")

        if not extracted_text.strip():
            log.warning(f"Extracted text is empty for '{filename}'. Skipping processing.")
            self.process_and_move_rejected(pdf_path, "Empty CV text")
            return {"error": "Empty CV text"}

        prompt = f"Extract structured CV information from the following text:\n\n{extracted_text[:500]}"  # First 500 chars only

        log.info("Sending prompt to Anthropic API...")
        try:
            response = self.call_anthropic(prompt)

            if not response or "error" in response:
                self.process_and_move_rejected(pdf_path, "Invalid CV format")
                return {"error": "Invalid CV data"}

            # Generate or use existing CV ID
            cv_id = response.get('id', str(uuid4()))
            response['id'] = cv_id

            # Save the structured CV locally
            self.save_json_locally(response, filename)

            log.info(f"Structured CV saved successfully for {filename}")

            return response

        except Exception as e:
            log.error(f"Error creating structured CV: {e}")
            self.process_and_move_rejected(pdf_path, str(e))
            return {"error": f"Error: {e}"}

    def call_anthropic(self, prompt):
        """
        Calls the Anthropic Claude API with the given prompt.
        """
        try:
            response = anthropic_client.messages.create(
                model=self.model,
                max_tokens=8000,
                temperature=0.2,
                system="Extract structured data.",
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            )

            return json.loads(response.content[0].text)
        except Exception as e:
            log.error(f"Anthropic API call failed: {e}")
            return {"error": str(e)}

    def save_json_locally(self, content, filename):
        """
        Saves structured CV data as a JSON file in a local folder.
        """
        try:
            json_path = os.path.join(LOCAL_JSON_STORAGE, f"{filename}.json")
            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(content, json_file, ensure_ascii=False, indent=4)

            log.info(f"Saved structured CV to {json_path}")

        except Exception as e:
            log.error(f"Failed to save JSON for {filename}: {e}")
            raise RuntimeError(f"Error saving JSON file: {e}")

    def process_and_move_rejected(self, file_path, error_msg=None):
        """
        Move CV to the rejected folder if processing fails.

        Args:
            file_path (str): The path of the file to move.
            error_msg (str): The error message describing why the file was rejected.
        """
        try:
            rejected_path = os.path.join(REJECTED_FOLDER, os.path.basename(file_path))
            shutil.move(file_path, rejected_path)
            log.warning(f"Moved rejected file '{file_path}' to {REJECTED_FOLDER}: {error_msg}")
        except Exception as e:
            log.error(f"Failed to move rejected file '{file_path}': {e}")


if __name__ == "__main__":
    log.info("Starting CV processing pipeline.")

    try:
        processor = CVProcessor()
    except Exception as e:
        log.critical(f"Initialization failed: {e}")
        raise

    folder_path = "src/data/cv"

    try:
        log.info("Processing PDFs for structured CV generation...")
        processor.process_cvs_in_folder(folder_path)
        log.info("PDF processing completed.")
    except Exception as e:
        log.error(f"Processing error: {e}")

    log.info("Pipeline execution finished.")
