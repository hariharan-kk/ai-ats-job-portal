# 🚀 AI-Powered Applicant Tracking System (ATS)

An intelligent, full-stack Django web application designed to automate the initial screening phase of technical recruitment. This system utilizes Google's Generative AI (`gemini-2.5-flash`) to parse uploaded resumes, evaluate them against specific job requirements in real-time, and generate actionable match scores for HR teams.

## 🌟 Key Features

* **Intelligent Resume Parsing:** Extracts unstructured text from candidate PDF uploads using `PyPDF2`.
* **Automated AI Screening:** Integrates with the Google Gemini API (forced into strict JSON output mode) to evaluate candidate skills against core job requirements, returning a precise percentage match and justification.
* **Role-Based Access Control:** Custom middleware to isolate Candidate Dashboards from the Secure HR Admin Portal.
* **Interactive HR Command Center:** A heavily customized Django Admin interface featuring inline status editing, automated candidate sorting by AI score, and an integrated interview scheduler.
* **Automated SMTP Email Pipeline:** Backend triggers that automatically email candidates based on AI evaluation thresholds and interview scheduling events.

## 🛠️ Tech Stack

* **Backend:** Python, Django 5.x
* **AI / NLP:** Google Gemini 2.5 Flash API (`google.generativeai`)
* **Data Processing:** PyPDF2
* **Frontend:** HTML5, Bootstrap 5
* **Database:** SQLite (Development)
* **Automation:** Django `send_mail` via Google SMTP

## 🔄 System Architecture & Workflow

### 1. The Candidate Flow
1. User browses active technical job postings.
2. User uploads a PDF resume via the secure application portal.
3. The system extracts the text and sends a structured prompt to Gemini.
4. The AI returns a JSON payload containing the match score.
5. The application is saved, and the candidate instantly receives an automated email regarding their Shortlisted or Rejected status.

### 2. The HR Admin Flow
1. HR logs into the secure backend portal.
2. The dashboard displays all candidates, automatically sorted with the highest AI match scores at the top.
3. HR can review the AI's justification and the extracted resume text.
4. If selected, HR updates the status to "HR Interviewing" and inputs a date/venue.
5. A custom Django `save()` method intercepts the database update and automatically fires off a calendar invitation email to the candidate.

## 🚀 Local Installation & Setup

**1. Clone the repository**
\`\`\`bash
git clone https://github.com/yourusername/ai-ats-job-portal.git
cd ai-ats-job-portal
\`\`\`

**2. Create and activate a virtual environment**
\`\`\`bash
python -m venv venv
source venv/Scripts/activate  # On Windows
\`\`\`

**3. Install dependencies**
\`\`\`bash
pip install django PyPDF2 google-generativeai
\`\`\`

**4. Configure Environment Variables**
Open `settings.py` and add your secure credentials:
* `GEMINI_API_KEY = "your_google_ai_studio_key"`
* `EMAIL_HOST_USER = "your_gmail_address"`
* `EMAIL_HOST_PASSWORD = "your_16_character_app_password"`

**5. Run Database Migrations**
\`\`\`bash
python manage.py makemigrations
python manage.py migrate
\`\`\`

**6. Create a Superuser (HR Admin)**
\`\`\`bash
python manage.py createsuperuser
\`\`\`

**7. Start the Development Server**
\`\`\`bash
python manage.py runserver
\`\`\`
Navigate to `http://127.0.0.1:8000/` for the Candidate portal and `http://127.0.0.1:8000/admin/` for the HR portal.