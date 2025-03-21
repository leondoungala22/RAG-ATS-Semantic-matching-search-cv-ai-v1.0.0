import os
import io
from flask import Flask, request, render_template, jsonify, send_file, make_response
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from retriever.helper_retriever import HelperRetriever, VectorStoreManager
from utils.db import get_connection
import config

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "tmp_uploads"
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load vector store using the shared VectorStoreManager.
vectorstore = VectorStoreManager.load_existing_vector_store()
if not vectorstore:
    raise Exception("Vector store could not be loaded.")
retriever = HelperRetriever(vectorstore, threshold=0.65)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    job_description = ""
    # Textarea input
    if request.form.get("job_text"):
        job_description = request.form["job_text"]

    # File upload
    file = request.files.get("job_file")
    if file and file.filename.endswith(".txt"):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            job_description = f.read()

    if not job_description:
        return jsonify({"error": "No job description provided."}), 400

    results = retriever.perform_search(job_description)
    filtered = retriever.rerank_with_openai(job_description, results)

    response_data = []
    for r in filtered:
        # Remove path and file extension from the Chroma document ID.
        uuid_name = os.path.splitext(os.path.basename(r["id"]))[0]
        response_data.append({
            "uuid": uuid_name,
            "score": round(r["score"], 4),
            "reason": r.get("reason", "N/A")
        })

    return jsonify(response_data)


@app.route("/attachment/<uuid>")
def get_attachment(uuid):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT filename, pdf FROM cv_attachment
            WHERE id::text = %s OR filename = %s OR filename = %s
        """, (uuid, uuid, f"{uuid}.json"))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            filename, pdf_bytes = result
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype="application/pdf",
                download_name=filename,
                as_attachment=False
            )
        else:
            return make_response("❌ No PDF found for this CV.", 404)
    except Exception as e:
        return make_response(f"❌ Error retrieving CV PDF: {e}", 500)


if __name__ == "__main__":
    app.run(debug=True)
