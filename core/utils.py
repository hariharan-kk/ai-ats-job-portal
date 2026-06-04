import PyPDF2
import json
import ollama
import requests 

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
    
def generate_custom_questions(resume_text):
    """
    Sends the resume to the local AI to generate 5 custom multiple-choice questions.
    Forces the AI to return a strict JSON array so Django can save it to the database.
    """
    url = "http://localhost:11434/api/generate"
    
    prompt = f"""
    You are an expert Senior Technical Recruiter and Senior Software Engineer. 
    Review the following candidate resume text. Identify the core programming languages, frameworks, and tools the candidate claims to know.
    
    Your task is to generate EXACTLY 10 highly technical, real-world multiple-choice questions to test those specific skills. 
    Do NOT ask basic trivia. Ask advanced, scenario-based, or architectural questions.

    Resume Text:
    {resume_text}

    You MUST return the output STRICTLY as a single JSON object containing a key named "questions", which holds an array of exactly 10 objects. Do not include any markdown or conversational text. 
    You MUST follow this exact structure:
    {{
        "questions": [
            {{
                "text": "In Django, what is the most efficient way to resolve an N+1 query problem when accessing related foreign key objects?",
                "option_a": "Using .all() with a Python for-loop",
                "option_b": "Using .select_related() or .prefetch_related()",
                "option_c": "Using raw SQL exclusively",
                "option_d": "Increasing the database cache timeout",
                "correct_answer": "B"
            }}
        ]
    }}
    """
    payload = {
        "model": "qwen2.5:3b",
        "prompt": prompt,
        "stream": False,
        "format": "json"  
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        # Extract the raw text from the AI's response
        ai_response_text = response.json().get("response", "[]")
        
        # --- DEBUG PRINTOUT ---
        print("\n=== DEBUG: WHAT DID QWEN ACTUALLY SAY? ===")
        print(ai_response_text)
        print("==========================================\n")
        
        # Clean up the string just in case the AI added markdown backticks
        ai_response_text = ai_response_text.strip()
        if ai_response_text.startswith("```json"):
            ai_response_text = ai_response_text[7:]
        if ai_response_text.startswith("```"):
            ai_response_text = ai_response_text[3:]
        if ai_response_text.endswith("```"):
            ai_response_text = ai_response_text[:-3]
            
        ai_response_text = ai_response_text.strip()

        # Convert the JSON string into a usable Python List/Dictionary
        questions_list = json.loads(ai_response_text)
        return questions_list
        
    except Exception as e:
        print(f"\nCRITICAL JSON ERROR: Failed to parse Qwen's output: {e}\n")
        return None