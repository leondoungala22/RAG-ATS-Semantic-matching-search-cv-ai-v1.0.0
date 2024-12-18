import os
import io
import sys
import base64
import yaml
import logging as log
from flask import Flask, request, render_template, send_file, jsonify
from retriever.helper_retriever import CVRetrieverApp

# Get the absolute path of the project's root directory (relative to this file)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the project root to the Python path
if project_root not in sys.path:
    sys.path.append(project_root)

# Initialize Flask app
app = Flask(__name__)

# Create an instance of CVRetrieverApp
cv_retriever = CVRetrieverApp()

@app.route('/')
def index():
    """
    Render the main search page with an empty result set.. 
    """
    return render_template('index.html', has_results=False, results=[])

@app.route('/search', methods=['POST'])
def search():
    """
    Handle the search request, perform similarity search, and display results.
    """
    # Get job description from the form
    job_description = request.form.get('job_description')

    if job_description:
        # Perform similarity search
        filtered_results = cv_retriever.perform_similarity_search(job_description)

        # Prepare results for rendering
        results = []
        if filtered_results:
            for result in filtered_results:
                document_id = result['id']
                score = result.get('score', 'N/A')

                # Query the full document by ID
                document = cv_retriever.query_document_by_id(document_id)
                if document:
                    formatted_cv = cv_retriever.format_document_dynamically(document)
                    try:
                        # Parse formatted CV as a dictionary
                        formatted_cv_dict = yaml.safe_load(formatted_cv)
                    except yaml.YAMLError as e:
                        app.logger.error(f"Failed to parse formatted CV for document_id {document_id}: {e}")
                        continue

                    # Get the original CV (PDF) from MySQL
                    attached_cv = cv_retriever.get_candidate_cv(document_id)

                    results.append({
                        'id': document_id,  # Add 'id' for compatibility
                        'document_id': document_id,
                        'similarity_score': score,
                        'formatted_cv': formatted_cv_dict,
                        'attached_cv': attached_cv
                    })

        # Pass results to display_results for debugging
        cv_retriever.display_results(results)

        # Render results in the template
        return render_template('index.html', results=results, has_results=bool(results))
    else:
        # Return an error message if no job description is provided
        return render_template('index.html', error="Please provide a job description.", has_results=False, results=[])

@app.route('/view_cv/<candidate_id>')
def view_cv(candidate_id):
    """
    Serve the original CV as a PDF file for the specified candidate ID.
    """
    try:
        attached_cv_base64 = cv_retriever.get_candidate_cv(candidate_id)
        if not attached_cv_base64:
            return "No CV found for the provided ID", 404

        # Decode the base64 string back to bytes
        attached_cv_bytes = base64.b64decode(attached_cv_base64)

        # Send the PDF file as response
        return send_file(io.BytesIO(attached_cv_bytes), mimetype='application/pdf', as_attachment=False, download_name='attached_cv.pdf')
    except Exception as e:
        app.logger.error(f"Error viewing CV: {e}")
        return "An error occurred while processing the CV.", 500

@app.route('/api/getCandidateData/<document_id>', methods=['GET'])
def get_candidate_data(document_id):
    """
    Fetch candidate data by document_id from NoSQL and return it in the desired format.
    """
    try:
        # Query the document by its ID
        app.logger.info(f"Fetching candidate data for document_id {document_id}...")
        document = cv_retriever.query_document_by_id(document_id)
        
        if document:
            # Format the document dynamically
            app.logger.info(f"Formatting CV for document_id {document_id}...")
            formatted_cv = cv_retriever.format_document_dynamically(document)
            
            # Parse the formatted CV if needed (assuming it's in YAML format)
            try:
                formatted_cv_dict = yaml.safe_load(formatted_cv)
                app.logger.info(f"Formatted CV dict for document_id {document_id}: \n{formatted_cv_dict}")
                
                # Create the response object
                response = jsonify(formatted_cv_dict)
                
                # Log the response
                app.logger.info(f"Returning response for document_id {document_id}: {response.get_json()}")
                
                return response  # Return the formatted CV as JSON
            except yaml.YAMLError as e:
                app.logger.error(f"Failed to parse formatted CV for document_id {document_id}: {e}")
                response = jsonify({"error": "Error parsing CV"})
                app.logger.info(f"Returning error response for document_id {document_id}: {response.get_json()}")
                return response
        else:
            app.logger.warning(f"Candidate with document_id {document_id} not found.")
            response = jsonify({"error": "Candidate not found"})
            app.logger.info(f"Returning error response for document_id {document_id}: {response.get_json()}")
            return response
    except Exception as e:
        app.logger.error(f"Error fetching candidate data for document_id {document_id}: {e}")
        response = jsonify({"error": "Error fetching candidate data"})
        app.logger.info(f"Returning error response for document_id {document_id}: {response.get_json()}")
        return response



if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
