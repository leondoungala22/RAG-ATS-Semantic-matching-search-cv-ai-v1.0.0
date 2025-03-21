from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)


from src.utils.logger import get_logger
from retriever.helper_retriever import HelperRetriever, load_existing_vector_store

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Load vectorstore once at app start
vectorstore = load_existing_vector_store()
retriever = HelperRetriever(vectorstore, threshold=0.65)

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    job_description = ""

    # Option 1: Text area input
    if request.form.get("job_text"):
        job_description = request.form["job_text"]

    # Option 2: File upload
    file = request.files.get("job_file")
    if file and file.filename.endswith(".txt"):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            job_description = f.read()

    if not job_description:
        return jsonify({"error": "No job description provided."}), 400

    # Run retrieval
    results = retriever.perform_search(job_description)
    filtered = retriever.rerank_with_openai(job_description, results)

    # Structure data for frontend
    data = [{
        "id": r["id"],
        "score": round(r["score"], 4),
        "reason": r["reason"]
    } for r in filtered]

    return jsonify(data)

@app.route("/cv/<path:cv_id>")
def view_cv(cv_id):
    # Returns full original CV content as plain text (or JSON)
    try:
        content = retriever.query_by_id(cv_id)
        return content or "CV not found."
    except Exception as e:
        return f"Error loading CV: {e}", 500

if __name__ == "__main__":
    app.run(debug=True)
