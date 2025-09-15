import vertexai
from vertexai.generative_models import GenerativeModel
import markdown
from google.oauth2 import service_account # --- NEW IMPORT ---

# --- NEW: Define credentials path ---
CREDENTIALS_FILE = "credentials.json"
credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)

PROJECT_ID = "legalease-ai-471416" 
LOCATION = "asia-south1"

def summarize_text(text: str, target_language: str = "English") -> str:
    # --- MODIFIED: Pass credentials directly ---
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
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

def define_word(word: str) -> str:
    """Uses the Gemini model to define a word in a conversational manner."""
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
    model = GenerativeModel("gemini-1.5-flash")

    # --- NEW, UPGRADED PROMPT ---
    prompt = f"""
    You are LegalEase AI's friendly chatbot assistant, Mr.Ken. Your persona is helpful, clear, and encouraging.
    
    A user has asked about a word or phrase. Your task is to respond conversationally.

    - If the user provides a word or legal term, greet them and explain the term in a simple, easy-to-understand way, as if you were talking to a curious teenager.
    - If the user says "hello", "hi", or a similar greeting, respond with a friendly greeting and briefly introduce yourself.
    - If the user asks a question that is not a definition, provide a polite and helpful response.
    
    Here is the user's input: "{word}"
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred while defining the word: {e}")
        return "Sorry, I'm having a little trouble right now. Please try again in a moment."
# ... (rest of your legal_analyzer.py code remains the same) ...

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