/* ============================================================
   DataCleaner AI — app.js
   Handles: Upload, Scan, Chat/Clean, Preview, Export
   ============================================================ */

const API = "https://mustafahussein2000-datacleaner-api.hf.space";
let sessionId = null;
let currentFileName = null;
let auditLog = [];
let previewBeforeData = null;
let previewAfterData = null;
let currentTab = "before";
let healthChartInstance = null;
let currentSortCol = null;
let currentSortAsc = true;

// ============================================================
// SECTION SWITCHING
// ============================================================
function showSection(id) {
    document.querySelectorAll(".section").forEach(s => {
        s.classList.remove("active");
        s.classList.add("hidden");
    });
    const el = document.getElementById(id);
    el.classList.remove("hidden");
    el.classList.add("active");
}

// ============================================================
// DRAG & DROP UPLOAD ZONE
// ============================================================
const uploadZone = document.getElementById("uploadZone");
const fileInput = document.getElementById("fileInput");

uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadZone.classList.add("drag-over");
});
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("drag-over"));
uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
});
fileInput.addEventListener("change", (e) => {
    if (e.target.files[0]) handleFileUpload(e.target.files[0]);
});
uploadZone.addEventListener("click", (e) => {
    if (e.target.tagName !== "LABEL" && e.target.tagName !== "INPUT") {
        fileInput.click();
    }
});

// ============================================================
// FILE UPLOAD
// ============================================================
async function handleFileUpload(file) {
    const allowed = [".csv", ".xlsx", ".xls"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) {
        showToast("❌ يُدعم CSV و Excel فقط", "error");
        return;
    }

    showLoading("جاري رفع الملف وتحليله...");
    animateProgress();

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API}/upload`, { method: "POST", body: formData });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "فشل في رفع الملف");
        }
        const data = await res.json();
        sessionId = data.session_id;

        hideLoading();
        renderScanReport(data.scan_report);
        renderPreviewTable(data.preview, "before");
        previewBeforeData = data.preview;
        previewAfterData = data.preview;

        updateStats(
            data.scan_report.total_rows,
            data.scan_report.total_columns,
            data.scan_report.total_issues
        );

        document.getElementById("exportCard").classList.remove("hidden");
        showSection("section-workspace");
        showToast(`✅ تم رفع "${file.name}" بنجاح!`, "success");

    } catch (err) {
        hideLoading();
        showToast("❌ خطأ: " + err.message, "error");
    }
}

// ============================================================
// SCAN REPORT
// ============================================================
function renderScanReport(report) {
    // Health badge
    const healthBadge = document.getElementById("healthBadge");
    const score = report.health_score ?? 100;
    healthBadge.textContent = `صحة البيانات: ${score}%`;
    healthBadge.style.background = score > 70
        ? "rgba(0,230,118,0.1)" : score > 40
        ? "rgba(255,183,77,0.1)" : "rgba(255,82,82,0.1)";
    healthBadge.style.color = score > 70
        ? "var(--success)" : score > 40
        ? "var(--warning)" : "var(--danger)";
    healthBadge.style.borderColor = healthBadge.style.color;

    // Draw Chart.js Doughnut — safe re-render guard
    try {
        if (healthChartInstance) {
            healthChartInstance.destroy();
            healthChartInstance = null;
        }
        const canvas = document.getElementById('healthChart');
        // Reset canvas to clear any stale state from a previous chart
        const parent = canvas.parentElement;
        const newCanvas = document.createElement('canvas');
        newCanvas.id = 'healthChart';
        parent.replaceChild(newCanvas, canvas);

        const ctx = newCanvas.getContext('2d');
        healthChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['صحي', 'مشاكل محتملة'],
                datasets: [{
                    data: [score, 100 - score],
                    backgroundColor: [
                        score > 70 ? '#00e676' : (score > 40 ? '#ffb74d' : '#ff5252'),
                        'rgba(255, 255, 255, 0.05)'
                    ],
                    borderWidth: 0,
                    cutout: '75%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: true }
                }
            }
        });
    } catch (chartErr) {
        console.warn('Chart render skipped:', chartErr);
    }

    // Summary stats
    const summaryEl = document.getElementById("scanSummary");
    summaryEl.innerHTML = `
        <div class="scan-stat">
            <div class="scan-stat-value">${report.total_rows.toLocaleString()}</div>
            <div class="scan-stat-label">صف</div>
        </div>
        <div class="scan-stat">
            <div class="scan-stat-value">${report.total_columns}</div>
            <div class="scan-stat-label">عمود</div>
        </div>
    `;

    // Issues
    const list = document.getElementById("issuesList");
    if (!report.issues || report.issues.length === 0) {
        list.innerHTML = `<div class="issue-item low">✅ لم نجد مشاكل واضحة في البيانات</div>`;
        return;
    }
    list.innerHTML = report.issues.map(issue => `
        <div class="issue-item ${issue.severity}">
            <span class="issue-badge">${getIssueIcon(issue.type)}</span>
            <div class="issue-content">
                <div class="issue-message">${issue.message}</div>
                ${issue.suggestion ? `
                <div class="issue-suggestion">
                    <span class="suggestion-text">💡 ${issue.suggestion}</span>
                    <button class="btn-quick-fix" onclick="executeQuickFix('${issue.action_prompt.replace(/'/g, "\\'")}')">صلّحها بالـ AI ✨</button>
                </div>
                ` : ''}
            </div>
        </div>
    `).join("");
}

function executeQuickFix(prompt) {
    document.getElementById("chatInput").value = prompt;
    sendMessage();
}

function getIssueIcon(type) {
    const icons = {
        duplicates: "🔁",
        missing_values: "⬜",
        mixed_date_formats: "📅",
        arabic_numbers: "🔢",
        outliers: "🚨",
        mixed_language: "🔠",
        whitespace_issues: "␣",
        inconsistent_casing: "Aa"
    };
    return icons[type] || "⚠️";
}

// ============================================================
// PREVIEW TABLE
// ============================================================
function renderPreviewTable(preview, tab) {
    const wrapper = document.getElementById("tableWrapper");
    if (!preview || !preview.columns || !preview.data || preview.data.length === 0) {
        wrapper.innerHTML = `<p class="table-placeholder">لا توجد بيانات للعرض</p>`;
        return;
    }

    const cols = preview.columns;
    let rows = [...preview.data];

    // Apply Sorting
    if (currentSortCol) {
        rows.sort((a, b) => {
            const valA = a[currentSortCol];
            const valB = b[currentSortCol];
            if (valA === valB) return 0;
            if (valA === null || valA === "") return 1; // push nulls to bottom
            if (valB === null || valB === "") return -1;
            const res = String(valA).localeCompare(String(valB), undefined, {numeric: true});
            return currentSortAsc ? res : -res;
        });
    }

    const headerHTML = cols.map(c => {
        let arrow = "";
        let className = "sortable-header";
        if (c === currentSortCol) {
            arrow = currentSortAsc ? " <span style='color:var(--success);font-size:0.8rem'>▲</span>" : " <span style='color:var(--danger);font-size:0.8rem'>▼</span>";
        }
        return `<th onclick="sortTable('${c.replace(/'/g, "\\'")}')" class="${className}" style="cursor: pointer; user-select: none;" title="اضغط للترتيب">${c}${arrow}</th>`;
    }).join("");
    
    const rowsHTML = rows.map(row =>
        `<tr>${cols.map(c => {
            const val = row[c];
            if (val === null || val === "" || val === undefined) {
                return `<td class="null-cell">NULL</td>`;
            }
            return `<td>${String(val).substring(0, 60)}</td>`;
        }).join("")}</tr>`
    ).join("");

    wrapper.innerHTML = `
        <table>
            <thead><tr>${headerHTML}</tr></thead>
            <tbody>${rowsHTML}</tbody>
        </table>
    `;
}

