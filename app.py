from flask import Flask, render_template, request
from legal_analyzer import summarize_text # Correctly imported
from PyPDF2 import PdfReader
import os # Good practice for secret keys

app = Flask(__name__)
app.secret_key = os.urandom(24) # Added for security best practices

@app.route("/", methods=["GET", "POST"])
def index():
    html_result = None
    text_to_analyze = ""

    if request.method == "POST":
        # --- NEW: Get the selected language from the form ---
        # Defaults to 'English' if something goes wrong
        selected_language = request.form.get("target_language", "English")

        # Check if a file was uploaded
        uploaded_file = request.files.get('pdf_file')
        
        if uploaded_file and uploaded_file.filename != '':
            try:
                # Read the PDF file from the upload
                reader = PdfReader(uploaded_file)
                # Loop through all pages and extract text
                for page in reader.pages:
                    text_to_analyze += page.extract_text() + "\n"
            
            except Exception as e:
                # Create a user-friendly error message if PDF reading fails
                html_result = f"<p style='color: #ff6b6b;'><b>Error:</b> Could not read the PDF file. It may be corrupted or a scanned image. Please try another file.</p>"

        # If no file was uploaded, check for pasted text
        if not text_to_analyze:
            text_to_analyze = request.form.get("legal_text", "")

        # --- AI Analysis ---
        # If we have text and no error has occurred, analyze it.
        if text_to_analyze and not html_result:
            try:
                # --- MODIFIED: Pass the language to the function ---
                # The summarize_text function now directly returns HTML
                html_result = summarize_text(text_to_analyze, target_language=selected_language)
            
            except Exception as e:
                html_result = f"<p style='color: #ff6b6b;'><b>Error:</b> Could not connect to the AI service. Please check your configuration. Details: {e}</p>"
        
        # If the user clicked submit with no input
        elif not text_to_analyze and not html_result:
            html_result = "<p style='color: #ffcc00;'>Please paste text or upload a file to analyze.</p>"


    # Render the main page, passing in the result
    return render_template("index.html", result=html_result)

if __name__ == "__main__":
    app.run(debug=True)