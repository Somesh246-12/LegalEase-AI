from flask import Flask, render_template, request, jsonify, Response, session
import os
import json
from google.oauth2 import service_account
from google.auth import default as google_auth_default
from google.cloud import documentai

from legal_analyzer import (
    summarize_text,
    get_chatbot_response,
    analyze_risks,
    render_risks_html,
    compute_risk_stats,
    rewrite_clause,
    risks_to_csv,
    risks_to_html,
    risks_to_pdf_bytes,
    is_legal_document,  # pyright: ignore[reportUnusedImport]
    check_document_authenticity
)

# --- NEW, MORE ROBUST CREDENTIALS LOGIC ---
# This new section can handle credentials from a local file OR a secure environment variable.
credentials = None

# 1. First, try to load credentials from the environment variable (for Render)
creds_json_str = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
if creds_json_str:
    try:
        creds_info = json.loads(creds_json_str)
        credentials = service_account.Credentials.from_service_account_info(creds_info)
        print("Successfully loaded credentials from environment variable.")
    except Exception as e:
        print(f"Error loading credentials from environment variable: {e}")

# 2. If that fails, try loading from the local credentials.json file (for local development)
if not credentials:
    try:
        credentials = service_account.Credentials.from_service_account_file("credentials.json")
        print("Successfully loaded credentials from local file.")
    except Exception:
        pass

# 3. As a final fallback, try Application Default Credentials (for Google Cloud Run)
if not credentials:
    try:
        credentials, _ = google_auth_default()
        print("Successfully loaded credentials using Application Default Credentials.")
    except Exception:
        print("Could not load credentials from any source.")
# --------------------------------------------------------------------------


# --- Configuration ---
PROJECT_ID = "legalease-ai-471416"
DOCAI_LOCATION = "eu"
DOCAI_PROCESSOR_ID = "3c22ed109a51b5e9" # Make sure this is your Document OCR Processor ID
# -----------------------------------------------

app = Flask(__name__)
app.secret_key = os.urandom(24)

def process_document_with_docai(file_content, mime_type):
    """Processes a document using Document AI."""
    opts = {"api_endpoint": f"{DOCAI_LOCATION}-documentai.googleapis.com"}
    client = documentai.DocumentProcessorServiceClient(client_options=opts, credentials=credentials)
    name = client.processor_path(PROJECT_ID, DOCAI_LOCATION, DOCAI_PROCESSOR_ID)
    raw_document = documentai.RawDocument(content=file_content, mime_type=mime_type)
    
    # --- The imageless mode logic has been removed from this section ---
    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document,
    )
    result = client.process_document(request=request)
    return result.document.text

# ... (The rest of your app.py file is the same) ...

@app.route("/", methods=["GET", "POST"])
def index():
    html_result = None
    original_text = ""
    risk_html = None
    warning_message = None

    if request.method == "POST":
        selected_language = request.form.get("target_language", "English")
        text_to_analyze = ""
        uploaded_file = request.files.get('pdf_file')
        pasted_text = request.form.get("legal_text", "")

        try:
            if uploaded_file and uploaded_file.filename != '':
                file_content = uploaded_file.read()
                mime_type = uploaded_file.mimetype
                text_to_analyze = process_document_with_docai(file_content, mime_type)
            elif pasted_text:
                text_to_analyze = pasted_text
            
            original_text = text_to_analyze

            if text_to_analyze:

                if not is_legal_document(text_to_analyze):
                    warning_message = "This does not appear to be a legal document. The analysis may be less accurate, but here is our best effort:"
                html_result = summarize_text(text_to_analyze, target_language=selected_language)
                risks = analyze_risks(text_to_analyze, target_language=selected_language)
                risk_html = render_risks_html(risks, target_language=selected_language)
                session['risks'] = risks
                session['risk_language'] = selected_language
            else:
                 html_result = "<p style='color: #ffcc00;'>Please paste text or upload a file to analyze.</p>"

        except Exception as e:
            html_result = f"<p style='color: #ff6b6b;'><b>Error:</b> Could not process the document. Details: {e}</p>"

    return render_template("index.html", result=html_result, original_text=original_text, risk_html=risk_html, warning_message=warning_message)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    history = data.get("history")
    document_text = data.get("document_text", "")

    if not history:
        return {"response": "An error occurred. No history received."}, 400
    
    bot_response = get_chatbot_response(history, document_text)
    return {"response": bot_response}

@app.route("/risks.json")
def risks_json():
    risks = session.get('risks', [])
    stats = compute_risk_stats(risks) if risks else {"severity": {}, "type": {}}
    return jsonify({"risks": risks, "stats": stats})

@app.route("/rewrite", methods=["POST"])
def rewrite():
    data = request.get_json(silent=True) or {}
    clause = data.get("clause", "")
    mode = data.get("mode", "plain")
    language = data.get("language", session.get('risk_language', 'English'))
    if not clause.strip():
        return jsonify({"error": "No clause provided"}), 400
    safer = rewrite_clause(clause, target_language=language, mode=mode)
    return jsonify({"rewrite": safer})

@app.route("/export.csv")
def export_csv():
    risks = session.get('risks', [])
    csv_str = risks_to_csv(risks)
    return Response(
        csv_str,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=risks.csv"}
    )

@app.route("/export.html")
def export_html():
    risks = session.get('risks', [])
    language = session.get('risk_language', 'English')
    html_doc = risks_to_html(risks, target_language=language)
    return Response(
        html_doc,
        mimetype='text/html',
        headers={"Content-Disposition": "attachment; filename=risks.html"}
    )

@app.route("/export.pdf")
def export_pdf():
    risks = session.get('risks', [])
    language = session.get('risk_language', 'English')
    pdf_bytes = risks_to_pdf_bytes(risks, target_language=language)
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={"Content-Disposition": "attachment; filename=risks.pdf"}
    )


@app.route("/check-authenticity", methods=["POST"])
def check_authenticity():
    """
    A new endpoint that only performs the authenticity check.
    """
    text_to_analyze = ""
    uploaded_file = request.files.get('pdf_file')
    pasted_text = request.form.get("legal_text", "")

    try:
        if uploaded_file and uploaded_file.filename != '':
            file_content = uploaded_file.read()
            mime_type = uploaded_file.mimetype
            text_to_analyze = process_document_with_docai(file_content, mime_type)
        elif pasted_text:
            text_to_analyze = pasted_text

        if text_to_analyze:
            report = check_document_authenticity(text_to_analyze)
            return jsonify(report)
        else:
            # If no text, return a generic "safe" report to avoid blocking the user
            return jsonify({ "confidence_score": 100, "summary": "No text provided.", "findings": [] })

    except Exception as e:
        print(f"Error in authenticity check endpoint: {e}")
        return jsonify({"error": "Failed to process document for authenticity check."}), 500

        
if __name__ == "__main__":
    app.run(debug=True)

