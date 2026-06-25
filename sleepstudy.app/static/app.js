// --- State Management ---
let currentSessionId = null;
let activeConnectors = [];
let hrBrChart = null;
let recoveryChart = null;
let snoreCoughChart = null;
let globalSleepAids = [];
let selectedSleepAids = new Set();
let selectedSleepDisruptors = new Set();

// --- DOM Elements ---
const elConnectorBadges = document.getElementById("connector-badges");
const elHistoryBody = document.getElementById("history-table-body");
const elEmptyState = document.getElementById("empty-analysis-state");
const elChartsContainer = document.getElementById("analysis-charts-container");
const elSessionTitle = document.getElementById("current-session-title");
const elSessionTime = document.getElementById("current-session-time");
const elSessionStats = document.getElementById("current-session-stats");
const elStatDuration = document.getElementById("stat-duration");
const elStatScore = document.getElementById("stat-score");
const elStatRestingHr = document.getElementById("stat-resting-hr");
const elStatAvgHrv = document.getElementById("stat-avg-hrv");
const elStatHrvStatus = document.getElementById("stat-hrv-status");
const elStatBodyBattery = document.getElementById("stat-body-battery");
const elStatSnores = document.getElementById("stat-snores");
const elSwimlanes = document.getElementById("stages-swimlane-container");

// Journal Elements
const elJournalLoaded = document.getElementById("journal-session-loaded");
const elJournalEmpty = document.getElementById("journal-session-empty");
const elJournalForm = document.getElementById("journal-form");
const elJournalNotes = document.getElementById("journal-notes");
const elJournalPosition = document.getElementById("journal-position");
const elJournalSleepAidsPool = document.getElementById("journal-sleep-aids-pool");
const elJournalSleepDisruptorsPool = document.getElementById("journal-sleep-disruptors-pool");
const elSleepAidsConfigList = document.getElementById("sleep-aids-config-list");
const elSleepDisruptorsConfigList = document.getElementById("sleep-disruptors-config-list");
const elAddSleepAidForm = document.getElementById("add-sleep-aid-form");
const elNewSleepAidName = document.getElementById("new-sleep-aid-name");
const elNewSleepAidCategory = document.getElementById("new-sleep-aid-category");

// Modal Elements
const elImportModal = document.getElementById("import-modal");
const elBtnOpenImport = document.getElementById("btn-open-import");
const elBtnCloseImport = document.getElementById("btn-close-import");
const elBtnCancelImport = document.getElementById("btn-cancel-import");
const elBtnSubmitImport = document.getElementById("btn-submit-import");
const elConnectorSelect = document.getElementById("import-connector-select");
const elDropZone = document.getElementById("drop-zone");
const elFileInput = document.getElementById("import-file-input");
const elImportFeedback = document.getElementById("import-feedback");

// Garmin Config Elements
const elGarminConfigForm = document.getElementById("garmin-config-form");
const elGarminEmail = document.getElementById("garmin-email");
const elGarminPassword = document.getElementById("garmin-password");
const elGarminStatusBadge = document.getElementById("garmin-status-badge");
const elGarminSyncDate = document.getElementById("garmin-sync-date");
const elBtnSyncGarmin = document.getElementById("btn-sync-garmin");
const elGarminSyncLog = document.getElementById("garmin-sync-log");
const elGarminRawSelect = document.getElementById("garmin-raw-select");
const elBtnCopyRawGarmin = document.getElementById("btn-copy-raw-garmin");
const elBtnDownloadRawGarmin = document.getElementById("btn-download-raw-garmin");

let selectedFile = null;

function saveTimezoneOffset() {
    try {
        const offsetMinutes = new Date().getTimezoneOffset();
        const offsetHours = -offsetMinutes / 60;
        fetch("/api/connectors/system/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ timezone_offset: offsetHours.toString() })
        });
    } catch (err) {
        console.error("Failed to save timezone offset:", err);
    }
}

// --- Initialize App ---
document.addEventListener("DOMContentLoaded", () => {
    // Restore sidebar state from localStorage
    const isSidebarCollapsed = localStorage.getItem("sidebar-collapsed") === "true";
    const layoutEl = document.querySelector(".app-layout");
    if (isSidebarCollapsed && layoutEl) {
        layoutEl.classList.add("sidebar-collapsed");
        const btnSidebarToggle = document.getElementById("sidebar-toggle");
        if (btnSidebarToggle) btnSidebarToggle.innerText = "▶";
    }

    saveTimezoneOffset();
    fetchConnectors();
    fetchSessions();
    fetchSleepAids();
    setupEventListeners();
    setupNavigation();
    setupEndpointUrls();
    loadGarminConfig();
    loadGarminRawFiles();
});

// --- Tab Navigation Setup ---
function setupNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    const tabViews = document.querySelectorAll(".tab-view");

    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            const targetTab = item.getAttribute("data-tab");
            if (!targetTab) return; // Prevent import button from overriding active tab state

            e.preventDefault();

            // Close mobile sidebar if open
            if (document.body.classList.contains("mobile-sidebar-open")) {
                document.body.classList.remove("mobile-sidebar-open");
            }

            // Toggle Nav Item Active State
            navItems.forEach(nav => {
                if (nav.getAttribute("data-tab")) {
                    nav.classList.remove("active");
                }
            });
            item.classList.add("active");

            // Toggle Tab View Active State
            tabViews.forEach(view => {
                view.classList.remove("active");
                if (view.getAttribute("id") === `view-${targetTab}`) {
                    view.classList.add("active");
                }
            });

            if (targetTab === "sleep-aids") {
                fetchSleepAids();
            }
        });
    });
}

// --- Dynamic API URLs Setup ---
function setupEndpointUrls() {
    // Dynamically display host IP and port to make sync configuration easy
    const hostUrl = `${window.location.protocol}//${window.location.host}`;
    const scEndpoint = `${hostUrl}/api/connectors/snore_cough_app/import`;
    document.getElementById("sc-endpoint-input").value = scEndpoint;
    document.getElementById("saa-endpoint-input").value = `${hostUrl}/api/connectors/sleep_as_android/import`;

    // Set default sync date to yesterday (morning of yesterday is sleep from night before)
    const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
    elGarminSyncDate.value = yesterday;

    // Generate Dynamic QR Code for App enrollment configuration
    try {
        const qrData = JSON.stringify({
            connector_id: "snore_cough_app",
            endpoint_url: scEndpoint
        });

        new QRious({
            element: document.getElementById('sc-qr-canvas'),
            value: qrData,
            size: 150,
            level: 'H',
            foreground: '#0f172a',
            background: '#ffffff'
        });
    } catch (qrErr) {
        console.error("Failed to generate custom app enrollment QR Code:", qrErr);
    }
}

