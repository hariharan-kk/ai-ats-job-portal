import PyPDF2
import google.generativeai as genai
import json
from django.conf import settings

def extract_text_from_pdf(pdf_file):
    """Extracts raw text from an uploaded PDF file."""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"PDF Extraction Error: {e}")
        return ""

def evaluate_resume_with_gemini(resume_text, job_requirements):
    """Sends the resume and requirements to Gemini and returns a score and justification."""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    # THE FIX: We added the generation_config to FORCE pure JSON output
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""
    You are an expert technical recruiter and AI ATS system.
    Evaluate the following resume against the provided job requirements.
    
    Job Requirements:
    {job_requirements}
    
    Resume Text:
    {resume_text}
    
    Return ONLY a valid JSON object with exactly two keys:
    "score": an integer from 0 to 100 representing the percentage match.
    "justification": a brief 2-3 sentence explanation of why this score was given.
    """
    
    try:
        response = model.generate_content(prompt)
        
        # THE FIX: Because we forced JSON mode above, we can delete the messy .replace() cleaner
        # We just load the raw text directly into JSON now!
        result = json.loads(response.text)
        
        return result.get('score', 0), result.get('justification', "Failed to generate justification.")
    except Exception as e:
        # If it still fails, it will print exactly WHY to your terminal
        print(f"Gemini API Error: {e}")
        return 0, "Error evaluating resume."