import vertexai
from vertexai.generative_models import GenerativeModel
import markdown
from google.oauth2 import service_account # --- NEW IMPORT ---
from google.auth import default as google_auth_default

# --- NEW: Define credentials path ---
CREDENTIALS_FILE = "credentials.json"
try:
	credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
except Exception:
	try:
		credentials, _ = google_auth_default()
	except Exception:
		credentials = None

PROJECT_ID = "legalease-ai-471416" 
LOCATION = "asia-south1"

def summarize_text(text: str, target_language: str = "English") -> str:
	# --- MODIFIED: Initialize Vertex AI with available credentials (or ADC) ---
	if credentials is not None:
		vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
	else:
		vertexai.init(project=PROJECT_ID, location=LOCATION)
	model = GenerativeModel("gemini-1.5-flash")

	prompt = f"""
	You are an expert paralegal AI assistant. Your goal is to simplify complex legal documents for the average person.
	Analyze the following legal clause and provide a simple, easy-to-understand summary.
	Use Markdown for formatting, such as headings, bold text, and bullet points.

	IMPORTANT: You must provide your entire response in the following language: {target_language}

	Here is the legal clause to analyze:
	---
	{text}
	---
	"""

	try:
		response = model.generate_content(prompt)
		return markdown.markdown(response.text)
	except Exception as e:
		print(f"An error occurred with the AI model: {e}")
		return "Sorry, there was an error processing your request with the AI."

def get_chatbot_response(history: list, document_text: str) -> str:
	"""Gets a conversational, document-aware response from the Gemini model."""
	# Initialize Vertex AI and model for chat responses
	if credentials is not None:
		vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
	else:
		vertexai.init(project=PROJECT_ID, location=LOCATION)
	model = GenerativeModel("gemini-1.5-flash")
	# This function reuses the existing model connection

	conversation_history_string = ""
	for message in history:
		role = "User" if message['role'] == 'user' else "AI"
		conversation_history_string += f"{role}: {message['text']}\n"

	# --- NEW, DOCUMENT-AWARE PROMPT ---
	prompt = f"""You are LegalEase AI's expert chatbot. Your primary goal is to answer questions based ONLY on the provided legal document.

	If the user asks a question, answer it using the document.
	If the user asks for a definition, provide it.
	If the user asks a question that cannot be answered from the document, politely state that the answer is not found in the text.
	Be friendly and conversational.

	---
	PROVIDED DOCUMENT TEXT:
	{document_text}
	---

	CONVERSATION HISTORY:
	{conversation_history_string}
	---
	AI: """

	try:
		response = model.generate_content(prompt)
		return response.text.strip()
	except Exception as e:
		print(f"An error occurred in the chatbot: {e}")
		return "Sorry, I'm having a little trouble right now. Please try again in a moment."

if __name__ == "__main__":
    sample_legal_text = """
    "Confidential Information" means any data or information that is proprietary to the Disclosing Party and not generally known to the public,
    whether in tangible or intangible form, whenever and however disclosed, including, but not limited to:
    (i) any marketing strategies, plans, financial information, or projections, operations, sales estimates, business plans and performance results
    relating to the past, present or future business activities of such party, its affiliates, subsidiaries and affiliated companies;
    (ii) plans for products or services, and customer or supplier lists; (iii) any scientific or technical information, invention, design,
    process, procedure, formula, improvement, technology or method; and (iv) any other information that should reasonably be recognized as
    confidential information of the Disclosing Party.
    """

    print("Analyzing legal text...")
    print("-" * 30)
    summary = summarize_text(sample_legal_text, target_language="Marathi")
    print("AI-Generated Summary (in Marathi):")
    print(summary)
    print("-" * 30)