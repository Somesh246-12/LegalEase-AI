# LegalEase AI ✨

A web application built for the Google Cloud Gen AI Exchange Hackathon that demystifies complex legal documents using the power of Google's Gemini models on Vertex AI.

## 🚀 Features

- **Paste Text:** Directly paste legal clauses or documents for analysis.
- **Multi-Format Support:** Users can either paste raw text or upload documents, including **PDFs, TXT files, and Images (JPG, PNG)**.
- **AI-Powered Summarization:** Get a clear, simple summary of your document, highlighting key obligations, rights, and potential risks.
- **OCR for Images:** Automatically extracts text from uploaded images using the Google Cloud Vision API.
- **Multilingual Support:** Get simplified explanations in various languages, including English, Spanish, French, German, Hindi, and Marathi.
- **Interactive Chatbot:** A floating chatbot assistant can provide simple definitions for any confusing words in the summary.
- **Modern UI:** A clean, responsive, and user-friendly interface.
- **AI-Powered Risk Analysis:** Detects potentially unfavorable clauses, assigns a **Low / Medium / High** severity, and presents **color‑coded** items with practical suggestions. Risk content and labels are localized to the selected language.

## 🛠️ Technology Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS
- **Cloud Platform:** Google Cloud
- **AI Services:**
    - **Vertex AI:** For accessing and managing the generative models.
    - **Gemini AI Model:** The core AI engine for text analysis and summarization.
    - **Google Cloud Vision API:** For OCR

## How to Run Locally

To get a local copy up and running, follow these simple steps.

### Prerequisites
* Python 3.8+
* Google Cloud SDK (`gcloud`) installed and configured.

### Installation & Setup
1.  **Clone the repo:**
    ```sh
    git clone [https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git)
    cd YOUR_REPOSITORY_NAME
    ```
2.  **Create and activate a virtual environment:**
    ```sh
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS / Linux
    source venv/bin/activate
    ```
3.  **Install the required packages:**
    ```sh
    pip install Flask google-cloud-aiplatform google-cloud-vision PyPDF2 Markdown
    ```
4.  **Set up Google Cloud Credentials:**
    * Follow the Google Cloud documentation to create a **service account**.
    * Grant the service account the **`Editor`** role for your project.
    * Download the JSON key for the service account and save it in your project folder with the name `credentials.json`.

5.  **Secure Your Credentials:**
    * Create a file named `.gitignore` in your project folder.
    * Add `credentials.json` to this file to prevent your secret key from being uploaded to GitHub.

6.  **Run the application:**
    ```sh
    flask run
    ```

## 🧠 Risk Analysis Overview
- Located alongside the summary, the **Risk Analysis** pane lists extracted risks as items with:
  - **Clause**: short quote or heading
  - **Issue**: what could go wrong
  - **Severity**: Low / Medium / High (machine‑readable values; color‑coded)
  - **Suggestion**: practical mitigation or redline idea
- The selected output language applies to risk text as well (e.g., Marathi labels and content), while severity values remain consistent internally.

### Colors
- High: red
- Medium: yellow
- Low: green

### Tips & Troubleshooting
- If the risk panel shows “No obvious risks detected”:
  - Provide more context or a larger portion of the contract.
  - Ensure `credentials.json` is valid and the Vertex AI model is reachable.
- If risk items appear misaligned, ensure you’re on the latest build; the app normalizes markdown to avoid stray bullets and extra spacing.

---
> **Disclaimer:** This tool is for informational purposes only and does not constitute legal advice. Always consult with a qualified legal professional for any legal matters.
