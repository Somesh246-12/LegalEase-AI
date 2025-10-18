from flask import Flask, render_template, request, jsonify, Response, session
import os
import json
from google.oauth2 import service_account
from google.auth import default as google_auth_default
from google.cloud import documentai
from concurrent.futures import ThreadPoolExecutor

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
    check_document_authenticity,
    check_page_limit,
    check_document_logos,
    check_document_blur
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
            # Step 1: Extract text from the document (this remains sequential)
            if uploaded_file and uploaded_file.filename != '':
                file_content = uploaded_file.read()
                mime_type = uploaded_file.mimetype
                
                # Check page limit first
                page_limit_result = check_page_limit(file_content, mime_type)
                if page_limit_result['exceeds_limit']:
                    warning_message = f"📄 {page_limit_result['message']} {page_limit_result['recommendation']}"
                    return render_template("index.html", result=None, original_text="", risk_html=None, warning_message=warning_message)
                
                text_to_analyze = process_document_with_docai(file_content, mime_type)
            elif pasted_text:
                text_to_analyze = pasted_text
            
            original_text = text_to_analyze

            if text_to_analyze:
                # Step 2: Run the quick legal document check first
                if not is_legal_document(text_to_analyze):
                    warning_message = "This does not appear to be a legal document. The analysis may be less accurate, but here is our best effort:"

                # --- NEW PARALLEL EXECUTION BLOCK ---
                # Step 3: Run the two slow AI tasks (summary and risks) at the same time
                with ThreadPoolExecutor() as executor:
                    # Submit both functions to the executor to run concurrently
                    summary_future = executor.submit(summarize_text, text_to_analyze, selected_language)
                    risks_future = executor.submit(analyze_risks, text_to_analyze, selected_language)

                # Step 4: Wait for both tasks to finish and get their results
                html_result = summary_future.result()
                risks = risks_future.result()
                # --- END OF PARALLEL BLOCK ---

                # Step 5: Proceed with the now-completed results
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
    A multi-stage pre-check endpoint.
    1. Checks Page Limit
    2. NEW: Checks for Blurriness
    3. Checks Authenticity
    """
    text_to_analyze = ""
    file_content = None
    mime_type = None
    
    uploaded_file = request.files.get('pdf_file')
    pasted_text = request.form.get("legal_text", "")

    try:
        if uploaded_file and uploaded_file.filename != '':
            file_content = uploaded_file.read()
            mime_type = uploaded_file.mimetype
            
            # --- CHECK 1: PAGE LIMIT (Existing) ---
            page_limit_result = check_page_limit(file_content, mime_type)
            if page_limit_result['exceeds_limit']:
                return jsonify({
                    "verdict": "PAGE_LIMIT_EXCEEDED",
                    "summary": page_limit_result['message'],
                    "confidence_score": 100,
                    "page_details": page_limit_result
                })
            
            # --- NEW CHECK 2: BLUR ---
            # Run the blur check on the raw file content
            blur_check = check_document_blur(file_content, mime_type)
            if blur_check["is_blurry"]:
                return jsonify({
                    "verdict": "BLURRY",
                    "summary": blur_check["summary"],
                    "confidence_score": 100, # Use 100 as a strong signal
                    "blur_details": blur_check
                })
            
            # --- IF CHECKS PASS, GET TEXT FOR AUTHENTICITY ---
            text_to_analyze = process_document_with_docai(file_content, mime_type)
        
        elif pasted_text:
            text_to_analyze = pasted_text

        # --- CHECK 3: AUTHENTICITY (Existing) ---
        if text_to_analyze:
            # Pass file content for logo analysis
            file_content_for_analysis = file_content if (uploaded_file and uploaded_file.filename != '') else None
            mime_type_for_analysis = mime_type if (uploaded_file and uploaded_file.filename != '') else None
            
            report = check_document_authenticity(text_to_analyze, file_content_for_analysis, mime_type_for_analysis)
            return jsonify(report)
        else:
            # No text, return a generic "safe" report
            return jsonify({ "confidence_score": 100, "summary": "No text provided.", "findings": [] })

    except Exception as e:
        print(f"Error in authenticity check endpoint: {e}")
        return jsonify({"error": "Failed to process document for authenticity check."}), 500

@app.route("/check-logos", methods=["POST"])
def check_logos():
    """
    A dedicated endpoint for logo analysis only.
    """
    uploaded_file = request.files.get('pdf_file')
    
    if not uploaded_file or uploaded_file.filename == '':
        return jsonify({"error": "No file provided for logo analysis."}), 400
    
    try:
        file_content = uploaded_file.read()
        mime_type = uploaded_file.mimetype
        
        # Check page limit first
        page_limit_result = check_page_limit(file_content, mime_type)
        if page_limit_result['exceeds_limit']:
            return jsonify({
                "success": False,
                "error": "Document exceeds page limit",
                "page_details": page_limit_result
            })
        
        # Perform logo analysis
        logo_result = check_document_logos(file_content, mime_type)
        return jsonify(logo_result)
        
    except Exception as e:
        print(f"Error in logo analysis endpoint: {e}")
        return jsonify({"error": "Failed to process document for logo analysis."}), 500

        
if __name__ == "__main__":
    app.run(debug=True)

