import vertexai
from vertexai.generative_models import GenerativeModel
import markdown # --- NEW: Import the markdown library ---

PROJECT_ID = "legalease-ai-471416"
LOCATION = "asia-south1"

# --- MODIFIED: Added 'target_language' parameter ---
def summarize_text(text: str, target_language: str = "English") -> str:
    """Uses the Gemini model to summarize a piece of legal text in a specified language."""

    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # Load the Gemini-1.5-Flash model
    model = GenerativeModel("gemini-1.5-flash")

    # --- MODIFIED: The prompt now includes the language instruction ---
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
        # Send the prompt to the model and get the response
        response = model.generate_content(prompt)
        # --- MODIFIED: Convert the AI's markdown response to HTML ---
        return markdown.markdown(response.text)
    except Exception as e:
        print(f"An error occurred with the AI model: {e}")
        return "Sorry, there was an error processing your request with the AI."


# This is the main part of our script for testing
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

    # Call our function to get the summary in Marathi
    # You can change "Marathi" to "Spanish", "Hindi", etc. to test
    summary = summarize_text(sample_legal_text, target_language="Marathi")

    # Print the result from the AI
    print("AI-Generated Summary (in Marathi):")
    # Note: The output will be HTML formatted, which might look a bit messy in the terminal
    # but will render correctly in the browser.
    print(summary)
    print("-" * 30)