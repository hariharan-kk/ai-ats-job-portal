# 🚀 Offline AI Applicant Tracking System (ATS)

A privacy-first, full-stack Django web application designed to automate technical recruitment screening using localized Artificial Intelligence. By entirely removing cloud dependencies, this system utilizes a local Small Language Model (Qwen 2.5 via Ollama) to parse unstructured resumes, evaluate them against core job requirements, and output strict JSON match scores—all while keeping sensitive candidate data 100% on-premise.

**Developed by Angith Krishna B**

## 🌟 Key Features

* **100% Offline AI Screening:** Replaced cloud APIs with a local instance of the Qwen 2.5 (3B) model using Ollama, ensuring zero-cost inference and total data privacy.
* **Intelligent Document Parsing:** Extracts raw text from candidate PDF uploads using `PyPDF2`.
* **Prompt Engineering for Strict JSON:** Custom system prompts force the local LLM to bypass conversational chat and return structured, database-ready JSON payloads.
* **Role-Based Access Control:** Custom middleware physically isolates Candidate Application Dashboards from the Secure HR Admin Portal.
* **Interactive HR Command Center:** A heavily customized Django Admin interface featuring inline status editing, automated candidate sorting by AI score, and an integrated interview scheduler.
* **Automated SMTP Email Pipeline:** Backend `save()` overrides automatically trigger and email Google Meet/Zoom invitations to candidates when HR updates their status.

## 🛠️ Tech Stack

* **Backend:** Python, Django 5.x
* **AI / ML Engine:** Ollama, Qwen 2.5 (3-Billion Parameter Model)
* **Data Processing:** PyPDF2
* **Frontend:** HTML5, Bootstrap 5
* **Database:** SQLite (Development)
* **Automation:** Django `send_mail` via Google SMTP

## 🔄 System Architecture & Workflow

### 1. The Candidate Flow
1. User browses active technical job postings.
2. User uploads a PDF resume via the secure application portal.
3. The system extracts the text and sends a structured prompt to the local Ollama server running on the host machine.
4. The Qwen model returns a JSON payload containing a precise percentage match and justification.
5. The application is saved, and the candidate instantly receives an automated email regarding their status.

### 2. The HR Admin Flow
1. HR logs into the secure backend portal.
2. The dashboard displays all candidates, automatically sorted with the highest AI match scores at the top.
3. HR can review the AI's justification and the extracted resume text without any data ever leaving the local network.
4. If selected, HR updates the status to "HR Interviewing" and inputs a date/venue.
5. A custom Django method intercepts the database update and automatically fires off a calendar invitation email to the candidate.

## 🚀 Local Installation & Setup

**1. Install the Local AI Engine**
Download and install [Ollama](https://ollama.com/). Once installed, open your terminal and pull the Qwen 2.5 model:
\`\`\`bash
ollama run qwen2.5:3b
\`\`\`

**2. Clone the repository**
\`\`\`bash
git clone https://github.com/yourusername/ai-ats-job-portal.git
cd ai-ats-job-portal
\`\`\`

**3. Create and activate a virtual environment**
\`\`\`bash
python -m venv venv
# On Windows:
venv\Scripts\activate  
# On macOS/Linux:
source venv/bin/activate
\`\`\`

**4. Install dependencies**
\`\`\`bash
pip install django PyPDF2 ollama
\`\`\`

**5. Configure Environment Variables**
Open `settings.py` and add your secure email credentials for the automated scheduling pipeline:
* `EMAIL_HOST_USER = "your_gmail_address"`
* `EMAIL_HOST_PASSWORD = "your_16_character_app_password"`

**6. Run Database Migrations**
\`\`\`bash
python manage.py makemigrations
python manage.py migrate
\`\`\`

**7. Create a Superuser (HR Admin)**
\`\`\`bash
python manage.py createsuperuser
\`\`\`

**8. Start the Development Server**
\`\`\`bash
python manage.py runserver
\`\`\`
Navigate to `http://127.0.0.1:8000/` for the Candidate portal and `http://127.0.0.1:8000/admin/` for the HR portal.