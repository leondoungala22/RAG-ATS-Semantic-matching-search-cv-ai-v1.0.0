import os
import sys
import json
import psycopg2
import fitz  # PyMuPDF
import uuid
import shutil
import logging
from dotenv import load_dotenv
from pdf2image import convert_from_path
import easyocr
import numpy as np
from PIL import Image

# Load environment variables
load_dotenv()

# PostgreSQL Credentials
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")

if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB]):
    raise ValueError("❌ Missing PostgreSQL environment variables. Check your .env file.")

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("CVProcessor")

class CVProcessor:
    def __init__(self):
        """
        Initializes the CVProcessor and ensures PostgreSQL connectivity.
        """
        log.info("🚀 Initializing CVProcessor...")

        try:
            self.pg_conn = psycopg2.connect(
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                host=POSTGRES_HOST,
                port=POSTGRES_PORT
            )
            self.ensure_attachments_table_exists()
            log.info("✅ Successfully connected to PostgreSQL.")
        except Exception as e:
            log.critical(f"❌ PostgreSQL connection failed: {e}")
            raise RuntimeError("Database connection failed.")

    def ensure_attachments_table_exists(self):
        """
        Ensures the 'attachments' table exists in PostgreSQL.
        """
        try:
            cursor = self.pg_conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cv_attachment (
                    id UUID PRIMARY KEY,
                    filename TEXT NOT NULL,
                    pdf BYTEA NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            self.pg_conn.commit()
            cursor.close()
            log.info("✅ PostgreSQL table 'cv_attachment' ensured to exist.")
        except Exception as e:
            log.error(f"❌ Error ensuring PostgreSQL table exists: {e}")
            raise

    def process_cvs_in_folder(self, pdf_folder):
        """
        Processes all PDF files in a given folder.
        """
        pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]

        for filename in pdf_files:
            try:
                log.info(f"📄 Processing file: {filename}")
                pdf_path = os.path.join(pdf_folder, filename)
                extracted_text = self.extract_text_from_pdf(pdf_path)

                if not extracted_text.strip():
                    raise ValueError("No text extracted from PDF")

                structured_cv = self.create_structured_cv(extracted_text, filename, pdf_path)

                if "error" in structured_cv:
                    raise ValueError(f"Error creating structured CV for file '{filename}'")

                log.info(f"✅ Successfully processed and saved CV from file: {filename}")
            except Exception as e:
                log.warning(f"⚠️ Error with file '{filename}': {e}. Moving to rejected folder.")
                self.process_and_move_rejected(pdf_path, str(e))

    def extract_text_from_pdf(self, pdf_path):
        """
        Extracts text from a PDF file, combining text from all pages.
        Uses both text extraction and OCR if needed.
        """
        try:
            log.info(f"🔍 Extracting text from PDF: {pdf_path}")
            reader = easyocr.Reader(["en"])  
            doc = fitz.open(pdf_path)
            text = ""

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()

                if page_text.strip():
                    text += page_text
                else:
                    log.warning(f"⚠️ No text found on page {page_num + 1}. Attempting OCR.")
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = reader.readtext(np.array(img), detail=0)
                    text += " ".join(ocr_text)

            doc.close()

            if not text.strip():
                raise ValueError("No text extracted from PDF")

            log.info(f"✅ Successfully extracted text from PDF: {pdf_path}")
            return text.strip()

        except Exception as e:
            log.error(f"❌ Error extracting text from PDF {pdf_path}: {e}")
            raise RuntimeError(f"Error extracting text from PDF: {e}")

    def save_pdf_to_postgres(self, cv_id, pdf_path):
        """
        Saves the CV PDF as binary data into PostgreSQL.
        """
        try:
            cursor = self.pg_conn.cursor()
            with open(pdf_path, 'rb') as file:
                binary_data = file.read()

            cursor.execute(
                "INSERT INTO cv_attachment (id, filename, pdf) VALUES (%s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING;",
                (cv_id, os.path.basename(pdf_path), psycopg2.Binary(binary_data))
            )
            self.pg_conn.commit()
            cursor.close()
            log.info(f"✅ CV PDF saved in PostgreSQL for ID: {cv_id}")

        except Exception as e:
            log.error(f"❌ Failed to save attachment to PostgreSQL: {e}")
            raise RuntimeError("Error saving CV PDF to PostgreSQL.")

    def save_json_locally(self, cv_id, content):
        """
        Saves the structured CV as a JSON file locally in `src/data/cv_json/`.
        """
        try:
            json_dir = "src/data/cv_json"
            os.makedirs(json_dir, exist_ok=True)
            json_path = os.path.join(json_dir, f"{cv_id}.json")

            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(content, json_file, ensure_ascii=False, indent=4)

            log.info(f"✅ Structured CV saved locally at {json_path}")

        except Exception as e:
            log.error(f"❌ Error saving JSON locally: {e}")

    def create_structured_cv(self, extracted_text, filename, cv_path):
        """
        Generates a structured CV and saves it to PostgreSQL and local storage.
        """
        if not extracted_text.strip():
            log.warning(f"⚠️ Extracted text is empty for file '{filename}'. Skipping processing.")
            self.process_and_move_rejected(cv_path, "Empty CV text")
            return {"error": "Empty CV text"}

        try:
            # Generate unique CV ID
            cv_id = str(uuid.uuid4())

            structured_cv = {
                "id": cv_id,
                "filename": filename,
                "text": extracted_text
            }

            # Save JSON locally
            self.save_json_locally(cv_id, structured_cv)

            # Save PDF to PostgreSQL
            self.save_pdf_to_postgres(cv_id, cv_path)

            log.info(f"✅ Successfully processed and saved CV: {filename}")
            return structured_cv

        except Exception as e:
            log.error(f"❌ Error creating structured CV for file '{filename}': {e}")
            self.process_and_move_rejected(cv_path, str(e))
            return {"error": f"Structured CV creation failed: {str(e)}"}

    def process_and_move_rejected(self, file_path, error_msg):
        """
        Move rejected CVs to `cv_rejected/` folder.
        """
        rejected_folder = "src/data/cv_rejected"
        os.makedirs(rejected_folder, exist_ok=True)

        try:
            shutil.move(file_path, os.path.join(rejected_folder, os.path.basename(file_path)))
            log.warning(f"⚠️ Moved rejected file '{file_path}' to {rejected_folder} due to error: {error_msg}")
        except Exception as e:
            log.error(f"❌ Failed to move rejected file '{file_path}': {e}")

if __name__ == "__main__":
    log.info("🚀 Starting CV processing pipeline.")
    processor = CVProcessor()
    processor.process_cvs_in_folder("src/data/cv")
    log.info("✅ Pipeline execution finished.")
