// AI Web CTF Solver - JavaScript functionality

// Real-time updates for challenge monitoring
let currentChallengeId = null;
let updateInterval = null;

// Initialize page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Auto-update challenge status if on monitor page
    const challengeId = getChallengeIdFromUrl();
    if (challengeId) {
        startMonitoring(challengeId);
    }
    
    // Initialize form handlers
    initializeFormHandlers();
    
    // Initialize tooltips and other Bootstrap components
    initializeBootstrap();
});

// Get challenge ID from current URL
function getChallengeIdFromUrl() {
    const path = window.location.pathname;
    const match = path.match(/\/challenges\/([^\/]+)/);
    return match ? match[1] : null;
}

// Start real-time monitoring for a challenge
function startMonitoring(challengeId) {
    currentChallengeId = challengeId;
    
    // Initial load
    updateChallengeStatus();
    
    // Set up periodic updates (every 2 seconds)
    updateInterval = setInterval(updateChallengeStatus, 2000);
}

// Stop monitoring
function stopMonitoring() {
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
    currentChallengeId = null;
}

// Update challenge status via API
async function updateChallengeStatus() {
    if (!currentChallengeId) return;
    
    try {
        const response = await fetch(`/api/challenges/${currentChallengeId}/status`);
        if (!response.ok) throw new Error('Failed to fetch status');
        
        const data = await response.json();
        updateUI(data);
        
        // Stop monitoring if challenge is complete or failed
        if (data.status === 'completed' || data.status === 'failed' || data.status === 'stopped') {
            stopMonitoring();
        }
    } catch (error) {
        console.error('Error updating challenge status:', error);
    }
}

// Update UI elements with new status data
function updateUI(data) {
    // Update progress bar
    const progressBar = document.getElementById('progress-bar');
    if (progressBar) {
        progressBar.style.width = `${data.progress || 0}%`;
        progressBar.textContent = `${data.progress || 0}%`;
    }
    
    // Update status badge
    const statusBadge = document.getElementById('status-badge');
    if (statusBadge) {
        statusBadge.className = `badge status-${data.status}`;
        statusBadge.textContent = data.status.toUpperCase();
    }
    
    // Update current agent
    const currentAgent = document.getElementById('current-agent');
    if (currentAgent && data.current_agent) {
        currentAgent.textContent = data.current_agent;
    }
    
    // Update logs
    const logsContainer = document.getElementById('logs-container');
    if (logsContainer && data.logs) {
        updateLogs(data.logs);
    }
    
    // Update vulnerabilities
    const vulnContainer = document.getElementById('vulnerabilities-container');
    if (vulnContainer && data.vulnerabilities) {
        updateVulnerabilities(data.vulnerabilities);
    }
    
    // Update flags
    const flagsContainer = document.getElementById('flags-container');
    if (flagsContainer && data.flags) {
        updateFlags(data.flags);
    }
    
    // Update statistics
    updateStatistics(data.stats || {});
}

// Update logs display
function updateLogs(logs) {
    const container = document.getElementById('logs-container');
    if (!container) return;
    
    // Keep only recent logs (last 100)
    const recentLogs = logs.slice(-100);
    
    container.innerHTML = '';
    recentLogs.forEach(log => {
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        
        const timestamp = new Date(log.timestamp).toLocaleTimeString();
        logEntry.innerHTML = `
            <span class="log-timestamp">${timestamp}</span>
            <span class="log-agent">[${log.agent}]</span>
            <span class="log-message">${escapeHtml(log.message)}</span>
        `;
        
        container.appendChild(logEntry);
    });
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

// Update vulnerabilities display
function updateVulnerabilities(vulnerabilities) {
    const container = document.getElementById('vulnerabilities-container');
    if (!container) return;
    
    container.innerHTML = '';
    vulnerabilities.forEach(vuln => {
        const vulnDiv = document.createElement('div');
        vulnDiv.className = `vulnerability-item vulnerability-${vuln.severity.toLowerCase()}`;
        vulnDiv.innerHTML = `
            <h6>${escapeHtml(vuln.type)}</h6>
            <p>${escapeHtml(vuln.description)}</p>
            <small>Severity: ${vuln.severity}</small>
        `;
        container.appendChild(vulnDiv);
    });
}

// Update flags display
function updateFlags(flags) {
    const container = document.getElementById('flags-container');
    if (!container) return;
    
    container.innerHTML = '';
    flags.forEach(flag => {
        const flagDiv = document.createElement('div');
        flagDiv.className = 'flag-found';
        flagDiv.innerHTML = `
            <h6>Flag Found!</h6>
            <div class="flag-text">${escapeHtml(flag.value)}</div>
            <small>Found by: ${flag.source}</small>
        `;
        container.appendChild(flagDiv);
    });
}

// Update statistics
function updateStatistics(stats) {
    const elements = {
        'pages-crawled': stats.pages_crawled || 0,
        'forms-found': stats.forms_found || 0,
        'vulnerabilities-found': stats.vulnerabilities_found || 0,
        'exploits-attempted': stats.exploits_attempted || 0,
        'flags-found': stats.flags_found || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

// Initialize form handlers
function initializeFormHandlers() {
    // Challenge submission form
    const submitForm = document.getElementById('challenge-form');
    if (submitForm) {
        submitForm.addEventListener('submit', handleChallengeSubmit);
    }
    
    // Stop challenge buttons
    document.querySelectorAll('.stop-challenge-btn').forEach(btn => {
        btn.addEventListener('click', handleStopChallenge);
    });
}

// Handle challenge form submission
async function handleChallengeSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Disable submit button and show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Starting...';
    
    try {
        const response = await fetch('/api/challenges/submit', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('Failed to submit challenge');
        
        const data = await response.json();
        
        // Redirect to monitor page
        window.location.href = `/challenges/${data.challenge_id}`;
        
    } catch (error) {
        console.error('Error submitting challenge:', error);
        alert('Failed to submit challenge. Please try again.');
        
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Start Solving';
    }
}

// Handle stop challenge
async function handleStopChallenge(event) {
    const challengeId = event.target.dataset.challengeId;
    if (!challengeId) return;
    
    if (!confirm('Are you sure you want to stop this challenge?')) return;
    
    try {
        const response = await fetch(`/api/challenges/${challengeId}/stop`, {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Failed to stop challenge');
        
        // Refresh page or update UI
        location.reload();
        
    } catch (error) {
        console.error('Error stopping challenge:', error);
        alert('Failed to stop challenge. Please try again.');
    }
}

// Initialize Bootstrap components
function initializeBootstrap() {
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
    
    // Initialize popovers
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    popovers.forEach(popover => {
        new bootstrap.Popover(popover);
    });
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    stopMonitoring();
});