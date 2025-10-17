import os
import vertexai
from vertexai.generative_models import GenerativeModel
import markdown
import json
import re
import csv
import io
from google.oauth2 import service_account
from google.auth import default as google_auth_default
from fpdf import FPDF

# --- CONFIGURATION ---
PROJECT_ID = "legalease-ai-471416"
LOCATION = "asia-south1"
CREDENTIALS_FILE = "credentials.json"  # for local dev

# --- LOAD CREDENTIALS AND INITIALIZE VERTEX AI ---
credentials = None

try:
    # 1. Check if GOOGLE_APPLICATION_CREDENTIALS_JSON is set (Render deployment)
    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json:
        credentials = service_account.Credentials.from_service_account_info(json.loads(creds_json))
        print("Initialized with credentials from GOOGLE_APPLICATION_CREDENTIALS_JSON.")
    else:
        # 2. Local file fallback
        credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
        print("Initialized with local credentials.json.")
except Exception as e:
    try:
        # 3. ADC fallback
        credentials, _ = google_auth_default()
        print("Initialized with Application Default Credentials.")
    except Exception as e2:
        print("Warning: Could not find credentials. API calls will likely fail.", e2)

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# --- MODEL INSTANTIATION: Define the model once to be reused ---
model = GenerativeModel("gemini-2.5-flash")



def analyze_risks(text: str, target_language: str = "English") -> list[dict]:
    """Analyze legal text and return a list of risks."""
    # REMOVED: vertexai.init() call was here

    def _parse_json_flex(raw: str) -> list[dict]:
        # Try direct JSON
        try:
            data = json.loads(raw)
            return data.get("risks", []) if isinstance(data, dict) else []
        except Exception:
            pass
        # Try fenced code blocks ```json ... ``` or ``` ... ```
        fenced = re.findall(r"```(?:json)?\n([\s\S]*?)\n```", raw, flags=re.IGNORECASE)
        for block in fenced:
            try:
                data = json.loads(block)
                return data.get("risks", []) if isinstance(data, dict) else []
            except Exception:
                continue
        # Try to find the first JSON object heuristically
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw[start:end+1]
            try:
                data = json.loads(candidate)
                return data.get("risks", []) if isinstance(data, dict) else []
            except Exception:
                pass
        return []

    base_prompt = f"""
    You are a senior contract analyst. Read the document and extract a concise list of potential risks.
    Return STRICT JSON ONLY, no markdown, no commentary, matching this schema exactly:
    {{
    "risks": [
    {{
      "clause": "Short quote or heading from the relevant clause.",
      "issue": "A brief, one-sentence explanation of the potential problem.",
      "severity": "low|medium|high",
      "type": "A single category like IP, Liability, Payment, Termination, etc.",
      "worst_case": "A very short, practical worst-case outcome (max 10 words).",
      "suggestion": "A short, actionable tip. Start with a verb (e.g., 'Clarify...', 'Negotiate...', 'Define...')."
    }}
    ]
    }}
    CRITICAL:
    - The values for "clause", "issue", and "suggestion" MUST be written in this language: {target_language}
    - The value for "severity" MUST be one of: low, medium, high (lowercase, English)
    - "type" should be a single short word or phrase in {target_language} that best describes the risk category.
    Document:
    ---
    {text}
    ---
    """
    try:
        response = model.generate_content(base_prompt)
        raw = response.text or ""
        risks = _parse_json_flex(raw)
        # Fallback: retry with truncated document and stronger instruction if empty
        if not risks:
            short_doc = text[:15000]
            retry_prompt = f"""
            Output JSON only. Do not include any text before or after the JSON. Same schema as above.
            Ensure fields are in {target_language} except severity which must be low|medium|high.
            Document:
            ---
            {short_doc}
            ---
            """
            try:
                retry_resp = model.generate_content(retry_prompt)
                risks = _parse_json_flex(retry_resp.text or "")
            except Exception:
                pass
        # Normalize severity to expected set
        normalized = []
        for r in risks:
            sev = str(r.get("severity", "")).strip().lower()
            if sev not in {"low", "medium", "high"}:
                sev = "medium"
            normalized.append({
                "clause": r.get("clause", ""),
                "issue": r.get("issue", ""),
                "severity": sev,
                "type": r.get("type", ""),
                "worst_case": r.get("worst_case", ""),
                "suggestion": r.get("suggestion", "")
            })
        return normalized
    except Exception as e:
        print(f"Risk analysis error: {e}")
        return []


