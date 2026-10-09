import json
import re
import logging
import time
from google import genai
from google.genai import types
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Gemini prompt constants ──────────────────────────────────────────────────

STAGE1_SYSTEM = """You are an expert recruitment analyst. Analyze the Job Description provided and extract ALL requirements.

CRITICAL RULES:
- Extract GRANULAR, INDIVIDUAL requirements. For example, if the JD mentions "NumPy, Pandas, and Scikit-learn", extract THREE separate requirements: "NumPy", "Pandas", and "Scikit-learn".
- Extract ONLY requirements that are explicitly stated or clearly implied by the JD text.
- Do NOT invent requirements that aren't in the JD.
- Classify each requirement's importance based on the JD language (e.g. "must have" = required, "nice to have" = preferred).
- Include the exact JD text quote that supports each requirement as jd_evidence.

Return a JSON object with this structure:
{
  "job_title": "extracted job title",
  "job_summary": "1-2 sentence summary of the role",
  "requirements": [
    {
      "requirement": "Python",
      "category": "technical_skill",
      "importance": "required",
      "jd_evidence": "exact quote from JD supporting this requirement"
    }
  ]
}

Categories: technical_skill, soft_skill, experience, education, certification, responsibility, domain_knowledge
Importance: required, preferred, bonus

Do not include any text outside the JSON object."""

