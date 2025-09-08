import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = "legalease-ai-471416"
LOCATION = "asia-south1"

def summarize_text(text: str) -> str:
    """Uses the Gemini model to summarize a piece of legal text."""

    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # Load the Gemini-1.5-Flash model
    model = GenerativeModel("gemini-1.5-flash")

    # This is our instruction to the AI. We're telling it how to behave.
    prompt = f"""
    You are an expert paralegal AI assistant. Your goal is to simplify complex legal documents for the average person.
    Analyze the following legal clause and provide a simple, easy-to-understand summary in bullet points.
    Focus on the key obligations, rights, and potential risks for the person signing the document.

    Here is the legal clause:
    ---
    {text}
    ---
    """

    # Send the prompt to the model and get the response
    response = model.generate_content(prompt)

    return response.text


# This is the main part of our script that runs when you execute the file
# if __name__ == "__main__":
# A sample piece of complex legal text to test our function
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

    # Call our function to get the summary
    summary = summarize_text(sample_legal_text)

    # Print the result from the AI
    print("AI-Generated Summary:")
    print(summary)
    print("-" * 30)