def render_risks_html(risks: list[dict], target_language: str = "English") -> str:
    """Render color-coded HTML list for risks with localized badge labels."""
    def _labels(lang: str) -> tuple[str, str, str, str]:
        lang = (lang or "").lower()
        if lang.startswith("spanish") or lang.startswith("espa"): # Español
            return ("Alto", "Medio", "Bajo", "Riesgo")
        if lang.startswith("french") or lang.startswith("fran"): # Français
            return ("Élevé", "Moyen", "Faible", "Risque")
        if lang.startswith("german") or lang.startswith("deut"): # Deutsch
            return ("Hoch", "Mittel", "Niedrig", "Risiko")
        if lang.startswith("hindi") or "हिन्दी" in lang: # हिन्दी
            return ("उच्च", "मध्यम", "निम्न", "जोखिम")
        if lang.startswith("marathi") or "मराठी" in lang: # मराठी
            return ("उच्च", "मध्यम", "कमी", "जोखीम")
        return ("High", "Medium", "Low", "Risk")

    def _field_labels(lang: str) -> tuple[str, str]:
        lang = (lang or "").lower()
        if lang.startswith("spanish") or lang.startswith("espa"):
            return ("Problema", "Sugerencia")
        if lang.startswith("french") or lang.startswith("fran"):
            return ("Problème", "Suggestion")
        if lang.startswith("german") or lang.startswith("deut"):
            return ("Problem", "Empfehlung")
        if lang.startswith("hindi") or "हिन्दी" in lang:
            return ("मुद्दा", "सुझाव")
        if lang.startswith("marathi") or "मराठी" in lang:
            return ("मुद्दा", "सूचना")
        return ("Issue", "Suggestion")

    def _md_inline(s: str) -> str:
        """Convert markdown to inline HTML: strip block tags like <p>, <ul>, <ol>, <li>."""
        if not s:
            return ""
        html = markdown.markdown(s)
        # Strip wrapping <p> ... </p>
        if html.startswith('<p>') and html.endswith('</p>'):
            html = html[3:-4]
        # Flatten lists
        html = html.replace('<ul>', '').replace('</ul>', '')
        html = html.replace('<ol>', '').replace('</ol>', '')
        html = html.replace('</li>', '; ')
        html = html.replace('<li>', '')
        # Remove newlines introduced by markdown
        return html.replace('\n', ' ').strip(' ;')

    if not risks:
        return "<p class='risk-empty'>No obvious risks detected.</p>"
    sev_to_class = {"low": "risk-low", "medium": "risk-medium", "high": "risk-high"}
    high_lbl, med_lbl, low_lbl, risk_word = _labels(target_language)
    issue_lbl, sugg_lbl = _field_labels(target_language)
    sev_label_map = {"high": high_lbl, "medium": med_lbl, "low": low_lbl}
    items = []
    for r in risks:
        css = sev_to_class.get(r.get("severity", "medium"), "risk-medium")
        clause = _md_inline((r.get("clause") or "").strip())
        issue = _md_inline((r.get("issue") or "").strip())
        worst_case = _md_inline((r.get("worst_case") or "").strip())
        rtype = _md_inline((r.get("type") or "").strip())
        suggestion = _md_inline((r.get("suggestion") or "").strip())
        badge_text = f"{sev_label_map.get(r.get('severity','medium'), med_lbl)} {risk_word}"
        items.append(
            f"<li class='risk-item {css}' data-type='{rtype}'>"
            f"<div class='risk-header'><span class='risk-badge'>{badge_text}</span>"
            f"<strong>{clause or 'Unnamed Clause'}</strong></div>"
            f"<div class='risk-body'><div class='risk-issue'><b>{issue_lbl}:</b> {issue}</div>"
            f"<div class='risk-worst'><b>Worst case:</b> {worst_case}</div>"
            f"<div class='risk-type'><b>Type:</b> {rtype}</div>"
            f"<div class='risk-suggestion'><b>{sugg_lbl}:</b> {suggestion}</div>"
            f"</div>"
            f"</li>"
        )
    return "<ul class='risk-list'>" + "".join(items) + "</ul>"


def compute_risk_stats(risks: list[dict]) -> dict:
    """Compute counts for severity and type to drive charts."""
    severity_counts: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
    type_counts: dict[str, int] = {}
    for r in risks:
        sev = str(r.get("severity", "")).strip().lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
        else:
            severity_counts.setdefault("medium", 0)
            severity_counts["medium"] += 1
        rtype = (r.get("type") or "Uncategorized").strip() or "Uncategorized"
        type_counts[rtype] = type_counts.get(rtype, 0) + 1
    return {"severity": severity_counts, "type": type_counts}


def rewrite_clause(clause_text: str, target_language: str = "English", mode: str = "plain") -> str:
    """Generate a safer rewrite of a clause."""
    # REMOVED: vertexai.init() call was here
    style_hint = "plain, clear non-legalese" if mode == "plain" else "concise, formal legal drafting"
    prompt = f"""
    Rewrite the following clause to be SAFER for the signing party while preserving business intent.
    - Use {style_hint}
    - Keep it brief and actionable
    - Write entirely in: {target_language}

    Clause:
    ---
    {clause_text}
    ---
    """
    try:
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        print(f"Rewrite error: {e}")
        return "Sorry, could not generate a safer rewrite right now."


