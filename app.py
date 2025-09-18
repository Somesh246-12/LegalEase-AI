from flask import Flask, render_template, request
from legal_analyzer import summarize_text, get_chatbot_response
from PyPDF2 import PdfReader
import os
from google.cloud import vision
from google.oauth2 import service_account # --- NEW IMPORT ---

# --- NEW: Define credentials path ---
CREDENTIALS_FILE = "credentials.json"
credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)

# --- NEW IMPORTS ---
from legal_analyzer import analyze_risks, render_risks_html

app = Flask(__name__)
app.secret_key = os.urandom(24)

def extract_text_from_image(file):
    """Performs OCR on an image file and returns the extracted text."""
    # --- MODIFIED: Pass credentials directly ---
    client = vision.ImageAnnotatorClient(credentials=credentials)
    content = file.read()
    image = vision.Image(content=content)
    
    response = client.text_detection(image=image)
    texts = response.text_annotations
    
    if texts:
        return texts[0].description
    else:
        return ""

# ... (rest of your app.py code remains the same) ...

@app.route("/", methods=["GET", "POST"])
def index():
    html_result = None
    text_to_analyze = ""
    original_text = ""
    # NEW: risk html
    risk_html = None

    if request.method == "POST":
        selected_language = request.form.get("target_language", "English")
        uploaded_file = request.files.get('pdf_file')
        original_text = text_to_analyze
        
        if uploaded_file and uploaded_file.filename != '':
            try:
                filename = uploaded_file.filename.lower()
                
                if filename.endswith('.pdf'):
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        text_to_analyze += page.extract_text() + "\n"
                
                elif filename.endswith(('.png', '.jpg', '.jpeg')):
                    text_to_analyze = extract_text_from_image(uploaded_file)
                
                elif filename.endswith('.txt'):
                    text_to_analyze = uploaded_file.read().decode('utf-8')
                
                else:
                    html_result = f"<p style='color: #ffcc00;'>Unsupported file type. Please upload a PDF, TXT, PNG, or JPG file.</p>"
            
            except Exception as e:
                html_result = f"<p style='color: #ff6b6b;'><b>Error:</b> Could not read the file. It may be corrupted or an unsupported format. Details: {e}</p>"

        # If not from file, use pasted text
        if not text_to_analyze and not html_result:
            text_to_analyze = request.form.get("legal_text", "")

        # Ensure original_text mirrors what we will analyze for chat context
        original_text = text_to_analyze if text_to_analyze else original_text

        if text_to_analyze and not html_result:
            try:
                html_result = summarize_text(text_to_analyze, target_language=selected_language)
                # --- NEW: risk analysis
                risks = analyze_risks(text_to_analyze, target_language=selected_language)
                risk_html = render_risks_html(risks, target_language=selected_language)
            except Exception as e:
                html_result = f"<p style='color: #ff6b6b;'><b>Error:</b> Could not connect to the AI service. Details: {e}</p>"
        
        elif not text_to_analyze and not html_result:
            html_result = "<p style='color: #ffcc00;'>Please paste text or upload a file to analyze.</p>"

    return render_template("index.html", result=html_result, original_text=original_text, risk_html=risk_html)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    history = data.get("history")
    document_text = data.get("document_text", "")  # NEW: Get document text

    if not history:
        return {"response": "An error occurred. No history received."}, 400

    # NEW: Pass document_text to the AI function
    bot_response = get_chatbot_response(history, document_text)
    return {"response": bot_response}

if __name__ == "__main__":
    app.run(debug=True)