from flask import Flask, render_template, request
from legal_analyzer import summarize_text
from PyPDF2 import PdfReader
import markdown

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    html_result = None
    text_to_analyze = ""

    if request.method == "POST":
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
        # If we have some text (from either source) and no error has occurred, analyze it.
        if text_to_analyze and not html_result:
            try:
                result = summarize_text(text_to_analyze)
                if result:
                    html_result = markdown.markdown(result)
            except Exception as e:
                html_result = f"<p style='color: #ff6b6b;'><b>Error:</b> Could not connect to the AI service. Please check your configuration and try again. Details: {e}</p>"

    # Render the main page, passing in the result (or None if it's the first visit)
    return render_template("index.html", result=html_result)

if __name__ == "__main__":
    app.run(debug=True)