def risks_to_csv(risks: list[dict]) -> str:
    """Return CSV string for risks."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["clause", "issue", "severity", "type", "worst_case", "suggestion"])
    for r in risks:
        writer.writerow([
            r.get("clause", ""),
            r.get("issue", ""),
            r.get("severity", ""),
            r.get("type", ""),
            r.get("worst_case", ""),
            r.get("suggestion", ""),
        ])
    return output.getvalue()


def risks_to_html(risks: list[dict], target_language: str = "English") -> str:
    """Return standalone HTML for risks."""
    body = render_risks_html(risks, target_language)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Risk Export</title>"
        "<style>body{font-family:sans-serif;padding:24px;} .risk-item{margin:12px 0;padding:12px;border-radius:8px;border:1px solid #eee;}</style>"
        "</head><body>" + body + "</body></html>"
    )


def risks_to_pdf_bytes(risks: list[dict], target_language: str = "English") -> bytes:
    """Render a compact PDF for the risks list and return it as bytes."""
    def _safe(text: str) -> str:
        s = (text or "")
        s = (s
            .replace("“", '"').replace("”", '"')
            .replace("‘", "'").replace("’", "'")
            .replace("–", "-").replace("—", "-")
            .replace("•", "-")
        )
        try:
            return s.encode('latin-1', 'replace').decode('latin-1')
        except Exception:
            return s
    pdf = FPDF(unit="pt", format="A4")
    pdf.set_auto_page_break(auto=True, margin=36)
    pdf.add_page()
    pdf.set_title("LegalEase AI - Risk Report")

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 22, "LegalEase AI - Risk Report", ln=1)
    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(40, 40, 40)

    if not risks:
        pdf.multi_cell(0, 16, _safe("No obvious risks detected."))
        return pdf.output(dest='S').encode('latin1')

    sev_color = {"low": (6,214,160), "medium": (255,209,102), "high": (255,107,107)}

    for r in risks:
        sev = str(r.get("severity", "medium")).lower()
        color = sev_color.get(sev, (200,200,200))
        pdf.set_fill_color(*color)
        pdf.set_text_color(0,0,0)
        pdf.cell(70, 16, _safe(sev.capitalize()), align='C', fill=True)
        pdf.cell(0, 16, _safe(f"Clause: {r.get('clause','')}`".rstrip('`')), ln=1)

        pdf.set_text_color(60,60,60)
        issue = r.get("issue", "")
        worst = r.get("worst_case", "")
        type_ = r.get("type", "")
        sugg = r.get("suggestion", "")
        if type_:
            pdf.set_font_size(11)
            pdf.multi_cell(0, 14, _safe(f"Type: {type_}"))
        if issue:
            pdf.multi_cell(0, 14, _safe(f"Issue: {issue}"))
        if worst:
            pdf.multi_cell(0, 14, _safe(f"Worst case: {worst}"))
        if sugg:
            pdf.multi_cell(0, 14, _safe(f"Suggestion: {sugg}"))
        pdf.ln(6)

    return pdf.output(dest='S').encode('latin-1', 'replace')


def summarize_text(text: str, target_language: str = "English") -> str:
    """Generates a simple summary of the text."""
    # REMOVED: vertexai.init() call was here
    prompt = f"""
    You are an expert paralegal AI assistant. Your goal is to simplify complex legal documents for the average person, providing a balanced summary that is detailed but easy to read.

    **Output Structure:**
    1.  **Document Purpose:** Start with a 1-2 sentence overview explaining what this document is for (e.g., 'This is a freelance contract for web design services between a client and a developer.').
    2.  **Key Sections Explained:** Below the overview, create a summary of the document's main sections. For each section, use a bolded heading (like **Scope of Work** or **Payment Terms**) and provide a 1-3 sentence explanation in simple terms. Cover all important topics present in the document, such as who is involved, main responsibilities, payment details, confidentiality, liability, and how the agreement can be ended.

    Use Markdown for formatting. The entire response MUST be in this language: **{target_language}**

    ---
    LEGAL TEXT:
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
    # REMOVED: vertexai.init() call was here
    conversation_history_string = ""
    for message in history:
        role = "User" if message['role'] == 'user' else "AI"
        conversation_history_string += f"{role}: {message['text']}\n"

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


def is_legal_document(text: str) -> bool:
    """
    Uses the AI to perform a quick classification of the text.
    Returns True if the document appears to be legal in nature, False otherwise.
    """
    # Use a very short snippet for speed
    text_snippet = text[:2000]

    prompt = f"""
    You are a document classifier. Your task is to determine if the following text is a legal document.
    Legal documents include contracts, terms of service, non-disclosure agreements, lease agreements, privacy policies, etc.
    Non-legal documents include articles, stories, recipes, conversations, etc.

    Analyze the text below and respond with a single word: YES or NO.

    ---
    TEXT:
    {text_snippet}
    ---
    """
    try:
        # Use a low temperature for a more deterministic, non-creative answer
        generation_config = {"temperature": 0.0}
        response = model.generate_content(prompt, generation_config=generation_config)

        # Check if the response text contains "YES"
        return "yes" in (response.text or "").strip().lower()

    except Exception as e:
        print(f"Legal document classification error: {e}")
        # If classification fails, assume it's legal to proceed without interruption.
        return True


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
