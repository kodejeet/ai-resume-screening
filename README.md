# 💼 AI Resume Screening & Skill Gap Analyzer

A complete, modern Python application designed as a practical recruitment intelligence tool powered by **Google Gemini API (Google AI Studio)**. The system allows recruiters, HR professionals, and candidates to upload or paste a resume alongside a target job description to evaluate candidate fit, extract matched vs missing skills, compute an objective match score, and receive actionable skill gap recommendations.

---

## 📌 Core Features

1. **📄 Candidate Resume Parsing & Processing**
   - Supports direct file uploads (**PDF**, **DOCX**, or **TXT**) and text pasting.
   - Automatically extracts plain text server-side using `pypdf` and `python-docx`.

2. **🎯 Google Gemini AI Resume Screening & Match Scoring**
   - Calculates a candidate-to-job compatibility score (0% – 100%).
   - Classifies fit into **Strong Match**, **Moderate Match**, or **Weak Match**.
   - Compares experience depth and educational qualifications against job prerequisites.
   - Enforces strict anti-hallucination rules and evidence-based Python validation.

3. **📊 Skill Gap Analysis & Learning Recommendations**
   - Categorizes skills into **Matched Skills**, **Missing Skills**, and **Additional/Relevant Skills**.
   - Itemizes each missing skill with its business importance, reason for necessity, and actionable ways the candidate can bridge the gap.

4. **💡 Resume Optimization Suggestions**
   - Provides targeted recommendations to improve the candidate's resume (quantifying impact, adding ATS keywords, highlighting key experience).

5. **📜 Evaluation History**
   - Maintains session evaluation history allowing recruiters to switch between candidate evaluations instantly.

---

## ⚙️ System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Frontend Web Interface                      │
│     Inter Font + Restrained Light Theme + Responsive UI      │
└──────────────────────────────┬───────────────────────────────┘
                               │ REST API / Form Upload
┌──────────────────────────────▼───────────────────────────────┐
│              Flask Backend Layer (Python app.py)             │
│   - Document Parser (pypdf & python-docx)                    │
│   - Task Processor & Prompt Engineering (task_processor.py)   │
│   - Config Manager & Key Security (config.py)                │
│   - Evidence-based Validation Layer (ai_engine.py)           │
└──────────────────────────────┬───────────────────────────────┘
                               │ Google GenAI SDK (google-genai)
┌──────────────────────────────▼───────────────────────────────┐
│                 Google Gemini API Engine                     │
│   - Model: gemini-2.5-flash (with SDK fallback)             │
│   - Returns Structured JSON Evaluation                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
ai-project-bwu/
├── .env                  # Gemini API credentials (never committed)
├── .env.example          # Template environment variable file
├── .gitignore            # Git rules (.env, .venv, __pycache__)
├── requirements.txt      # Dependencies (flask, python-dotenv, google-genai, pypdf, python-docx)
├── README.md             # Project documentation
├── config.py             # Configuration & environment variable loader
├── ai_engine.py          # Gemini API integration & evidence validation layer
├── app.py                # Flask server endpoints (/api/status, /api/analyze)
├── services/
│   ├── __init__.py
│   ├── document_parser.py# PDF & DOCX text extraction service
│   └── task_processor.py # Business logic & input validation
├── templates/
│   └── index.html        # Recruitment UI dashboard template
└── static/
    ├── css/
    │   └── style.css     # Clean light theme stylesheet
    └── js/
        └── main.js       # Client interaction & results renderer
```

---

## 🚀 Installation & Quickstart

### 1. Prerequisites
- Python 3.9 or higher installed.

### 2. Setup Virtual Environment
```bash
# Navigate to project directory
cd ai-project-bwu

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Configure Gemini API Key
Ensure `.env` exists in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
PORT=5000
DEBUG=True
```

### 4. Start the Application
```bash
python3 app.py
```
Or run directly via `.venv`:
```bash
.venv/bin/python3 app.py
```

Open your browser to: **`http://127.0.0.1:5000`**

---

## 🛡️ Security & Resiliency

- **API Key Security**: `GEMINI_API_KEY` is restricted strictly to backend environment variables. It is never exposed in browser code, HTML, or server logs.
- **Robust Error Handling**: Handles missing uploads, empty documents, invalid file types, API timeouts, and Gemini connection errors gracefully without generating fake fallback data.
