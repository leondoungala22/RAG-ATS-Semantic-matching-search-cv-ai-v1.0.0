import os
from win32com import client
from utils.logger import get_logger


log = get_logger("DataTool")


class DataTool:
    def __init__(self):
        """
        Initialize DataTool for handling file operations.
        """
        log.info("DataTool initialized.")

    @staticmethod
    def convert_doc_to_pdf(folder):
        """
        Converts .doc, .DOC, and .docx files to .pdf in the given folder.

        Args:
            folder (str): Path to the folder containing .doc and .docx files.
        """
        log.info(f"Scanning folder: {folder} for .doc, .DOC, and .docx files...")
        # Create output folder if it doesn't exist
        if not os.path.exists(folder):
            os.makedirs(folder)

        # Initialize Word application
        word = client.Dispatch("Word.Application")
        word.Visible = False

        try:
            for filename in os.listdir(folder):
                # Process .doc, .DOC, and .docx files
                if filename.lower().endswith((".doc", ".docx")):
                    input_path = os.path.abspath(os.path.join(folder, filename))
                    output_path = os.path.abspath(os.path.join(folder, f"{os.path.splitext(filename)[0]}.pdf"))

                    if os.path.getsize(input_path) == 0:
                        # Delete empty file
                        os.remove(input_path)
                        log.warning(f"Deleted empty file: {input_path}")
                        continue

                    if not os.path.exists(input_path):
                        log.warning(f"File not found: {input_path}")
                        continue

                    try:
                        # Open Word document
                        doc = word.Documents.Open(input_path)

                        # Save as PDF
                        doc.SaveAs(output_path, FileFormat=17)  # 17 is the PDF format in Word
                        doc.Close()

                        log.info(f"Converted: {input_path} -> {output_path}")

                        # Remove the original file after successful conversion
                        os.remove(input_path)
                        log.info(f"Deleted original file: {input_path}")
                    except Exception as file_error:
                        log.error(f"Failed to convert {input_path}: {file_error}")
        except Exception as e:
            log.error(f"General error during conversion: {e}")
        finally:
            word.Quit()