// --- Clipboard Helper ---
function copyEndpointUrl(inputId) {
    const copyText = document.getElementById(inputId);
    copyText.select();
    copyText.setSelectionRange(0, 99999); // Mobile
    
    try {
        navigator.clipboard.writeText(copyText.value);
        alert("Copied API sync endpoint to clipboard!");
    } catch (err) {
        // Fallback
        document.execCommand("copy");
        alert("Copied API sync endpoint to clipboard!");
    }
}

// --- Garmin Configurations API ---

async function loadGarminConfig() {
    try {
        const response = await fetch("/api/connectors/garmin/config");
        if (response.ok) {
            const config = await response.json();
            if (config && config.email) {
                elGarminEmail.value = config.email;
                elGarminPassword.value = "••••••••••••"; // Masked password
                
                const elAutoSync = document.getElementById("garmin-auto-sync");
                if (elAutoSync) {
                    elAutoSync.checked = (config.auto_sync === "true");
                }
                
                elGarminStatusBadge.innerText = "Configured";
                elGarminStatusBadge.className = "status-indicator status-connected";
            } else {
                elGarminStatusBadge.innerText = "Not Configured";
                elGarminStatusBadge.className = "status-indicator status-disconnected";
            }
        }
    } catch (err) {
        console.error("Error loading Garmin config:", err);
    }
}

async function saveGarminConfig(e) {
    e.preventDefault();
    const email = elGarminEmail.value;
    const password = elGarminPassword.value;
    const autoSyncVal = document.getElementById("garmin-auto-sync")?.checked ? "true" : "false";

    if (!email || !password) {
        alert("Please fill in both email and password.");
        return;
    }

    try {
        const response = await fetch("/api/connectors/garmin/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password, auto_sync: autoSyncVal })
        });

        if (!response.ok) throw new Error("Failed to save credentials.");
        
        alert("Garmin credentials saved successfully!");
        loadGarminConfig();
    } catch (err) {
        console.error("Error saving Garmin config:", err);
        alert("Failed to save credentials: " + err.message);
    }
}

async function loadGarminRawFiles() {
    try {
        const response = await fetch("/api/connectors/garmin/raw");
        if (response.ok) {
            const files = await response.json();
            if (files && files.length > 0) {
                elGarminRawSelect.innerHTML = files.map(date => 
                    `<option value="${date}">garmin_raw_${date}.json</option>`
                ).join("");
            } else {
                elGarminRawSelect.innerHTML = `<option value="">No synced files found</option>`;
            }
        }
    } catch (err) {
        console.error("Error loading Garmin raw files list:", err);
    }
}

async function copyRawGarminData() {
    const selectedDate = elGarminRawSelect.value;
    if (!selectedDate) {
        alert("No raw file selected to copy.");
        return;
    }

    try {
        const response = await fetch(`/api/connectors/garmin/raw/${selectedDate}`);
        if (!response.ok) throw new Error("Failed to load file content.");
        const data = await response.json();
        
        await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
        alert(`Copied garmin_raw_${selectedDate}.json payload to clipboard!`);
    } catch (err) {
        console.error("Failed to copy raw Garmin data:", err);
        alert("Failed to copy file to clipboard: " + err.message);
    }
}