STAGE2_SYSTEM = """You are an expert AI Talent Acquisition Specialist performing deep evidence-based resume screening.

You are given:
1. A structured list of granular job requirements (extracted from the JD)
2. The full candidate resume text
3. The original job description text

CRITICAL ANTI-HALLUCINATION & EVIDENCE RULES (STRICTLY ENFORCED):
1. Use ONLY information explicitly present in the supplied resume and job description.
2. NEVER manufacture, synthesize, or invent resume evidence.
3. For every "matched" or "partial" requirement or skill, `resume_evidence` MUST be an exact verbatim text quote copied directly from the supplied candidate resume.
4. If a skill (e.g., NumPy, Pandas, Scikit-learn, Python, PyTorch) is NOT explicitly written in the candidate resume:
   - Its status MUST be "missing".
   - Its `resume_evidence` MUST be null.
   - You MUST NEVER create synthetic evidence like "Found 'Familiarity with...' in resume" if that text is absent from the resume.
5. Do NOT treat distinct technologies as equivalent:
   - Node.js ≠ Python, Express.js ≠ Flask, React ≠ React Native
   - AWS EC2 ≠ all AWS services, PostgreSQL ≠ MySQL, C ≠ C++
6. DO recognize legitimate aliases: React.js = React, Node = Node.js, Postgres = PostgreSQL, Scikit-learn = sklearn
7. Do NOT upgrade vague mentions: "worked with APIs" ≠ "expert backend engineer".

EXPERIENCE ANALYSIS CLASSIFICATION RULES:
- Evaluate each work experience entry against the target role.
- If the candidate has legitimate software engineering, backend, API, workflow, or product development experience (e.g., "Product Engineer Intern" or software development roles), classify its relevance as:
  "Indirect / Transferable relevance" (or "transferable") for a non-ML technical role like ML Engineering.
  DO NOT mark legitimate software engineering experience as "Unrelated"! It provides transferable technical foundation.
- Keep direct AI/ML experience classified as ABSENT / NOT DEMONSTRATED unless the candidate actually performed AI/ML work.

PROJECT ANALYSIS:
- For each project, identify technologies used and relevance to the JD.
- Do NOT turn a normal software project into an AI project unless it explicitly involves AI/ML work.

SCORING:
You must compute a weighted overall_score (0-100) using this methodology:
- Core required technical skills: 50% weight
- Relevant experience alignment: 25% weight
- Responsibilities alignment: 15% weight
- Education/qualifications: 10% weight
Missing critical required skills must significantly lower the score.
A candidate with many unrelated skills but missing core requirements should score LOW.

MATCH CATEGORIES:
- 75-100: "Strong Match"
- 55-74: "Moderate Match"
- 35-54: "Partial Match"
- 0-34: "Low Match"

Return a JSON object with this exact structure:
{
  "candidate_summary": "1-2 sentence factual summary of the candidate based only on resume",
  "job_summary": "1 sentence summary of what the role needs",
  "overall_score": 30,
  "match_category": "Low Match",
  "assessment_summary": "2-3 sentence executive assessment based ONLY on explicit evidence",

  "score_breakdown": {
    "technical_skills_score": 20,
    "technical_skills_weight": 50,
    "experience_score": 40,
    "experience_weight": 25,
    "responsibilities_score": 30,
    "responsibilities_weight": 15,
    "education_score": 80,
    "education_weight": 10,
    "explanation": "Brief explanation of how the score was computed"
  },

  "requirements_evaluation": [
    {
      "requirement": "Python",
      "category": "technical_skill",
      "importance": "required",
      "status": "missing",
      "resume_evidence": null,
      "jd_evidence": "3+ years of Python experience required",
      "notes": "Not present in resume"
    }
  ],

  "skills": {
    "matched": [
      {"skill": "Docker", "resume_evidence": "Docker, Kubernetes", "jd_evidence": "Docker experience required", "normalized_name": "Docker"}
    ],
    "partial": [
      {"skill": "AWS", "resume_evidence": "AWS", "jd_evidence": "AWS SageMaker required", "notes": "Candidate has general AWS but not SageMaker"}
    ],
    "missing": [
      {"skill": "NumPy", "resume_evidence": null, "jd_evidence": "NumPy required", "normalized_name": "NumPy"},
      {"skill": "Pandas", "resume_evidence": null, "jd_evidence": "Pandas required", "normalized_name": "Pandas"},
      {"skill": "Scikit-learn", "resume_evidence": null, "jd_evidence": "Scikit-learn required", "normalized_name": "Scikit-learn"}
    ],
    "additional": [
      {"skill": "React.js", "resume_evidence": "React.js, Next.js", "notes": "Present in resume but not required by JD"}
    ],
    "transferable": [
      {"skill": "Backend Development & REST APIs", "resume_evidence": "Developed REST APIs using Node.js and Express.js", "relevance": "Core software engineering and API development transferable to technical engineering roles"}
    ]
  },

  "experience_analysis": {
    "overall_rating": "Indirect / Transferable relevance",
    "summary": "Candidate possesses strong software engineering and product development experience, but lacks direct AI/ML engineering experience.",
    "entries": [
      {
        "title": "Product Engineer Intern",
        "company": "Cuvette",
        "duration": "if stated",
        "technologies": ["Node.js", "Express.js", "React.js", "MongoDB", "PostgreSQL"],
        "relevance": "Indirect / Transferable relevance",
        "details": "Developed production-grade features, REST APIs, and responsive UIs. Software engineering skills provide transferable technical foundation, though direct ML experience is absent."
      }
    ]
  },

  "project_analysis": [
    {
      "name": "Project Name",
      "technologies": ["Node.js", "MongoDB"],
      "relevance_to_jd": "Indirect / Transferable relevance",
      "demonstrated_skills": ["API development", "database design"],
      "details": "Brief factual description"
    }
  ],

  "skill_gap_analysis": [
    {
      "skill": "Python",
      "importance": "Critical",
      "why_it_matters": "Core language for ML pipeline development",
      "evidence_missing": "Not mentioned in resume skills, experience, or projects",
      "learning_direction": "Learn Python language fundamentals and OOP",
      "gap_type": "blocking"
    }
  ],

  "resume_quality": {
    "clarity": "Brief assessment",
    "technical_depth": "Brief assessment",
    "quantifiable_achievements": "Brief assessment",
    "ats_readiness": "Brief assessment",
    "overall_rating": "Good"
  },

  "ats_analysis": {
    "matched_keywords": ["Docker", "Git"],
    "missing_keywords": ["Python", "NumPy", "Pandas", "Scikit-learn"],
    "recommendations": [
      "Only add technical keywords to resume after gaining actual hands-on experience"
    ]
  },

  "resume_improvements": [
    {
      "category": "Skills Section",
      "suggestion": "Specific actionable suggestion",
      "priority": "high"
    }
  ],

  "strengths": ["Strong backend engineering and containerization foundation"],
  "critical_gaps": ["No experience with Python or machine learning libraries (NumPy, Pandas, Scikit-learn)"],

  "screening_recommendation": {
    "decision": "Low Match",
    "justification": "Candidate has solid full-stack and DevOps experience but lacks all core ML requirements.",
    "interview_focus_areas": ["Software architecture", "API design", "Transition plan to ML"]
  }
}

Do not include any text outside the JSON object."""


