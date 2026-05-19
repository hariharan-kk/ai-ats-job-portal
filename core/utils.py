import PyPDF2
import json
import ollama 

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

def evaluate_resume_with_local_model(resume_text, job_requirements):
    """Sends the resume to local Qwen 2.5 and returns a score and justification."""
    
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
        # Call the local Ollama server
        response = ollama.chat(model='qwen2.5:3b', messages=[
            {
                'role': 'user',
                'content': prompt,
            },
        ], format='json') 
        
        # Parse the JSON string
        result = json.loads(response['message']['content'])
        
        return result.get('score', 0), result.get('justification', "Failed to generate justification.")
    
    except Exception as e:
        print(f"Local AI Error: {e}")
        return 0, "Error evaluating resume with local model."