async function downloadRawGarminData() {
    const selectedDate = elGarminRawSelect.value;
    if (!selectedDate) {
        alert("No raw file selected to download.");
        return;
    }

    try {
        const response = await fetch(`/api/connectors/garmin/raw/${selectedDate}`);
        if (!response.ok) throw new Error("Failed to load file content.");
        const data = await response.json();
        
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute("href", dataStr);
        downloadAnchor.setAttribute("download", `garmin_raw_${selectedDate}.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
    } catch (err) {
        console.error("Failed to download raw Garmin data:", err);
        alert("Failed to download file: " + err.message);
    }
}

// --- Garmin Active Sync Trigger ---

async function triggerGarminSync() {
    const syncDate = elGarminSyncDate.value;
    if (!syncDate) {
        alert("Please select a target date to sync.");
        return;
    }

    elBtnSyncGarmin.disabled = true;
    elBtnSyncGarmin.innerText = "Syncing...";
    elGarminSyncLog.innerText = `[INFO] Initializing sync pipeline for target morning: ${syncDate}...\n`;
    elGarminSyncLog.scrollTop = elGarminSyncLog.scrollHeight;

    try {
        const response = await fetch("/api/connectors/garmin/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ date: syncDate })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || "Sync process returned an error.");
        }

        // Read stream chunks for real-time scrolling logs
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            elGarminSyncLog.innerText += chunk;
            elGarminSyncLog.scrollTop = elGarminSyncLog.scrollHeight;
        }

        elGarminSyncLog.innerText += "\n[SUCCESS] Garmin Sync run completed.";
        elGarminSyncLog.scrollTop = elGarminSyncLog.scrollHeight;

        // Refresh sessions list
        fetchSessions();
        loadGarminRawFiles();

    } catch (err) {
        console.error("Garmin sync failure:", err);
        elGarminSyncLog.innerText += `\n[ERROR] Sync failed: ${err.message}\n`;
        elGarminSyncLog.scrollTop = elGarminSyncLog.scrollHeight;
    } finally {
        elBtnSyncGarmin.disabled = false;
        elBtnSyncGarmin.innerText = "Run Sync Now";
    }
}

// --- Core API Interactions ---

async function fetchConnectors() {
    try {
        const response = await fetch("/api/connectors");
        activeConnectors = await response.json();
        renderConnectorBadges();
        populateConnectorSelect();
    } catch (err) {
        console.error("Error fetching connectors:", err);
        if (elConnectorBadges) {
            elConnectorBadges.innerHTML = `<span class="badge badge-danger">Error loading connectors</span>`;
        }
    }
}

async function fetchSessions() {
    try {
        const response = await fetch("/api/sessions");
        const sessions = await response.json();
        renderSessionsTable(sessions);
    } catch (err) {
        console.error("Error fetching sessions:", err);
        elHistoryBody.innerHTML = `<tr><td colspan="7" class="loading-row" style="color: var(--danger);">Failed to load history from server.</td></tr>`;
    }
}

async function fetchSessionDetails(sessionId) {
    try {
        const response = await fetch(`/api/sessions/${sessionId}`);
        if (!response.ok) throw new Error("Failed to load session details.");
        const data = await response.json();
        
        currentSessionId = sessionId;
        renderSessionAnalysis(data);
        fetchSessions(); // re-render list to show active row
    } catch (err) {
        console.error("Error loading session:", err);
        alert("Error loading sleep session details: " + err.message);
    }
}

async function saveJournalNotes(e) {
    e.preventDefault();
    if (!currentSessionId) return;

    const ratingVal = document.querySelector('input[name="rating"]:checked')?.value;
    const notesText = elJournalNotes.value;

    const positionVal = elJournalPosition.value || null;
    const aidsVal = Array.from(selectedSleepAids).join(",") || null;
    const disruptorsVal = Array.from(selectedSleepDisruptors).join(",") || null;

    if (!ratingVal) {
        alert("Please select a sleep quality rating first.");
        return;
    }

    try {
        const response = await fetch(`/api/sessions/${currentSessionId}/notes`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                rating: parseInt(ratingVal, 10),
                notes: notesText,
                sleep_position: positionVal,
                sleep_aids: aidsVal,
                sleep_disruptors: disruptorsVal
            })
        });

        if (!response.ok) throw new Error("Failed to save journal notes.");
        
        // Refresh session list to show updated details
        fetchSessions();
        alert("Sleep journal saved successfully!");
    } catch (err) {
        console.error("Error saving notes:", err);
        alert(err.message);
    }
}

async function deleteSession(sessionId, date) {
    if (!confirm(`Are you sure you want to delete the sleep session for ${date}? This will delete all metrics and cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
        if (!response.ok) throw new Error("Failed to delete session.");
        
        if (currentSessionId === sessionId) {
            // Close active panel
            currentSessionId = null;
            elChartsContainer.style.display = "none";
            elSessionStats.style.display = "none";
            elEmptyState.style.display = "flex";
            elJournalLoaded.style.display = "none";
            elJournalEmpty.style.display = "flex";
            elSessionTitle.innerText = "Select a session to review";
            elSessionTime.innerText = "-";
        }
        
        fetchSessions();
    } catch (err) {
        console.error("Error deleting session:", err);
        alert(err.message);
    }
}

// --- Render Operations ---

function renderConnectorBadges() {
    if (!elConnectorBadges) return;
    if (activeConnectors.length === 0) {
        elConnectorBadges.innerHTML = `<span class="loading-text">No active connectors</span>`;
        return;
    }
    elConnectorBadges.innerHTML = activeConnectors.map(c => 
        `<span class="connector-badge" title="${c.description}">${c.display_name}</span>`
    ).join("");
}

function populateConnectorSelect() {
    elConnectorSelect.innerHTML = activeConnectors.map(c => 
        `<option value="${c.connector_id}">${c.display_name}</option>`
    ).join("");
}

function renderSessionsTable(sessions) {
    if (sessions.length === 0) {
        elHistoryBody.innerHTML = `<tr><td colspan="7" class="loading-row">No sleep data available. Import a dataset to start.</td></tr>`;
        return;
    }

    elHistoryBody.innerHTML = sessions.map(s => {
        const start = new Date(s.start_time);
        const end = new Date(s.end_time);
        const durHrs = ((end - start) / 1000 / 60 / 60).toFixed(1);
        
        // Sleep score badge class
        let scoreClass = "";
        if (s.sleep_score >= 80) scoreClass = "score-high";
        else if (s.sleep_score >= 60) scoreClass = "score-med";
        else if (s.sleep_score) scoreClass = "score-low";

        const scoreText = s.sleep_score ? `<span class="score-badge ${scoreClass}">${s.sleep_score}</span>` : "-";
        
        // Notes summary
        let notesParts = [];
        if (s.sleep_position) {
            notesParts.push(`Pos: ${s.sleep_position}`);
        }
        if (s.sleep_aids) {
            notesParts.push(`Aids: ${s.sleep_aids}`);
        }
        if (s.sleep_disruptors) {
            notesParts.push(`Disruptors: ${s.sleep_disruptors}`);
        }
        if (s.notes) {
            notesParts.push(s.notes);
        }
        const notesSum = notesParts.length > 0 
            ? notesParts.join(" | ") 
            : `<span class="color-text-dim">No journal entry</span>`;
        
        // Rating stars
        const starsText = s.rating ? `<span class="star-rating-val">${"★".repeat(s.rating)}${"☆".repeat(5-s.rating)}</span>` : "-";

        const timeStr = `${start.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} - ${end.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;

        return `
            <tr class="${currentSessionId === s.id ? 'active-row' : ''}">
                <td><strong>${s.date}</strong></td>
                <td>${timeStr}</td>
                <td><span class="duration-val">${durHrs}h</span></td>
                <td>${scoreText}</td>
                <td>${starsText}</td>
                <td><div class="notes-summary-cell">${notesSum}</div></td>
                <td class="actions-cell">
                    <button class="btn btn-secondary btn-sm" onclick="fetchSessionDetails('${s.id}')">Review</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteSession('${s.id}', '${s.date}')">Delete</button>
                </td>
            </tr>
        `;
    }).join("");
}

function renderSessionAnalysis(data) {
    const s = data.session;
    const start = new Date(s.start_time);
    const end = new Date(s.end_time);
    const durMs = end - start;
    const durHrs = Math.floor(durMs / 1000 / 60 / 60);
    const durMins = Math.round((durMs / 1000 / 60) % 60);

    // Update Header Meta
    elSessionTitle.innerText = `Sleep Analysis: Morning of ${s.date}`;
    elSessionTime.innerText = `${start.toLocaleString()} to ${end.toLocaleString()}`;
    
    elStatDuration.innerText = `${durHrs}h ${durMins}m`;
    elStatScore.innerText = s.sleep_score || "-";
    
    // Bind Garmin recovery summary statistics
    elStatRestingHr.innerText = s.resting_heart_rate ? `${s.resting_heart_rate} bpm` : "-";
    elStatAvgHrv.innerText = s.avg_overnight_hrv ? `${s.avg_overnight_hrv} ms` : "-";
    elStatHrvStatus.innerText = s.hrv_status || "-";
    elStatBodyBattery.innerText = s.body_battery_change ? (s.body_battery_change > 0 ? `+${s.body_battery_change}` : s.body_battery_change) : "-";

    // Count snores
    let totalSnores = 0;
    if (data.metrics.snore) {
        Object.values(data.metrics.snore).forEach(series => {
            totalSnores += series.length;
        });
    }
    elStatSnores.innerText = totalSnores;

    // Show containers
    elEmptyState.style.display = "none";
    elChartsContainer.style.display = "block";
    elSessionStats.style.display = "flex";

    // Setup Journal Panel
    elJournalEmpty.style.display = "none";
    elJournalLoaded.style.display = "block";
    elJournalNotes.value = s.notes || "";
    
    // Populate Sleep Position
    if (elJournalPosition) {
        elJournalPosition.value = s.sleep_position || "";
    }

    // Populate Sleep Aids
    selectedSleepAids.clear();
    if (s.sleep_aids) {
        s.sleep_aids.split(",").forEach(aid => {
            const trimmed = aid.trim();
            if (trimmed) selectedSleepAids.add(trimmed);
        });
    }
    renderJournalSleepAidsPool();

    // Populate Sleep Disruptors
    selectedSleepDisruptors.clear();
    if (s.sleep_disruptors) {
        s.sleep_disruptors.split(",").forEach(dis => {
            const trimmed = dis.trim();
            if (trimmed) selectedSleepDisruptors.add(trimmed);
        });
    }
    renderJournalSleepDisruptorsPool();
    
    // Reset star rating check
    const checkedStar = document.querySelector('input[name="rating"]:checked');
    if (checkedStar) checkedStar.checked = false;
    if (s.rating) {
        const starToCheck = document.getElementById(`star${s.rating}`);
        if (starToCheck) starToCheck.checked = true;
    }

    // 1. Render Sleep Stage Swimlanes
    renderSwimlanes(data.metrics.sleep_stage, start, end);

    // 2. Render Heart Rate & Respiration Charts
    renderHeartRateRespirationChart(data.metrics, start, end);

    // 3. Render Recovery & Energy Charts
    renderRecoveryChart(data.metrics, start, end);

    // 4. Render Sleep Noise & Stability Charts
    renderSnoreCoughChart(data.metrics, start, end);
}

function renderSwimlanes(stageData, sessionStart, sessionEnd) {
    elSwimlanes.innerHTML = "";
    if (!stageData || Object.keys(stageData).length === 0) {
        elSwimlanes.innerHTML = `<p class="loading-text">No sleep stage data records found.</p>`;
        return;
    }

    const sessionStartMs = sessionStart.getTime();
    const sessionEndMs = sessionEnd.getTime();
    const totalMs = sessionEndMs - sessionStartMs;

    Object.keys(stageData).forEach(connectorId => {
        const connector = activeConnectors.find(c => c.connector_id === connectorId);
        const name = connector ? connector.display_name : connectorId;
        
        const rawPoints = stageData[connectorId];
        if (rawPoints.length === 0) return;

        // Parse and sort segments chronologically
        const segments = rawPoints.map((p, idx) => {
            const start = new Date(p.t).getTime();
            
            // Check if raw payload contains explicit end time
            let end = null;
            const raw = p.raw_payload;
            if (raw) {
                let endStr = raw.endTime || raw.end;
                if (endStr) {
                    endStr = endStr.replace(" ", "T");
                    // Naive date strings should be treated as UTC/GMT
                    if (!endStr.endsWith("Z") && !endStr.includes("+") && !endStr.includes("-", 10)) {
                        endStr += "Z";
                    }
                    end = new Date(endStr).getTime();
                }
            }
            
            // Fallback: If no explicit end, use next segment's start or session end
            if (!end) {
                if (idx < rawPoints.length - 1) {
                    end = new Date(rawPoints[idx + 1].t).getTime();
                } else {
                    end = sessionEndMs;
                }
            }
            
            return {
                stage: p.v.toLowerCase(),
                start: start,
                end: end
            };
        }).sort((a, b) => a.start - b.start);

        // Build HTML segments and fill initial/final gaps to align lanes
        let laneHtml = "";
        
        // 1. Initial Gap: If first segment starts after sessionStart
        if (segments[0].start > sessionStartMs) {
            const gapWidth = ((segments[0].start - sessionStartMs) / totalMs * 100).toFixed(3);
            laneHtml += `<div class="swimlane-segment stage-awake" style="width: ${gapWidth}%;" data-tooltip="Unmonitored Gap: ${Math.round((segments[0].start - sessionStartMs)/1000/60)} mins"></div>`;
        }

        // 2. Main segments
        segments.forEach(seg => {
            const segStart = Math.max(seg.start, sessionStartMs);
            const segEnd = Math.min(seg.end, sessionEndMs);
            const durationMs = segEnd - segStart;
            
            if (durationMs <= 0) return;
            
            const width = (durationMs / totalMs * 100).toFixed(3);
            const durationMins = Math.round(durationMs / 1000 / 60);
            
            // Formatted tooltip
            const timeLabel = `${new Date(segStart).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} - ${new Date(segEnd).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
            const tooltip = `${seg.stage.toUpperCase()} (${durationMins}m) | ${timeLabel}`;

            laneHtml += `<div class="swimlane-segment stage-${seg.stage}" style="width: ${width}%;" data-tooltip="${tooltip}"></div>`;
        });

        // 3. Final Gap: If last segment ends before sessionEnd
        const lastSegEnd = segments[segments.length - 1].end;
        if (lastSegEnd < sessionEndMs) {
            const gapWidth = ((sessionEndMs - lastSegEnd) / totalMs * 100).toFixed(3);
            laneHtml += `<div class="swimlane-segment stage-awake" style="width: ${gapWidth}%;" data-tooltip="Unmonitored Gap: ${Math.round((sessionEndMs - lastSegEnd)/1000/60)} mins"></div>`;
        }

        // Calculate summary for meta display
        const stageTotals = { awake: 0, light: 0, deep: 0, rem: 0 };
        segments.forEach(seg => {
            const durationMin = (seg.end - seg.start) / 1000 / 60;
            if (stageTotals[seg.stage] !== undefined) {
                stageTotals[seg.stage] += durationMin;
            }
        });
        const summaryText = `Deep: ${Math.round(stageTotals.deep)}m | REM: ${Math.round(stageTotals.rem)}m | Light: ${Math.round(stageTotals.light)}m | Awake: ${Math.round(stageTotals.awake)}m`;

        const swimlaneHtml = `
            <div class="swimlane">
                <div class="swimlane-meta">
                    <span class="swimlane-label">${name}</span>
                    <span class="swimlane-summary">${summaryText}</span>
                </div>
                <div class="swimlane-bar">
                    ${laneHtml}
                </div>
            </div>
        `;
        
        elSwimlanes.insertAdjacentHTML("beforeend", swimlaneHtml);
    });
}

