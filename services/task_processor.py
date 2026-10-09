from ai_engine import GeminiEngine

class TaskProcessor:
    """Service layer coordinating resume screening, prompt validation, and Gemini AI invocation."""

    def __init__(self):
        self.ai = GeminiEngine()

    def process_resume_screening(self, resume_text: str, job_description: str, filename: str = None) -> dict:
        """
        Validates input documents and invokes Google Gemini API for structured resume vs job description evaluation.
        """
        # 1. Validation: Resume Text Presence & Length
        if not resume_text or not resume_text.strip():
            return {
                "success": False,
                "error": "Resume text is empty or missing. Please upload a valid document or paste resume text."
            }

        if len(resume_text.strip()) < 30:
            return {
                "success": False,
                "error": "Resume content is too short (minimum 30 characters required for evaluation)."
            }

        # 2. Validation: Job Description Presence & Length
        if not job_description or not job_description.strip():
            return {
                "success": False,
                "error": "Job description is empty or missing. Please paste the job description text."
            }

        if len(job_description.strip()) < 30:
            return {
                "success": False,
                "error": "Job description is too short (minimum 30 characters required for evaluation)."
            }

        resume_text = resume_text.strip()
        job_description = job_description.strip()

        # 3. Trigger Gemini AI Analysis
        result = self.ai.analyze_resume(resume_text, job_description)

        if result.get("success") and result.get("data"):
            result["metadata"] = {
                "filename": filename or "Pasted Text Resume",
                "resume_char_count": len(resume_text),
                "jd_char_count": len(job_description)
            }

        return result