function sortTable(colName) {
    if (currentSortCol === colName) {
        currentSortAsc = !currentSortAsc;
    } else {
        currentSortCol = colName;
        currentSortAsc = true; // default to ascending when a new column is clicked
    }
    renderPreviewTable(currentTab === "before" ? previewBeforeData : previewAfterData, currentTab);
}

function showTab(tab) {
    currentTab = tab;
    document.getElementById("tabBefore").classList.toggle("active", tab === "before");
    document.getElementById("tabAfter").classList.toggle("active", tab === "after");
    renderPreviewTable(tab === "before" ? previewBeforeData : previewAfterData, tab);
}

function updateStats(rows, cols, issues) {
    if (rows !== null && rows !== undefined) document.getElementById("statRows").textContent = rows.toLocaleString();
    if (cols !== null && cols !== undefined) document.getElementById("statCols").textContent = cols;
    if (issues !== null && issues !== undefined) document.getElementById("statIssues").textContent = issues;
}

// ============================================================
// CHAT / CLEAN
// ============================================================
async function sendMessage() {
    if (!sessionId) {
        showToast("⚠️ الرجاء رفع ملف أولاً", "error");
        return;
    }
    const input = document.getElementById("chatInput");
    const userText = input.value.trim();
    if (!userText) return;

    input.value = "";
    addChatBubble("user", userText);

    const sendBtn = document.getElementById("sendBtn");
    sendBtn.disabled = true;

    showLoading("الذكاء الاصطناعي يكتب الكود وينفذه...");

    const formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("user_request", userText);

    try {
        const res = await fetch(`${API}/clean`, { method: "POST", body: formData });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "فشل في المعالجة");
        }
        const data = await res.json();

        hideLoading();

        // Update chat
        const summary = data.audit_log?.map(e => e.detail).join(" • ") || "تم التنفيذ";
        addChatBubble("assistant", `✅ ${summary}`);

        // Update previews
        previewBeforeData = data.preview_before;
        previewAfterData = data.preview_after;
        showTab("after");

        // Refresh the scan report automatically with post-cleaning results
        if (data.scan_report) {
            renderScanReport(data.scan_report);
        }

        // Update stats
        updateStats(data.rows_after, null, null);

        // Show audit log
        appendAuditLog(data.audit_log);
        document.getElementById("auditCard").classList.remove("hidden");

        // Show export panel
        document.getElementById("exportCard").classList.remove("hidden");

        // Toggle undo button
        const undoBtn = document.getElementById("undoBtn");
        if (undoBtn) undoBtn.style.display = data.can_undo ? "flex" : "none";

        showToast("✅ تم التنفيذ بنجاح!", "success");

    } catch (err) {
        hideLoading();
        addChatBubble("assistant", `❌ خطأ: ${err.message}`);
        showToast("❌ " + err.message, "error");
    } finally {
        sendBtn.disabled = false;
    }
}