function renderHeartRateRespirationChart(metrics, sessionStart, sessionEnd) {
    if (hrBrChart) hrBrChart.destroy();

    const datasets = [];

    // Colors for different sources
    const colors = {
        "garmin": { hr: "#818cf8", br: "#34d399", spo2: "#38bdf8" }, // indigo / teal / sky blue
        "health_connect": { hr: "#60a5fa", br: "#2dd4bf", spo2: "#06b6d4" },
        "fallback": { hr: "#94a3b8", br: "#a1a1aa", spo2: "#64748b" }
    };

    // 1. Process Heart Rate series
    if (metrics.heart_rate) {
        Object.keys(metrics.heart_rate).forEach(connectorId => {
            const connColors = colors[connectorId] || colors.fallback;
            const dataPoints = metrics.heart_rate[connectorId].map(p => ({
                x: Date.parse(p.t),
                y: p.v
            }));

            const connector = activeConnectors.find(c => c.connector_id === connectorId);
            const label = connector ? `${connector.display_name} HR` : `${connectorId} HR`;

            datasets.push({
                label: label,
                data: dataPoints,
                borderColor: connColors.hr,
                backgroundColor: connColors.hr + "1A", // 10% opacity
                borderWidth: 2,
                pointRadius: 1,
                pointHoverRadius: 5,
                yAxisID: "y-hr",
                tension: 0.2,
                fill: false
            });
        });
    }

    // 2. Process Respiration series
    if (metrics.respiration) {
        Object.keys(metrics.respiration).forEach(connectorId => {
            const connColors = colors[connectorId] || colors.fallback;
            const dataPoints = metrics.respiration[connectorId].map(p => ({
                x: Date.parse(p.t),
                y: p.v
            }));

            const connector = activeConnectors.find(c => c.connector_id === connectorId);
            const label = connector ? `${connector.display_name} Respiration` : `${connectorId} Respiration`;

            datasets.push({
                label: label,
                data: dataPoints,
                borderColor: connColors.br,
                borderDash: [5, 5],
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 4,
                yAxisID: "y-br",
                tension: 0.3,
                fill: false
            });
        });
    }

    // 3. Process SpO2 series
    if (metrics.spo2) {
        Object.keys(metrics.spo2).forEach(connectorId => {
            const connColors = colors[connectorId] || colors.fallback;
            const dataPoints = metrics.spo2[connectorId].map(p => ({
                x: Date.parse(p.t),
                y: p.v
            }));

            const connector = activeConnectors.find(c => c.connector_id === connectorId);
            const label = connector ? `${connector.display_name} SpO2 (%)` : `${connectorId} SpO2 (%)`;

            datasets.push({
                label: label,
                data: dataPoints,
                borderColor: connColors.spo2,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                yAxisID: "y-spo2",
                tension: 0.3,
                fill: false
            });
        });
    }

    const ctx = document.getElementById("chart-heart-respiration").getContext("2d");
    hrBrChart = new Chart(ctx, {
        type: "line",
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    labels: { color: "#e2e8f0", boxWidth: 12, font: { family: "Inter", size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        title: (context) => {
                            const d = new Date(context[0].raw.x);
                            return d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: "linear",
                    min: sessionStart.getTime(),
                    max: sessionEnd.getTime(),
                    ticks: {
                        color: "#94a3b8",
                        callback: function(value) {
                            return new Date(value).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        },
                        maxTicksLimit: 8
                    },
                    grid: { color: "rgba(255,255,255,0.03)" }
                },
                "y-hr": {
                    type: "linear",
                    position: "left",
                    title: { display: true, text: "Heart Rate (bpm)", color: "#818cf8" },
                    ticks: { color: "#94a3b8" },
                    grid: { color: "rgba(255,255,255,0.05)" }
                },
                "y-br": {
                    type: "linear",
                    position: "right",
                    title: { display: true, text: "Respiration (breaths/min)", color: "#34d399" },
                    ticks: { color: "#94a3b8" },
                    grid: { drawOnChartArea: false }
                },
                "y-spo2": {
                    type: "linear",
                    position: "right",
                    title: { display: true, text: "SpO2 (%)", color: "#38bdf8" },
                    ticks: { color: "#94a3b8" },
                    grid: { drawOnChartArea: false },
                    min: 80,
                    max: 100
                }
            }
        }
    });
}

