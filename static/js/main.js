/**
 * AI Resume Screening & Skill Gap Analyzer - Client Script
 */

document.addEventListener('DOMContentLoaded', () => {
    const navItems = document.querySelectorAll('.nav-item');
    const viewPanels = document.querySelectorAll('.view-panel');
    const formAnalyzer = document.getElementById('form-analyzer');
    const btnModeFile = document.getElementById('btn-mode-file');
    const btnModeText = document.getElementById('btn-mode-text');
    const wrapperFileInput = document.getElementById('wrapper-file-input');
    const wrapperTextInput = document.getElementById('wrapper-text-input');
    const dropzone = document.getElementById('dropzone');
    const resumeFileInput = document.getElementById('resume-file-input');
    const selectedFileBadge = document.getElementById('selected-file-badge');
    const fileNameText = document.getElementById('file-name-text');
    const btnRemoveFile = document.getElementById('btn-remove-file');
    const fileIconType = document.getElementById('file-icon-type');
    const resumeTextInput = document.getElementById('resume-text-input');
    const jdTextInput = document.getElementById('jd-text-input');
    const resultsPanel = document.getElementById('results-panel');
    const resultsLoader = document.getElementById('results-loader');
    const resultsContent = document.getElementById('results-content');
    const systemAlert = document.getElementById('system-alert');
    const systemAlertMsg = document.getElementById('system-alert-msg');
    const statusText = document.getElementById('status-text');

    const evaluationHistory = [];
    let currentInputMode = 'file';
    let selectedFile = null;

    checkSystemStatus();

    async function checkSystemStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.config && data.config.api_key_configured) {
                statusText.textContent = `Gemini AI Ready (${data.config.model})`;
            } else {
                statusText.textContent = 'Gemini API Key Missing';
                showSystemAlert('Warning: Gemini API key is not configured in .env file.');
            }
        } catch (err) {
            statusText.textContent = 'Backend Offline';
        }
    }

    // Navigation
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const viewName = item.getAttribute('data-view');
            navItems.forEach(n => n.classList.remove('active'));
            viewPanels.forEach(v => v.classList.remove('active'));
            item.classList.add('active');
            document.getElementById(`view-${viewName}`).classList.add('active');
        });
    });

    window.switchToScreeningView = function() {
        navItems.forEach(n => n.classList.remove('active'));
        viewPanels.forEach(v => v.classList.remove('active'));
        document.querySelector('[data-view="screening"]').classList.add('active');
        document.getElementById('view-screening').classList.add('active');
    };

    // File vs Text toggle
    btnModeFile.addEventListener('click', () => {
        currentInputMode = 'file';
        btnModeFile.classList.add('active'); btnModeText.classList.remove('active');
        wrapperFileInput.classList.remove('hidden'); wrapperTextInput.classList.add('hidden');
    });
    btnModeText.addEventListener('click', () => {
        currentInputMode = 'text';
        btnModeText.classList.add('active'); btnModeFile.classList.remove('active');
        wrapperTextInput.classList.remove('hidden'); wrapperFileInput.classList.add('hidden');
    });

    // File upload
    dropzone.addEventListener('click', () => resumeFileInput.click());
    resumeFileInput.addEventListener('change', (e) => { if (e.target.files?.[0]) handleFileSelected(e.target.files[0]); });
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.style.borderColor = 'var(--accent-primary)'; dropzone.style.backgroundColor = 'var(--accent-light)'; });
    dropzone.addEventListener('dragleave', (e) => { e.preventDefault(); dropzone.style.borderColor = 'var(--border-input)'; dropzone.style.backgroundColor = '#fdfdfd'; });
    dropzone.addEventListener('drop', (e) => { e.preventDefault(); dropzone.style.borderColor = 'var(--border-input)'; dropzone.style.backgroundColor = '#fdfdfd'; if (e.dataTransfer.files?.[0]) handleFileSelected(e.dataTransfer.files[0]); });

    function handleFileSelected(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['pdf', 'docx', 'txt'].includes(ext)) { alert('Unsupported file type.'); return; }
        selectedFile = file;
        fileNameText.textContent = file.name;
        if (ext === 'pdf') fileIconType.className = 'fa-solid fa-file-pdf text-danger';
        else if (ext === 'docx') fileIconType.className = 'fa-solid fa-file-word text-info';
        else fileIconType.className = 'fa-solid fa-file-lines text-muted';
        dropzone.classList.add('hidden'); selectedFileBadge.classList.remove('hidden');
    }
    btnRemoveFile.addEventListener('click', () => { selectedFile = null; resumeFileInput.value = ''; selectedFileBadge.classList.add('hidden'); dropzone.classList.remove('hidden'); });

    // Form Submission
    formAnalyzer.addEventListener('submit', async (e) => {
        e.preventDefault(); hideSystemAlert();
        const jdText = jdTextInput.value.trim();
        if (!jdText) return alert('Please enter a job description.');
        let formData = new FormData(), payloadJson = {}, isMultipart = false;
        if (currentInputMode === 'file') {
            if (!selectedFile) return alert('Please upload a resume file.');
            formData.append('resume_file', selectedFile); formData.append('job_description', jdText); isMultipart = true;
        } else {
            const resumeText = resumeTextInput.value.trim();
            if (!resumeText) return alert('Please paste resume text.');
            payloadJson = { resume_text: resumeText, job_description: jdText, filename: 'Pasted Resume Text' };
        }
        showLoader();
        try {
            let response;
            if (isMultipart) { response = await fetch('/api/analyze', { method: 'POST', body: formData }); }
            else { response = await fetch('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payloadJson) }); }
            const data = await response.json(); hideLoader();
            if (!response.ok || (data.error && !data.data)) { showSystemAlert(data.error || 'Failed to analyze resume.'); return; }
            if (data.error) showSystemAlert(data.error);
            renderResults(data.data, data.metadata);
            recordHistoryItem(data.data, data.metadata);
        } catch (err) { hideLoader(); showSystemAlert('Network Error: Failed to reach backend.'); }
    });

    // ── Render Results ──────────────────────────────────────────────────
    function renderResults(data, metadata) {
        resultsContent.classList.remove('hidden');
        const score = data.overall_score || data.overall_match || 0;
        const category = data.match_category || 'Evaluated';

        // Summary banner
        document.getElementById('score-circle-val').textContent = `${score}%`;
        document.getElementById('stat-score').textContent = `${score}%`;
        const badge = document.getElementById('summary-decision-badge');
        badge.textContent = category;
        if (score >= 75) { badge.style.backgroundColor = 'var(--status-success-bg)'; badge.style.color = 'var(--status-success)'; badge.style.borderColor = 'var(--status-success-border)'; }
        else if (score >= 55) { badge.style.backgroundColor = 'var(--status-warning-bg)'; badge.style.color = 'var(--status-warning)'; badge.style.borderColor = 'var(--status-warning-border)'; }
        else { badge.style.backgroundColor = 'var(--status-danger-bg)'; badge.style.color = 'var(--status-danger)'; badge.style.borderColor = 'var(--status-danger-border)'; }
        document.getElementById('summary-quote-text').textContent = data.assessment_summary || 'Analysis complete.';

        // Score Breakdown
        const bd = data.score_breakdown || {};
        const grid = document.getElementById('score-breakdown-grid');
        grid.innerHTML = '';
        const dims = [
            { label: 'Technical Skills', score: bd.technical_skills_score, weight: bd.technical_skills_weight || 50 },
            { label: 'Experience', score: bd.experience_score, weight: bd.experience_weight || 25 },
            { label: 'Responsibilities', score: bd.responsibilities_score, weight: bd.responsibilities_weight || 15 },
            { label: 'Education', score: bd.education_score, weight: bd.education_weight || 10 },
        ];
        dims.forEach(d => {
            const sc = d.score !== undefined ? d.score : '—';
            grid.innerHTML += `<div class="overview-stat-card"><span class="stat-label">${esc(d.label)} (${d.weight}% weight)</span><span class="stat-value">${sc}%</span></div>`;
        });
        const explEl = document.getElementById('score-explanation');
        explEl.textContent = bd.explanation || '';
        explEl.style.cssText = 'font-size:0.85rem;color:var(--text-secondary);margin-top:8px;padding:0 4px;';

        // Match Overview
        const ov = data.match_overview || {};
        document.getElementById('stat-skills-matched').textContent = ov.required_skills_matched_count || '—';
        document.getElementById('stat-skills-missing').textContent = ov.missing_required_skills_count !== undefined ? ov.missing_required_skills_count : '—';
        document.getElementById('stat-exp-align').textContent = ov.experience_alignment || '—';
        document.getElementById('stat-qual-align').textContent = ov.qualification_alignment || '—';

        // Skills chips
        const sk = data.skills || {};
        renderEvidenceChips('chips-matched', sk.matched || [], 'chip-success');
        renderEvidenceChips('chips-missing', sk.missing || [], 'chip-danger');
        renderEvidenceChips('chips-additional', sk.additional || [], 'chip-muted');
        renderEvidenceChips('chips-partial', sk.partial || [], 'chip-warning');
        renderEvidenceChips('chips-transferable', sk.transferable || [], 'chip-info');

        // Hide partial/transferable sections if empty
        toggleSection('partial-skills-block', (sk.partial || []).length > 0);
        toggleSection('transferable-skills-block', (sk.transferable || []).length > 0);

        // Requirements Evidence Table
        const evTbody = document.getElementById('tbody-evidence');
        evTbody.innerHTML = '';
        const reqs = data.requirements_evaluation || [];
        if (reqs.length === 0) {
            evTbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No detailed requirements available.</td></tr>';
        } else {
            reqs.forEach(r => {
                const statusCls = r.status === 'matched' ? 'text-success' : r.status === 'missing' ? 'text-danger' : r.status === 'partial' ? 'text-warning-dark' : 'text-muted';
                evTbody.innerHTML += `<tr>
                    <td><strong>${esc(r.requirement)}</strong></td>
                    <td>${esc(r.category || '—')}</td>
                    <td>${esc(r.importance || '—')}</td>
                    <td><span class="${statusCls}" style="font-weight:600;">${esc(r.status || '—')}</span></td>
                    <td style="font-size:0.82rem;">${r.resume_evidence ? esc(r.resume_evidence) : '<span style="color:var(--text-dim);">—</span>'}</td>
                    <td style="font-size:0.82rem;">${r.jd_evidence ? esc(r.jd_evidence) : '<span style="color:var(--text-dim);">—</span>'}</td>
                </tr>`;
            });
        }

        // Skill Gap Analysis
        const gapTbody = document.getElementById('tbody-skill-gaps');
        gapTbody.innerHTML = '';
        const gaps = data.skill_gap_analysis || [];
        if (gaps.length === 0) {
            gapTbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No critical skill gaps identified.</td></tr>';
        } else {
            gaps.forEach(g => {
                const impCls = (g.importance || '').toLowerCase() === 'critical' ? 'text-danger' : (g.importance || '').toLowerCase() === 'high' ? 'text-danger' : 'text-secondary';
                gapTbody.innerHTML += `<tr>
                    <td><strong>${esc(g.skill)}</strong></td>
                    <td><span class="${impCls}" style="font-weight:600;">${esc(g.importance || 'Medium')}</span></td>
                    <td>${esc(g.gap_type || '—')}</td>
                    <td>${esc(g.why_it_matters || g.reason || '')}</td>
                    <td style="font-size:0.82rem;">${esc(g.evidence_missing || '')}</td>
                    <td>${esc(g.learning_direction || g.recommendation || '')}</td>
                </tr>`;
            });
        }

        // Experience Analysis
        const exp = data.experience_analysis || {};
        document.getElementById('exp-rating-badge').textContent = exp.overall_rating || exp.rating || 'Evaluated';
        document.getElementById('exp-details-text').textContent = exp.summary || exp.details || 'See entries below.';
        const expEntries = document.getElementById('experience-entries');
        expEntries.innerHTML = '';
        (exp.entries || []).forEach(e => {
            const relCls = e.relevance === 'direct' ? 'chip-success' : e.relevance === 'transferable' ? 'chip-info' : 'chip-muted';
            expEntries.innerHTML += `<div class="improvement-item" style="margin-top:8px;">
                <div style="flex:1;">
                    <strong>${esc(e.title || '—')}</strong> at ${esc(e.company || '—')} ${e.duration ? '(' + esc(e.duration) + ')' : ''}
                    <span class="chip ${relCls}" style="margin-left:8px;">${esc(e.relevance || '—')}</span>
                    <p style="font-size:0.82rem;color:var(--text-secondary);margin-top:4px;">${esc(e.details || '')}</p>
                    ${e.technologies?.length ? '<div style="margin-top:4px;">' + e.technologies.map(t => `<span class="chip chip-muted">${esc(t)}</span>`).join(' ') + '</div>' : ''}
                </div>
            </div>`;
        });

        // Project Analysis
        const projContainer = document.getElementById('project-entries');
        projContainer.innerHTML = '';
        const projects = data.project_analysis || [];
        toggleSection('section-projects', projects.length > 0);
        projects.forEach(p => {
            const relCls = p.relevance_to_jd === 'high' ? 'chip-success' : p.relevance_to_jd === 'medium' ? 'chip-warning' : 'chip-muted';
            projContainer.innerHTML += `<div class="improvement-item" style="margin-top:8px;">
                <div style="flex:1;">
                    <strong>${esc(p.name || 'Project')}</strong> <span class="chip ${relCls}" style="margin-left:8px;">${esc(p.relevance_to_jd || '—')} relevance</span>
                    <p style="font-size:0.82rem;color:var(--text-secondary);margin-top:4px;">${esc(p.details || '')}</p>
                    ${p.technologies?.length ? '<div style="margin-top:4px;">' + p.technologies.map(t => `<span class="chip chip-muted">${esc(t)}</span>`).join(' ') + '</div>' : ''}
                </div>
            </div>`;
        });

        // Resume Quality
        const rq = data.resume_quality || {};
        const rqGrid = document.getElementById('resume-quality-grid');
        rqGrid.innerHTML = '';
        toggleSection('section-resume-quality', Object.keys(rq).length > 0);
        const rqItems = [
            { label: 'Clarity', val: rq.clarity },
            { label: 'Technical Depth', val: rq.technical_depth },
            { label: 'Achievements', val: rq.quantifiable_achievements },
            { label: 'ATS Ready', val: rq.ats_readiness },
            { label: 'Overall', val: rq.overall_rating },
        ];
        rqItems.forEach(i => { if (i.val) rqGrid.innerHTML += `<div class="overview-stat-card"><span class="stat-label">${esc(i.label)}</span><span class="stat-value-text">${esc(i.val)}</span></div>`; });

        // ATS Analysis
        const ats = data.ats_analysis || {};
        const atsEl = document.getElementById('ats-content');
        atsEl.innerHTML = '';
        toggleSection('section-ats', (ats.matched_keywords?.length || ats.missing_keywords?.length));
        if (ats.matched_keywords?.length) {
            atsEl.innerHTML += '<div class="skills-block"><h4><i class="fa-solid fa-check text-success"></i> Matched Keywords</h4><div class="chips-container">' + ats.matched_keywords.map(k => `<span class="chip chip-success">${esc(k)}</span>`).join('') + '</div></div>';
        }
        if (ats.missing_keywords?.length) {
            atsEl.innerHTML += '<div class="skills-block" style="margin-top:8px;"><h4><i class="fa-solid fa-xmark text-danger"></i> Missing Keywords</h4><div class="chips-container">' + ats.missing_keywords.map(k => `<span class="chip chip-danger">${esc(k)}</span>`).join('') + '</div></div>';
        }
        if (ats.recommendations?.length) {
            atsEl.innerHTML += '<div style="margin-top:12px;">' + ats.recommendations.map(r => `<p style="font-size:0.82rem;color:var(--text-secondary);margin:4px 0;"><i class="fa-solid fa-angle-right" style="color:var(--accent-primary);margin-right:6px;"></i>${esc(r)}</p>`).join('') + '</div>';
        }

        // Strengths & Critical Gaps
        const sgGrid = document.getElementById('strengths-gaps-grid');
        sgGrid.innerHTML = '';
        const strengths = data.strengths || [];
        const critGaps = data.critical_gaps || [];
        toggleSection('section-strengths-gaps', strengths.length > 0 || critGaps.length > 0);
        if (strengths.length) {
            sgGrid.innerHTML += '<div class="skills-block"><h4><i class="fa-solid fa-thumbs-up text-success"></i> Strengths</h4><ul style="padding-left:18px;font-size:0.85rem;">' + strengths.map(s => `<li style="margin:4px 0;">${esc(s)}</li>`).join('') + '</ul></div>';
        }
        if (critGaps.length) {
            sgGrid.innerHTML += '<div class="skills-block"><h4><i class="fa-solid fa-thumbs-down text-danger"></i> Critical Gaps</h4><ul style="padding-left:18px;font-size:0.85rem;">' + critGaps.map(g => `<li style="margin:4px 0;">${esc(g)}</li>`).join('') + '</ul></div>';
        }

        // Resume Improvements
        const impContainer = document.getElementById('improvements-container');
        impContainer.innerHTML = '';
        (data.resume_improvements || []).forEach(imp => {
            impContainer.innerHTML += `<div class="improvement-item">
                <div class="improvement-category"><i class="fa-solid fa-angle-right"></i> ${esc(imp.category || 'Suggestion')} ${imp.priority ? `<span class="chip chip-${imp.priority === 'high' ? 'danger' : 'muted'}" style="margin-left:6px;font-size:0.7rem;">${esc(imp.priority)}</span>` : ''}</div>
                <div class="improvement-text">${esc(imp.suggestion || '')}</div>
            </div>`;
        });

        // Screening Recommendation
        const rec = data.screening_recommendation || {};
        document.getElementById('rec-decision-title').textContent = rec.decision || category;
        document.getElementById('rec-justification-text').textContent = rec.justification || 'Review complete.';
        const focusEl = document.getElementById('rec-focus-areas');
        focusEl.innerHTML = '';
        if (rec.interview_focus_areas?.length) {
            focusEl.innerHTML = '<p style="font-size:0.82rem;font-weight:600;margin-top:10px;color:var(--text-secondary);">Interview Focus Areas:</p><ul style="padding-left:18px;font-size:0.82rem;">' + rec.interview_focus_areas.map(a => `<li>${esc(a)}</li>`).join('') + '</ul>';
        }

        // Render dedicated Skill Gap Analysis tab view
        renderSkillGapView(data);

        resultsPanel.scrollIntoView({ behavior: 'smooth' });
    }

    function renderSkillGapView(data) {
        const placeholder = document.getElementById('skillgap-placeholder');
        const content = document.getElementById('skillgap-view-content');
        if (!placeholder || !content) return;

        placeholder.classList.add('hidden');
        content.classList.remove('hidden');

        const score = data.overall_score || data.overall_match || 0;
        const gaps = data.skill_gap_analysis || [];
        const missing = data.skills?.missing || [];
        const matched = data.skills?.matched || [];
        const transferable = data.skills?.transferable || [];

        const criticalCount = gaps.filter(g => (g.importance || '').toLowerCase() === 'critical' || (g.importance || '').toLowerCase() === 'high').length;

        let html = `
            <div class="summary-banner" style="margin-bottom: 24px;">
                <div class="score-box">
                    <div class="score-circle" style="border-color: ${score >= 75 ? 'var(--status-success)' : score >= 55 ? 'var(--status-warning)' : 'var(--status-danger)'}; color: ${score >= 75 ? 'var(--status-success)' : score >= 55 ? 'var(--status-warning)' : 'var(--status-danger)'};">${score}%</div>
                    <div class="score-details">
                        <span class="score-label">Technical Alignment</span>
                        <span class="badge-decision">${esc(data.match_category || 'Evaluated')}</span>
                    </div>
                </div>
                <div class="assessment-quote">
                    <span class="quote-title">Skill Gap Overview</span>
                    <p>Candidate possesses <strong>${matched.length} matched skills</strong>, but has <strong>${missing.length} skill gaps</strong> (${criticalCount} high/critical priority). Below is the interactive gap matrix and training roadmap.</p>
                </div>
            </div>

            <div class="report-section">
                <h3 class="section-title"><i class="fa-solid fa-list-check"></i> Skill Gap Severity Matrix</h3>
                <div class="gap-matrix-grid">
        `;

        if (gaps.length === 0 && missing.length === 0) {
            html += `<div class="empty-state-card" style="grid-column: span 3;"><p>No critical skill gaps identified for this candidate!</p></div>`;
        } else {
            const gapList = gaps.length > 0 ? gaps : missing.map(m => ({
                skill: typeof m === 'string' ? m : m.skill,
                importance: 'High',
                gap_type: 'missing',
                why_it_matters: 'Required by target job description',
                evidence_missing: 'Not mentioned in resume',
                learning_direction: 'Gain foundational knowledge and hands-on practice'
            }));

            gapList.forEach(g => {
                const imp = (g.importance || 'High').toLowerCase();
                const cardClass = imp === 'critical' ? 'critical' : imp === 'high' ? 'high' : 'medium';
                const badgeClass = imp === 'critical' ? 'chip-danger' : imp === 'high' ? 'chip-warning' : 'chip-info';

                html += `
                    <div class="gap-card ${cardClass}">
                        <div class="gap-card-header">
                            <span class="gap-card-title">${esc(g.skill)}</span>
                            <span class="chip ${badgeClass}">${esc(g.importance || 'High')}</span>
                        </div>
                        <div class="gap-detail-item">
                            <strong>Category / Gap Type</strong>
                            <span>${esc(g.gap_type || 'Required Skill Deficit')}</span>
                        </div>
                        <div class="gap-detail-item">
                            <strong>Why It Matters (Role Impact)</strong>
                            <span>${esc(g.why_it_matters || g.reason || 'Required requirement for target role')}</span>
                        </div>
                        <div class="gap-detail-item">
                            <strong>Proof of Absence</strong>
                            <span>${esc(g.evidence_missing || 'Not present in resume text')}</span>
                        </div>
                        <div class="learning-path-box">
                            <strong style="color: var(--accent-primary); display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                                <i class="fa-solid fa-graduation-cap"></i> Targeted Upskilling Pathway
                            </strong>
                            <span>${esc(g.learning_direction || g.recommendation || 'Focus on learning core fundamentals.')}</span>
                        </div>
                    </div>
                `;
            });
        }

        html += `
                </div>
            </div>

            <div class="report-section" style="margin-top: 24px;">
                <h3 class="section-title"><i class="fa-solid fa-arrow-right-to-city"></i> Transferable Skills & Learning Foundation</h3>
                <div class="narrative-card">
                    <p>While the candidate lacks specific direct requirements, their existing technical skills provide a foundation that can accelerate training:</p>
                    <div class="chips-container" style="margin-top: 12px;">
        `;

        if (transferable.length > 0) {
            transferable.forEach(t => {
                const name = typeof t === 'string' ? t : (t.skill || t.normalized_name);
                const desc = typeof t === 'object' ? (t.relevance || t.resume_evidence || '') : '';
                html += `<span class="chip chip-info" title="${esc(desc)}"><i class="fa-solid fa-arrow-right-arrow-left"></i> ${esc(name)}</span>`;
            });
        } else {
            html += `<span style="font-size: 0.85rem; color: var(--text-secondary);">No transferable skills logged.</span>`;
        }

        html += `
                    </div>
                </div>
            </div>
        `;

        content.innerHTML = html;
    }


    function renderEvidenceChips(containerId, items, chipClass) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = '';
        if (items.length === 0) { container.innerHTML = '<span style="font-size:0.8rem;color:var(--text-muted);">None</span>'; return; }
        items.forEach(item => {
            const name = typeof item === 'string' ? item : (item.skill || item.normalized_name || '');
            const evidence = typeof item === 'object' ? (item.resume_evidence || item.relevance || item.notes || '') : '';
            const span = document.createElement('span');
            span.className = `chip ${chipClass}`;
            span.textContent = name;
            if (evidence) span.title = evidence;
            container.appendChild(span);
        });
    }

    function toggleSection(id, show) {
        const el = document.getElementById(id);
        if (el) el.style.display = show ? '' : 'none';
    }

    // History
    function recordHistoryItem(data, metadata) {
        evaluationHistory.unshift({ id: evaluationHistory.length + 1, filename: metadata?.filename || 'Resume', score: data.overall_score || data.overall_match || 0, decision: data.screening_recommendation?.decision || data.match_category || 'Evaluated', data });
        updateHistoryTable();
    }
    function updateHistoryTable() {
        const tbody = document.getElementById('tbody-history');
        tbody.innerHTML = '';
        if (evaluationHistory.length === 0) { tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:32px;">No evaluations yet.</td></tr>'; return; }
        evaluationHistory.forEach(item => {
            tbody.innerHTML += `<tr><td>#${item.id}</td><td><strong>${esc(item.filename)}</strong></td><td><span style="font-weight:700;color:var(--accent-primary);">${item.score}%</span></td><td><span class="badge-decision" style="font-size:0.75rem;">${esc(item.decision)}</span></td><td><button class="btn btn-secondary btn-sm btn-view-hist" data-id="${item.id}"><i class="fa-solid fa-eye"></i> View</button></td></tr>`;
        });
        tbody.querySelectorAll('.btn-view-hist').forEach(btn => {
            btn.addEventListener('click', () => { const found = evaluationHistory.find(h => h.id === parseInt(btn.dataset.id)); if (found) { switchToScreeningView(); renderResults(found.data, { filename: found.filename }); } });
        });
    }

    // Helpers
    function showLoader() { resultsPanel.classList.remove('hidden'); resultsLoader.classList.remove('hidden'); resultsContent.classList.add('hidden'); resultsPanel.scrollIntoView({ behavior: 'smooth' }); }
    function hideLoader() { resultsLoader.classList.add('hidden'); }
    function showSystemAlert(msg) { systemAlert.classList.remove('hidden'); systemAlertMsg.textContent = msg; }
    function hideSystemAlert() { systemAlert.classList.add('hidden'); }
    function esc(str) { if (typeof str !== 'string') return str; return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;"); }
});