async function undoAction() {
    if (!sessionId) return;
    
    showLoading("جاري التراجع...");
    try {
        const formData = new FormData();
        formData.append("session_id", sessionId);
        
        const res = await fetch(`${API}/undo`, { method: "POST", body: formData });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "فشل التراجع");
        }
        const data = await res.json();
        
        hideLoading();
        
        // Re-render chat entirely
        const container = document.getElementById("chatMessages");
        container.innerHTML = `
            <div class="chat-bubble assistant">
                <div class="bubble-avatar">🤖</div>
                <div class="bubble-text">أهلاً! أنا جاهز لتنظيف بياناتك. أخبرني بما تريد تغييره.</div>
            </div>
        `;
        if (data.chat_history && data.chat_history.length > 0) {
            data.chat_history.forEach(msg => addChatBubble(msg.role, msg.content));
        }
        
        // Render audit log entirely
        document.getElementById("auditList").innerHTML = "";
        if (data.audit_log && data.audit_log.length > 0) {
            appendAuditLog(data.audit_log);
        } else {
            document.getElementById("auditCard").classList.add("hidden");
        }
        
        // Update after preview
        previewAfterData = data.preview_after;
        showTab("after");
        updateStats(data.rows_after, null, null);
        
        // Toggle undo button
        const undoBtn = document.getElementById("undoBtn");
        if (undoBtn) undoBtn.style.display = data.can_undo ? "flex" : "none";
        
        showToast("✅ " + data.message, "success");
    } catch (err) {
        hideLoading();
        showToast("❌ " + err.message, "error");
    }
}

function setInput(text) {
    document.getElementById("chatInput").value = text;
    document.getElementById("chatInput").focus();
}

function addChatBubble(role, text) {
    const container = document.getElementById("chatMessages");
    const div = document.createElement("div");
    div.className = `chat-bubble ${role}`;
    div.innerHTML = `
        <div class="bubble-avatar">${role === "user" ? "👤" : "🤖"}</div>
        <div class="bubble-text">${text}</div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// ============================================================
// AUDIT LOG
// ============================================================
function appendAuditLog(entries) {
    const list = document.getElementById("auditList");
    entries.forEach(entry => {
        const div = document.createElement("div");
        div.className = "audit-entry";
        div.innerHTML = `
            <span class="audit-action">${entry.action}</span>
            <span>${entry.detail} ${entry.impact ? "— " + entry.impact : ""}</span>
        `;
        list.appendChild(div);
    });
}

// ============================================================
// EXPORT
// ============================================================
async function exportData(type) {
    if (!sessionId) return;

    showLoading(`جاري تجهيز ملف الـ ${type.toUpperCase()}...`);

    try {
        const res = await fetch(`${API}/export/${sessionId}/${type}`);
        if (!res.ok) throw new Error("فشل التصدير");

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;

        const ext = { csv: "csv", excel: "xlsx", python: "py", pdf: "pdf", ipynb: "ipynb" }[type];
        a.download = `cleaned_data.${ext}`;
        a.click();
        URL.revokeObjectURL(url);

        hideLoading();
        showToast(`✅ تم تحميل ملف ${type.toUpperCase()} بنجاح!`, "success");
    } catch (err) {
        hideLoading();
        showToast("❌ فشل التصدير: " + err.message, "error");
    }
}

// ============================================================
// LOADING OVERLAY
// ============================================================
function showLoading(text = "جاري المعالجة...") {
    document.getElementById("loadingText").textContent = text;
    document.getElementById("loadingOverlay").classList.remove("hidden");
}
function hideLoading() {
    document.getElementById("loadingOverlay").classList.add("hidden");
}

// ============================================================
// PROGRESS ANIMATION
// ============================================================
function animateProgress() {
    const prog = document.getElementById("uploadProgress");
    const fill = document.getElementById("progressFill");
    prog.classList.remove("hidden");
    let p = 0;
    const interval = setInterval(() => {
        p = Math.min(p + Math.random() * 15, 90);
        fill.style.width = p + "%";
        if (p >= 90) clearInterval(interval);
    }, 200);
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================
function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(-20px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