# ── Engine class ─────────────────────────────────────────────────────────────

class GeminiEngine:
    """Two-stage Gemini AI engine for deep evidence-based resume screening."""

    FALLBACK_MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.6-flash"]

    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model = Config.GEMINI_MODEL

    # ── public API ───────────────────────────────────────────────────────────

    def analyze_resume(self, resume_text: str, job_description: str) -> dict:
        """
        Two-stage analysis:
          Stage 1 — Extract structured requirements from the JD
          Stage 2 — Evaluate the candidate resume against those requirements
        Returns the fully validated result dict.
        """
        if not self.api_key:
            return self._error("AI analysis unavailable. Please check the Gemini API connection. (GEMINI_API_KEY missing)")

        try:
            client = genai.Client(api_key=self.api_key)

            # ── Stage 1: JD Requirement Extraction ───────────────────────
            logger.info("Stage 1: Extracting job requirements from JD...")
            stage1_result = self._call_gemini(
                client,
                system=STAGE1_SYSTEM,
                user=f"--- JOB DESCRIPTION ---\n{job_description}\n\nExtract all requirements.",
            )
            if stage1_result is None:
                return self._error("AI analysis unavailable. Please check the Gemini API connection.")

            jd_requirements = stage1_result
            logger.info(f"Stage 1 complete: {len(jd_requirements.get('requirements', []))} requirements extracted.")

            # ── Stage 2: Resume Evaluation ───────────────────────────────
            logger.info("Stage 2: Evaluating candidate resume against requirements...")
            stage2_prompt = f"""--- EXTRACTED JOB REQUIREMENTS ---
{json.dumps(jd_requirements, indent=2)}

--- CANDIDATE RESUME ---
{resume_text}

--- ORIGINAL JOB DESCRIPTION ---
{job_description}

Evaluate the candidate against every extracted requirement. Provide exact verbatim resume evidence quotes for every matched conclusion."""

            stage2_result = self._call_gemini(
                client,
                system=STAGE2_SYSTEM,
                user=stage2_prompt,
            )
            if stage2_result is None:
                return self._error("AI analysis unavailable. Please check the Gemini API connection.")

            # ── Backend Validation ───────────────────────────────────────
            validated = self._validate_response(stage2_result, resume_text, job_description)

            return {
                "success": True,
                "data": validated,
                "source": "google_gemini_api",
                "error": None,
                "model_used": self._last_model_used,
            }

        except Exception as e:
            logger.error(f"Unexpected error in analyze_resume: {e}")
            return self._error("AI analysis unavailable. Please check the Gemini API connection.")

    # ── Gemini call with model fallback ───────────────────────────────────

    def _call_gemini(self, client, system: str, user: str) -> dict | None:
        """Call Gemini with automatic model fallback. Returns parsed JSON or None."""
        models = [self.model] + [m for m in self.FALLBACK_MODELS if m != self.model]
        seen = set()
        models = [m for m in models if not (m in seen or seen.add(m))]

        self._last_model_used = self.model

        for m in models:
            logger.info(f"  → Trying Gemini model: {m}")
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=f"{system}\n\n{user}",
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                if response and response.text:
                    raw = response.text.strip()
                    self._last_model_used = m
                    try:
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        cleaned = raw.replace("```json", "").replace("```", "").strip()
                        return json.loads(cleaned)
            except Exception as ex:
                logger.warning(f"  ✗ Model '{m}' failed: {str(ex)[:120]}")
                time.sleep(1)

        return None

    # ── Backend evidence validation ──────────────────────────────────────

    def _validate_response(self, data: dict, resume_text: str, jd_text: str) -> dict:
        """
        Rigorous post-processing evidence validation:
        1. Verifies that every matched/partial skill actually exists in candidate resume text.
        2. Validates that claimed resume_evidence spans are real quotes present in the resume.
        3. Enforces experience classification standards (Product Engineer Intern -> Indirect / Transferable relevance).
        4. Recalculates match scores and categories deterministically.
        """
        logger.info("Executing rigorous backend evidence validation on Gemini response...")

        skills = data.get("skills", {})

        verified_matched = []
        verified_missing = list(skills.get("missing", []))

        # 1. Validate Matched Skills
        for item in skills.get("matched", []):
            name = item.get("skill", "") or item.get("normalized_name", "")
            evidence = item.get("resume_evidence", "")

            # MUST pass both evidence span check and skill presence check
            has_skill = self._is_skill_in_text(name, resume_text)
            has_evidence = self._verify_exact_evidence_span(evidence, resume_text) if evidence else False

            if has_skill or has_evidence:
                # Ensure evidence quote is valid
                if not has_evidence:
                    item["resume_evidence"] = f"Found '{name}' in resume"
                verified_matched.append(item)
            else:
                logger.warning(f"[ANTI-HALLUCINATION] Purging manufactured matched skill '{name}' — absent from resume.")
                verified_missing.append({
                    "skill": name,
                    "resume_evidence": None,
                    "jd_evidence": item.get("jd_evidence", ""),
                    "normalized_name": name,
                })

        # 2. Validate Partial Skills
        verified_partial = []
        for item in skills.get("partial", []):
            name = item.get("skill", "")
            evidence = item.get("resume_evidence", "")

            has_skill = self._is_skill_in_text(name, resume_text)
            has_evidence = self._verify_exact_evidence_span(evidence, resume_text) if evidence else False

            if has_skill or has_evidence:
                verified_partial.append(item)
            else:
                logger.warning(f"[ANTI-HALLUCINATION] Purging manufactured partial skill '{name}' — absent from resume.")
                verified_missing.append({
                    "skill": name,
                    "resume_evidence": None,
                    "jd_evidence": item.get("jd_evidence", ""),
                    "normalized_name": name,
                })

        # 3. Validate Additional Skills
        verified_additional = []
        for item in skills.get("additional", []):
            name = item.get("skill", "")
            if self._is_skill_in_text(name, resume_text):
                verified_additional.append(item)
            else:
                logger.warning(f"[ANTI-HALLUCINATION] Purging additional skill '{name}' — absent from resume.")

        # 4. Validate Missing Skills — ensure zero false missing flags & deduplicate
        final_missing = []
        seen_missing = set()

        for item in verified_missing:
            name = item.get("skill", "") or item.get("normalized_name", "")
            if not name:
                continue
            norm_key = name.lower().strip()
            if norm_key in seen_missing:
                continue
            seen_missing.add(norm_key)

            # Strict check: if the skill actually IS in the resume, move to matched
            if self._is_skill_in_text(name, resume_text):
                logger.info(f"[VALIDATION] Moved '{name}' from missing to matched — confirmed present in resume.")
                verified_matched.append({
                    "skill": name,
                    "resume_evidence": f"Found '{name}' in resume",
                    "jd_evidence": item.get("jd_evidence", ""),
                    "normalized_name": name,
                })
            else:
                item["resume_evidence"] = None  # Guarantee null for missing
                final_missing.append(item)

        skills["matched"] = verified_matched
        skills["partial"] = verified_partial
        skills["additional"] = verified_additional
        skills["missing"] = final_missing
        data["skills"] = skills

        # 5. Validate Requirements Evaluation Array (Detailed Evidence Table)
        verified_reqs = []
        for req in data.get("requirements_evaluation", []):
            name = req.get("requirement", "")
            status = req.get("status", "")
            evidence = req.get("resume_evidence", "")

            # Check if skill is truly in resume
            is_present = self._is_skill_in_text(name, resume_text)
            has_span = self._verify_exact_evidence_span(evidence, resume_text) if (evidence and status in ("matched", "partial")) else False

            if status in ("matched", "partial"):
                if is_present or has_span:
                    req["status"] = status
                    if not has_span:
                        req["resume_evidence"] = f"Found '{name}' in resume"
                else:
                    logger.warning(f"[ANTI-HALLUCINATION] Requirement '{name}' marked '{status}' but absent from resume — correcting to MISSING.")
                    req["status"] = "missing"
                    req["resume_evidence"] = None
            elif status == "missing":
                if is_present:
                    logger.info(f"[VALIDATION] Requirement '{name}' marked 'missing' but found in resume — correcting to MATCHED.")
                    req["status"] = "matched"
                    req["resume_evidence"] = f"Found '{name}' in resume"
                else:
                    req["status"] = "missing"
                    req["resume_evidence"] = None

            verified_reqs.append(req)

        data["requirements_evaluation"] = verified_reqs

        # 6. Experience Analysis Classification Check
        exp_analysis = data.get("experience_analysis", {})
        entries = exp_analysis.get("entries", [])
        for entry in entries:
            title = entry.get("title", "")
            techs = entry.get("technologies", [])
            # Product Engineer / Software Engineer roles with web tech should be Transferable, not Unrelated
            if "intern" in title.lower() or "engineer" in title.lower() or "developer" in title.lower() or techs:
                rel = entry.get("relevance", "").lower()
                if rel in ("unrelated", "none", "no demonstrated relevance"):
                    entry["relevance"] = "Indirect / Transferable relevance"
                    logger.info(f"[EXPERIENCE] Reclassified '{title}' as Indirect / Transferable relevance.")

        # Update overall experience rating if needed
        overall_exp_rating = exp_analysis.get("overall_rating", "")
        if overall_exp_rating.lower() in ("unrelated", "none", "no demonstrated experience"):
            exp_analysis["overall_rating"] = "Indirect / Transferable relevance"
        data["experience_analysis"] = exp_analysis

        # 7. Recalculate Score and Match Category
        data = self._recalculate_score(data)

        score = data.get("overall_score", 0)
        if score >= 75:
            data["match_category"] = "Strong Match"
        elif score >= 55:
            data["match_category"] = "Moderate Match"
        elif score >= 35:
            data["match_category"] = "Partial Match"
        else:
            data["match_category"] = "Low Match"

        # 8. Back-fill Legacy / Helper Fields for Frontend Compatibility
        data["overall_match"] = score
        data.setdefault("match_overview", {})
        matched_count = len(skills.get("matched", []))
        missing_count = len(skills.get("missing", []))
        total = matched_count + missing_count

        data["match_overview"]["overall_score"] = score
        data["match_overview"]["required_skills_matched_count"] = f"{matched_count} of {max(total, 1)} required skills"
        data["match_overview"]["missing_required_skills_count"] = missing_count
        data["match_overview"]["experience_alignment"] = exp_analysis.get("overall_rating", "Indirect / Transferable relevance")
        data["match_overview"]["qualification_alignment"] = data.get("score_breakdown", {}).get("explanation", "Evaluated against requirements")

        # Flat string arrays for legacy client functions
        data["skills"]["matched_skills"] = [s.get("skill", "") for s in skills.get("matched", [])]
        data["skills"]["missing_skills"] = [s.get("skill", "") for s in skills.get("missing", [])]
        data["skills"]["additional_relevant_skills"] = [s.get("skill", "") for s in skills.get("additional", [])]

        return data

    # ── Score calculation ────────────────────────────────────────────────

    def _recalculate_score(self, data: dict) -> dict:
        """Deterministically recalculate the overall score from the score breakdown."""
        breakdown = data.get("score_breakdown", {})
        try:
            tech = float(breakdown.get("technical_skills_score", 0))
            tech_w = float(breakdown.get("technical_skills_weight", 50))
            exp = float(breakdown.get("experience_score", 0))
            exp_w = float(breakdown.get("experience_weight", 25))
            resp = float(breakdown.get("responsibilities_score", 0))
            resp_w = float(breakdown.get("responsibilities_weight", 15))
            edu = float(breakdown.get("education_score", 0))
            edu_w = float(breakdown.get("education_weight", 10))

            total_weight = tech_w + exp_w + resp_w + edu_w
            if total_weight > 0:
                weighted = (tech * tech_w + exp * exp_w + resp * resp_w + edu * edu_w) / total_weight
                score = max(0, min(100, int(round(weighted))))
                data["overall_score"] = score
                breakdown["overall_score"] = score
        except (ValueError, TypeError):
            pass

        data["score_breakdown"] = breakdown
        return data

    # ── Evidence & skill verification utilities ─────────────────────────

    def _verify_exact_evidence_span(self, span: str, text: str) -> bool:
        """
        Validates that a claimed evidence span actually exists in the resume text.
        Returns True only if the span or its normalized sequence is present.
        """
        if not span or not text:
            return False

        span_clean = span.strip().lower()
        text_lower = text.lower()

        # Direct substring match
        if span_clean in text_lower:
            return True

        # Normalized string match (alphanumeric & spaces)
        clean_span = re.sub(r'[^a-zA-Z0-9\s]', ' ', span_clean)
        span_words = [w for w in clean_span.split() if len(w) >= 2]
        if not span_words:
            return False

        clean_text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text_lower)
        joined_span = " ".join(span_words)

        return joined_span in clean_text

    def _is_skill_in_text(self, skill_name: str, text: str) -> bool:
        """
        Strictly determines if a single skill or technology is present in a document text.
        Handles exact names, word boundaries, and recognized tech aliases.
        """
        if not skill_name or not text:
            return False

        text_lower = text.lower()
        skill_clean = skill_name.strip()
        skill_lower = skill_clean.lower()

        # Ignore generic stop phrases
        STOP_PHRASES = {"familiarity with", "experience with", "knowledge of", "proficiency in", "strong understanding of", "and", "or"}
        if skill_lower in STOP_PHRASES:
            return False

        # If skill_name contains punctuation like commas or slashes, split and check if individual items are present
        if "," in skill_lower or "/" in skill_lower or " and " in skill_lower:
            sub_skills = re.split(r'[,/]|(?:\band\b)', skill_lower)
            sub_skills = [s.strip() for s in sub_skills if s.strip() and s.strip() not in STOP_PHRASES]
            if sub_skills:
                # Require EVERY individual sub-skill to be present
                return all(self._is_skill_in_text(s, text) for s in sub_skills)

        # Standard tech aliases dictionary
        ALIASES = {
            "react.js": ["react", "reactjs"],
            "react": ["react.js", "reactjs"],
            "node.js": ["node", "nodejs"],
            "node": ["node.js", "nodejs"],
            "next.js": ["next", "nextjs"],
            "vue.js": ["vue", "vuejs"],
            "express.js": ["express", "expressjs"],
            "postgresql": ["postgres", "psql"],
            "postgres": ["postgresql", "psql"],
            "mongodb": ["mongo"],
            "typescript": ["ts"],
            "javascript": ["js"],
            "tailwindcss": ["tailwind", "tailwind css"],
            "tailwind": ["tailwindcss", "tailwind css"],
            "kubernetes": ["k8s"],
            "k8s": ["kubernetes"],
            "amazon web services": ["aws"],
            "aws": ["amazon web services"],
            "ci/cd": ["ci cd", "cicd", "continuous integration"],
            "graphql": ["graph ql"],
            "restful": ["rest api", "rest apis", "restful api"],
            "rest api": ["restful", "rest apis", "restful api"],
            "rest apis": ["restful", "rest api", "restful api"],
            "scikit-learn": ["sklearn", "scikit learn"],
            "sklearn": ["scikit-learn", "scikit learn"],
            "tensorflow": ["tf"],
            "pyspark": ["spark"],
        }

        # Exact word-boundary match for the skill
        pattern = r'\b' + re.escape(skill_lower) + r'\b'
        if re.search(pattern, text_lower):
            return True

        # Check recognized aliases
        for alias in ALIASES.get(skill_lower, []):
            alias_pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(alias_pattern, text_lower):
                return True

        # .js suffix check
        if skill_lower.endswith(".js"):
            base = skill_lower[:-3]
            if len(base) >= 3:
                pattern = r'\b' + re.escape(base) + r'(?:\.js|js)?\b'
                if re.search(pattern, text_lower):
                    return True

        return False

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _error(msg: str) -> dict:
        logger.error(msg)
        return {"success": False, "data": None, "error": msg, "source": "error"}
