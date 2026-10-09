from flask import Flask, render_template, request, jsonify
from config import Config
from services.document_parser import DocumentParser
from services.task_processor import TaskProcessor

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'bwu-resume-analyzer-secret-2026'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload limit

# Instantiate task processor service
processor = TaskProcessor()

@app.route('/')
def index():
    """Render main user interface."""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Return backend status and safe configuration info (NO API keys exposed)."""
    status = Config.get_safe_status()
    return jsonify({
        "status": "online",
        "app_name": "AI Resume Screening & Skill Gap Analyzer",
        "config": status
    })

@app.route('/api/analyze', methods=['POST'])
def handle_analyze():
    """
    Handle resume screening and skill gap analysis request.
    Supports both file upload (PDF/DOCX/TXT) and text pasting.
    """
    resume_text = ""
    filename = None
    job_description = ""

    # Check if request is multipart/form-data (file upload)
    if request.files or request.form:
        job_description = request.form.get('job_description', '').strip()
        pasted_resume = request.form.get('resume_text', '').strip()

        # Handle File Upload if present
        if 'resume_file' in request.files:
            file_storage = request.files['resume_file']
            if file_storage and file_storage.filename:
                filename = file_storage.filename
                extracted, err = DocumentParser.extract_text_from_file(file_storage)
                if err:
                    return jsonify({"success": False, "error": err}), 400
                resume_text = extracted

        # Fallback to pasted resume text if no file was uploaded
        if not resume_text and pasted_resume:
            resume_text = pasted_resume

    # Check if request is raw JSON payload
    elif request.is_json:
        data = request.get_json() or {}
        resume_text = data.get('resume_text', '').strip()
        job_description = data.get('job_description', '').strip()
        filename = data.get('filename', None)

    # Invoke task processor service
    result = processor.process_resume_screening(resume_text, job_description, filename)
    
    if not result.get("success"):
        return jsonify({
            "success": False,
            "error": result.get("error", "AI analysis unavailable. Please check the Gemini API connection.")
        }), 400

    return jsonify(result)

# Global Error Handlers
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"success": False, "error": "Bad Request: Invalid input or missing parameters."}), 400

@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({"success": False, "error": "File size exceeds maximum upload limit of 16MB."}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Requested endpoint not found."}), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"success": False, "error": f"Internal Server Error: {str(e)}"}), 500

def free_port(port: int):
    """Automatically clears/kills any process holding the port so app.py starts cleanly."""
    import socket, subprocess, time, os
    # Don't run twice during Flask reloader
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        return
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(('127.0.0.1', port)) == 0:
                print(f"🔄 Port {port} is in use. Clearing previous session...")
                subprocess.run(f"fuser -k -9 {port}/tcp", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(0.5)
    except Exception as e:
        pass

if __name__ == '__main__':
    Config.validate()
    free_port(Config.PORT)
    print(f"🚀 Starting AI Resume Screening Application on http://127.0.0.1:{Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)