function renderRecoveryChart(metrics, sessionStart, sessionEnd) {
    if (recoveryChart) recoveryChart.destroy();

    const datasets = [];

    const colors = {
        "garmin": { stress: "#f43f5e", bb: "#10b981", hrv: "#a78bfa" }, // Rose / Emerald / Lavender
        "fallback": { stress: "#fca5a5", bb: "#6ee7b7", hrv: "#c084fc" }
    };

    // 1. Process Stress level series
    if (metrics.stress) {
        Object.keys(metrics.stress).forEach(connectorId => {
            const connColors = colors[connectorId] || colors.fallback;
            const dataPoints = metrics.stress[connectorId].map(p => ({
                x: Date.parse(p.t),
                y: p.v
            }));

            const connector = activeConnectors.find(c => c.connector_id === connectorId);
            const label = connector ? `${connector.display_name} Stress` : `${connectorId} Stress`;

            datasets.push({
                label: label,
                data: dataPoints,
                borderColor: connColors.stress,
                backgroundColor: connColors.stress + "1A", // 10% opacity
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 4,
                yAxisID: "y-stress",
                tension: 0.2,
                fill: false
            });
        });
    }

    // 2. Process Body Battery series
    if (metrics.body_battery) {
        Object.keys(metrics.body_battery).forEach(connectorId => {
            const connColors = colors[connectorId] || colors.fallback;
            const dataPoints = metrics.body_battery[connectorId].map(p => ({
                x: Date.parse(p.t),
                y: p.v
            }));

            const connector = activeConnectors.find(c => c.connector_id === connectorId);
            const label = connector ? `${connector.display_name} Body Battery` : `${connectorId} Body Battery`;

            datasets.push({
                label: label,
                data: dataPoints,
                borderColor: connColors.bb,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                yAxisID: "y-bb",
                tension: 0.1,
                fill: false
            });
        });
    }

    // 3. Process HRV series
    if (metrics.hrv) {
        Object.keys(metrics.hrv).forEach(connectorId => {
            const connColors = colors[connectorId] || colors.fallback;
            const dataPoints = metrics.hrv[connectorId].map(p => ({
                x: Date.parse(p.t),
                y: p.v
            }));

            const connector = activeConnectors.find(c => c.connector_id === connectorId);
            const label = connector ? `${connector.display_name} HRV` : `${connectorId} HRV`;

            datasets.push({
                label: label,
                data: dataPoints,
                borderColor: connColors.hrv,
                borderDash: [3, 3],
                borderWidth: 1.5,
                pointRadius: 1,
                pointHoverRadius: 4,
                yAxisID: "y-hrv",
                tension: 0.3,
                fill: false
            });
        });
    }

    const ctx = document.getElementById("chart-recovery").getContext("2d");
    recoveryChart = new Chart(ctx, {
        type: "line",
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    labels: { color: "#e2e8f0", boxWidth: 12, font: { family: "Inter", size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        title: (context) => {
                            const d = new Date(context[0].raw.x);
                            return d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: "linear",
                    min: sessionStart.getTime(),
                    max: sessionEnd.getTime(),
                    ticks: {
                        color: "#94a3b8",
                        callback: function(value) {
                            return new Date(value).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        },
                        maxTicksLimit: 8
                    },
                    grid: { color: "rgba(255,255,255,0.03)" }
                },
                "y-stress": {
                    type: "linear",
                    position: "left",
                    title: { display: true, text: "Stress Score (0-100)", color: "#f43f5e" },
                    ticks: { color: "#94a3b8" },
                    grid: { color: "rgba(255,255,255,0.05)" },
                    min: 0,
                    max: 100
                },
                "y-bb": {
                    type: "linear",
                    position: "right",
                    title: { display: true, text: "Body Battery (%)", color: "#10b981" },
                    ticks: { color: "#94a3b8" },
                    grid: { drawOnChartArea: false },
                    min: 0,
                    max: 100
                },
                "y-hrv": {
                    type: "linear",
                    position: "right",
                    title: { display: true, text: "HRV (ms)", color: "#a78bfa" },
                    ticks: { color: "#94a3b8" },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
}

function renderSnoreCoughChart(metrics, sessionStart, sessionEnd) {
    if (snoreCoughChart) snoreCoughChart.destroy();

    const datasets = [];

    // Colors for events
    const colors = {
        snore: "#f97316", // Orange
        cough: "#ef4444"  // Red
    };

    // 1. Process Snore events
    if (metrics.snore) {
        Object.keys(metrics.snore).forEach(connectorId => {
            const dataPoints = metrics.snore[connectorId].map(p => ({
                x: Date.parse(p.t),
                y: p.v
            }));

            const connector = activeConnectors.find(c => c.connector_id === connectorId);
            const label = connector ? `${connector.display_name} Snore` : `${connectorId} Snore`;

            datasets.push({
                label: label,
                data: dataPoints,
                backgroundColor: colors.snore,
                borderColor: colors.snore + "CC",
                borderWidth: 1,
                barThickness: 8,
                yAxisID: "y-snore",
                type: "bar"
            });
        });
    }

    // 2. Process Cough events
    if (metrics.cough) {
        Object.keys(metrics.cough).forEach(connectorId => {
            const dataPoints = metrics.cough[connectorId].map(p => ({
                x: Date.parse(p.t),
                y: p.v
            }));

            const connector = activeConnectors.find(c => c.connector_id === connectorId);
            const label = connector ? `${connector.display_name} Cough` : `${connectorId} Cough`;

            datasets.push({
                label: label,
                data: dataPoints,
                backgroundColor: colors.cough,
                borderColor: colors.cough + "CC",
                borderWidth: 1,
                barThickness: 8,
                yAxisID: "y-cough",
                type: "bar"
            });
        });
    }

    // 3. Process Breathing Disruptions
    if (metrics.breathing_disruption) {
        Object.keys(metrics.breathing_disruption).forEach(connectorId => {
            const dataPoints = [];
            const rawPoints = metrics.breathing_disruption[connectorId];
            rawPoints.forEach(p => {
                const start = Date.parse(p.t);
                let end = start;
                if (p.raw_payload && p.raw_payload.endGMT) {
                    end = p.raw_payload.endGMT;
                }
                
                let val = p.v;
                if (val === 255) val = 0; // Map unmonitored to 0
                
                dataPoints.push({ x: start, y: val });
                if (end > start) {
                    dataPoints.push({ x: end, y: val });
                }
            });
            
            dataPoints.sort((a, b) => a.x - b.x);

            const connector = activeConnectors.find(c => c.connector_id === connectorId);
            const label = connector ? `${connector.display_name} Breathing Disruption` : `${connectorId} Breathing Disruption`;

            datasets.push({
                label: label,
                data: dataPoints,
                borderColor: "#fbbf24", // Amber
                backgroundColor: "rgba(251, 191, 36, 0.08)",
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                yAxisID: "y-bd",
                tension: 0,
                stepped: 'before',
                type: "line",
                fill: true
            });
        });
    }

    const ctx = document.getElementById("chart-snore-cough").getContext("2d");
    snoreCoughChart = new Chart(ctx, {
        type: "bar",
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    labels: { color: "#e2e8f0", boxWidth: 12, font: { family: "Inter", size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        title: (context) => {
                            const d = new Date(context[0].raw.x);
                            return d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: "linear",
                    min: sessionStart.getTime(),
                    max: sessionEnd.getTime(),
                    ticks: {
                        color: "#94a3b8",
                        callback: function(value) {
                            return new Date(value).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        },
                        maxTicksLimit: 8
                    },
                    grid: { color: "rgba(255,255,255,0.03)" }
                },
                "y-snore": {
                    type: "linear",
                    position: "left",
                    title: { display: true, text: "Snore Duration (sec)", color: colors.snore },
                    ticks: { color: "#94a3b8" },
                    grid: { color: "rgba(255,255,255,0.05)" },
                    min: 0
                },
                "y-cough": {
                    type: "linear",
                    position: "right",
                    title: { display: true, text: "Cough Count (intervals)", color: colors.cough },
                    ticks: { color: "#94a3b8", stepSize: 1 },
                    grid: { drawOnChartArea: false },
                    min: 0
                },
                "y-bd": {
                    type: "linear",
                    position: "right",
                    title: { display: true, text: "Breathing Disruptions", color: "#fbbf24" },
                    ticks: { color: "#94a3b8", stepSize: 1 },
                    grid: { drawOnChartArea: false },
                    min: 0,
                    max: 4
                }
            }
        }
    });
}

// --- Setup Interactions & Modal ---

function setupEventListeners() {
    // Sleep Aid form submission
    if (elAddSleepAidForm) {
        elAddSleepAidForm.addEventListener("submit", addSleepAid);
    }

    // Open/Close Modal
    elBtnOpenImport.addEventListener("click", () => {
        elImportFeedback.style.display = "none";
        elBtnSubmitImport.disabled = true;
        selectedFile = null;
        elDropZone.innerHTML = `<span class="upload-icon">📁</span><p>Drag and drop your JSON mock payload here, or <span class="highlight">browse files</span></p>`;
        elImportModal.style.display = "flex";
    });

    const closeModal = () => { elImportModal.style.display = "none"; };
    elBtnCloseImport.addEventListener("click", closeModal);
    elBtnCancelImport.addEventListener("click", closeModal);

    // Handle form submit for Notes
    elJournalForm.addEventListener("submit", saveJournalNotes);

    // Garmin config form submit
    elGarminConfigForm.addEventListener("submit", saveGarminConfig);

    // Garmin sync run trigger
    elBtnSyncGarmin.addEventListener("click", triggerGarminSync);

    // Garmin raw file copy/download (Diagnostics)
    elBtnCopyRawGarmin.addEventListener("click", copyRawGarminData);
    elBtnDownloadRawGarmin.addEventListener("click", downloadRawGarminData);

    // Drop Zone Events
    elDropZone.addEventListener("click", () => elFileInput.click());
    
    elFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    elDropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        elDropZone.classList.add("dragover");
    });

    elDropZone.addEventListener("dragleave", () => {
        elDropZone.classList.remove("dragover");
    });

    elDropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        elDropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    // Submit File Ingestion
    elBtnSubmitImport.addEventListener("click", submitImport);

    // Desktop Sidebar Collapse Toggle
    const btnSidebarToggle = document.getElementById("sidebar-toggle");
    const btnMobileToggle = document.getElementById("mobile-sidebar-toggle");
    const elSidebarOverlay = document.getElementById("sidebar-overlay");
    const sidebarEl = document.querySelector(".sidebar");
    const layoutEl = document.querySelector(".app-layout");

    if (btnSidebarToggle && layoutEl) {
        btnSidebarToggle.addEventListener("click", () => {
            const isCollapsed = layoutEl.classList.toggle("sidebar-collapsed");
            localStorage.setItem("sidebar-collapsed", isCollapsed);
            btnSidebarToggle.innerText = isCollapsed ? "▶" : "◀";
            // Trigger chart redraw during sidebar collapse animation
            resizeAllCharts();
        });
    }

    // Sidebar transitionend listener to finalize chart resizing
    if (sidebarEl) {
        sidebarEl.addEventListener("transitionend", (e) => {
            if (e.propertyName === "width" || e.propertyName === "transform") {
                resizeAllCharts();
            }
        });
    }

    // Mobile Hamburger Toggle
    if (btnMobileToggle) {
        btnMobileToggle.addEventListener("click", () => {
            document.body.classList.add("mobile-sidebar-open");
        });
    }

    // Mobile Sidebar Backdrop Overlay Click
    if (elSidebarOverlay) {
        elSidebarOverlay.addEventListener("click", () => {
            document.body.classList.remove("mobile-sidebar-open");
        });
    }

    // Window Resize Event
    window.addEventListener("resize", () => {
        resizeAllCharts();
    });
}

// --- Responsive Layout & Dynamic Chart Resizing Logic ---
function resizeAllCharts() {
    if (hrBrChart) {
        hrBrChart.resize();
        hrBrChart.update('none');
    }
    if (recoveryChart) {
        recoveryChart.resize();
        recoveryChart.update('none');
    }
    if (snoreCoughChart) {
        snoreCoughChart.resize();
        snoreCoughChart.update('none');
    }
}

function handleFileSelect(file) {
    if (file.type !== "application/json" && !file.name.endsWith(".json")) {
        showImportFeedback("Please upload a JSON file.", "error");
        return;
    }
    selectedFile = file;
    elDropZone.innerHTML = `<span class="upload-icon">✅</span><p>Selected: <strong class="highlight">${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)</p>`;
    elBtnSubmitImport.disabled = false;
    elImportFeedback.style.display = "none";
}

function showImportFeedback(msg, type) {
    elImportFeedback.innerText = msg;
    elImportFeedback.className = `feedback-msg ${type}`;
    elImportFeedback.style.display = "block";
}

async function submitImport() {
    if (!selectedFile) return;
    
    const connectorId = elConnectorSelect.value;
    elBtnSubmitImport.innerText = "Importing...";
    elBtnSubmitImport.disabled = true;

    try {
        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const payload = JSON.parse(e.target.result);
                
                const response = await fetch(`/api/connectors/${connectorId}/import`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const errInfo = await response.json();
                    throw new Error(errInfo.detail || "Ingestion endpoint failed.");
                }

                const result = await response.json();
                showImportFeedback(`Success! Imported session for ${result.date} (${result.samples_imported} metrics)`, "success");
                
                // Refresh list and reload details
                fetchSessions();
                fetchSessionDetails(result.session_id);

                setTimeout(() => {
                    elImportModal.style.display = "none";
                    elBtnSubmitImport.innerText = "Import File";
                }, 1500);

            } catch (jsonErr) {
                showImportFeedback("Invalid JSON format inside file or parser failed: " + jsonErr.message, "error");
                elBtnSubmitImport.innerText = "Import File";
                elBtnSubmitImport.disabled = false;
            }
        };
        reader.readAsText(selectedFile);
    } catch (err) {
        showImportFeedback("File reading failed: " + err.message, "error");
        elBtnSubmitImport.innerText = "Import File";
        elBtnSubmitImport.disabled = false;
    }
}

// --- Sleep Aids Dynamic Actions ---

async function fetchSleepAids() {
    try {
        const response = await fetch("/api/sleep_aids");
        if (response.ok) {
            globalSleepAids = await response.json();
            renderSleepAidsConfigList();
            renderSleepDisruptorsConfigList();
            renderJournalSleepAidsPool();
            renderJournalSleepDisruptorsPool();
        }
    } catch (err) {
        console.error("Error fetching sleep aids:", err);
    }
}

function renderSleepAidsConfigList() {
    if (!elSleepAidsConfigList) return;
    const aids = globalSleepAids.filter(x => x.category === "aid");
    if (aids.length === 0) {
        elSleepAidsConfigList.innerHTML = `<span class="color-text-dim" style="font-size: 13px;">No aids configured.</span>`;
        return;
    }
    
    elSleepAidsConfigList.innerHTML = aids.map(aid => `
        <span class="tag-pill">
            ${escapeHtml(aid.name)}
            <span class="tag-pill-delete" onclick="deleteSleepAid(${aid.id}, '${escapeHtml(aid.name)}')">&times;</span>
        </span>
    `).join("");
}

function renderSleepDisruptorsConfigList() {
    if (!elSleepDisruptorsConfigList) return;
    const disruptors = globalSleepAids.filter(x => x.category === "disruptor");
    if (disruptors.length === 0) {
        elSleepDisruptorsConfigList.innerHTML = `<span class="color-text-dim" style="font-size: 13px;">No disruptors configured.</span>`;
        return;
    }
    
    elSleepDisruptorsConfigList.innerHTML = disruptors.map(dis => `
        <span class="tag-pill">
            ${escapeHtml(dis.name)}
            <span class="tag-pill-delete" onclick="deleteSleepAid(${dis.id}, '${escapeHtml(dis.name)}')">&times;</span>
        </span>
    `).join("");
}

function renderJournalSleepAidsPool() {
    if (!elJournalSleepAidsPool) return;
    const aids = globalSleepAids.filter(x => x.category === "aid");
    if (aids.length === 0) {
        elJournalSleepAidsPool.innerHTML = `<span class="color-text-dim" style="font-size: 12px;">No aids configured. Add them under "Sleep Factors".</span>`;
        return;
    }

    elJournalSleepAidsPool.innerHTML = aids.map(aid => {
        const isActive = selectedSleepAids.has(aid.name);
        return `
            <span class="tag-pill ${isActive ? 'active' : ''}" data-name="${escapeHtml(aid.name)}" onclick="toggleJournalSleepAid(this)">
                ${escapeHtml(aid.name)}
            </span>
        `;
    }).join("");
}

function renderJournalSleepDisruptorsPool() {
    if (!elJournalSleepDisruptorsPool) return;
    const disruptors = globalSleepAids.filter(x => x.category === "disruptor");
    if (disruptors.length === 0) {
        elJournalSleepDisruptorsPool.innerHTML = `<span class="color-text-dim" style="font-size: 12px;">No disruptors configured. Add them under "Sleep Factors".</span>`;
        return;
    }

    elJournalSleepDisruptorsPool.innerHTML = disruptors.map(dis => {
        const isActive = selectedSleepDisruptors.has(dis.name);
        return `
            <span class="tag-pill disruptor ${isActive ? 'active' : ''}" data-name="${escapeHtml(dis.name)}" onclick="toggleJournalSleepDisruptor(this)">
                ${escapeHtml(dis.name)}
            </span>
        `;
    }).join("");
}

function toggleJournalSleepAid(el) {
    const name = el.getAttribute("data-name");
    if (selectedSleepAids.has(name)) {
        selectedSleepAids.delete(name);
        el.classList.remove("active");
    } else {
        selectedSleepAids.add(name);
        el.classList.add("active");
    }
}

function toggleJournalSleepDisruptor(el) {
    const name = el.getAttribute("data-name");
    if (selectedSleepDisruptors.has(name)) {
        selectedSleepDisruptors.delete(name);
        el.classList.remove("active");
    } else {
        selectedSleepDisruptors.add(name);
        el.classList.add("active");
    }
}

async function addSleepAid(e) {
    e.preventDefault();
    const name = elNewSleepAidName.value.trim();
    const category = elNewSleepAidCategory ? elNewSleepAidCategory.value : "aid";
    if (!name) return;

    try {
        const response = await fetch("/api/sleep_aids", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: name, category: category })
        });

        if (response.ok) {
            elNewSleepAidName.value = "";
            await fetchSleepAids();
        } else {
            const err = await response.json();
            alert(err.detail || "Failed to create tag.");
        }
    } catch (err) {
        console.error("Error creating tag:", err);
        alert("Error creating tag.");
    }
}

async function deleteSleepAid(id, name) {
    if (!confirm(`Are you sure you want to delete the "${name}" tag?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/sleep_aids/${id}`, {
            method: "DELETE"
        });

        if (response.ok) {
            await fetchSleepAids();
        } else {
            const err = await response.json();
            alert(err.detail || "Failed to delete tag.");
        }
    } catch (err) {
        console.error("Error deleting tag:", err);
        alert("Error deleting tag.");
    }
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
