/**
 * COMPLETE AI ALERT SYSTEM & ALERTS PAGE COMPONENT
 * Handles Toast Notifications, Alert Badges, Main Alert Panel, 3D Mesh Sync,
 * and the Dedicated Alerts Page Log Table with 4 Risk State Filters:
 * 🟢 NORMAL | 🟡 WARNING | 🔴 HIGH RISK | 🟣 CRITICAL
 */

class AlertsViewComponent {
  constructor(dataService) {
    this.dataService = dataService;
    this.alertsContainer = document.getElementById('alerts-history-list');
    this.toastContainer = document.getElementById('toast-container');
    this.filterButtons = document.querySelectorAll('.btn-alert-filter');
    this.navAlertBadge = document.getElementById('active-alert-count');
    
    this.currentFilter = 'all';
    this.lastProcessedAlertId = null;

    // Full Alert History Records Store
    this.alertHistory = [
      {
        alertId: "ALT-8904",
        assetId: "T-104",
        timestamp: "14:45:14",
        riskLevel: "CRITICAL",
        icon: "🟣",
        statusText: "Immediate Inspection Recommended",
        detectedCondition: "High-frequency ultrasonic acoustic transient discharge coupled with localized oil temperature delta surge.",
        explanation: "Simultaneous divergence across acoustic ultrasonic energy signatures and oil thermal rate-of-rise matching winding dielectric breakdown.",
        recommendation: "CRITICAL PREVENTIVE ACTION: Execute remote load shed on T-104 immediately and isolate Substation Beta West line.",
        status: "ACTIVE"
      },
      {
        alertId: "ALT-8902",
        assetId: "T-105",
        timestamp: "14:45:06",
        riskLevel: "HIGH_RISK",
        icon: "🔴",
        statusText: "AI Identified Abnormal Pattern Requiring Attention",
        detectedCondition: "Continuous thermal overheating pattern flagged on radiator cooling fins.",
        explanation: "GridGuard AI model classified sustained thermal escalation exceeding standard baseline load envelope.",
        recommendation: "Initiate auxiliary cooling pumps on T-105 and monitor winding thermal trajectory.",
        status: "ACTIVE"
      },
      {
        alertId: "ALT-8903",
        assetId: "T-102",
        timestamp: "14:45:10",
        riskLevel: "WARNING",
        icon: "🟡",
        statusText: "Unusual Operating Pattern Detected",
        detectedCondition: "Elevated mechanical vibration harmonic frequency drift.",
        explanation: "Frequency spectrum shift in core clamping vibration harmonics.",
        recommendation: "Schedule vibration spectrum analysis during upcoming maintenance window.",
        status: "MONITORING"
      },
      {
        alertId: "ALT-8890",
        assetId: "T-101",
        timestamp: "12:10:00",
        riskLevel: "NORMAL",
        icon: "🟢",
        statusText: "No Abnormal Condition Detected",
        detectedCondition: "Nominal operational baseline across all parameters.",
        explanation: "AI model confirmed 99.4% confidence match with healthy transformer operational profile.",
        recommendation: "Continue standard continuous background GridGuard AI monitoring.",
        status: "RESOLVED"
      }
    ];

    this.init();
  }

  init() {
    this.dataService.subscribe(data => this.handleDataUpdate(data));

    // Filter Buttons Listener
    this.filterButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        this.filterButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentFilter = btn.getAttribute('data-alert-filter');
        this.renderAlertsTable();
      });
    });
  }

  handleDataUpdate(data) {
    if (!data) return;

    // 1. Update Active Alert Count Badge
    if (this.navAlertBadge && data.networkSummary) {
      const activeCount = data.networkSummary.warningCount + data.networkSummary.highRiskCount + data.networkSummary.criticalCount;
      this.navAlertBadge.textContent = activeCount;
    }

    // 2. Process incoming primary alert & show Toast if new
    if (data.primaryAlert && data.primaryAlert.id !== this.lastProcessedAlertId) {
      this.lastProcessedAlertId = data.primaryAlert.id;
      this.addAlertRecordFromPrimary(data.primaryAlert);
      this.showToastNotification(data.primaryAlert);
    }

    // 3. Render Dedicated Alerts Page Log Table
    this.renderAlertsTable();
  }

  addAlertRecordFromPrimary(primary) {
    let icon = "🔴";
    let statusText = "High Risk Detected";
    if (primary.severity === "CRITICAL") {
      icon = "🟣";
      statusText = "Critical risk detected. Immediate inspection is recommended.";
    } else if (primary.severity === "WARNING") {
      icon = "🟡";
      statusText = "An unusual operating pattern has been detected.";
    } else if (primary.severity === "NORMAL") {
      icon = "🟢";
      statusText = "No abnormal condition detected.";
    }

    const newRecord = {
      alertId: primary.id || `ALT-${Math.floor(1000 + Math.random() * 9000)}`,
      assetId: primary.assetId,
      timestamp: primary.timestamp,
      riskLevel: primary.severity,
      icon,
      statusText,
      detectedCondition: primary.detectedAbnormalCondition,
      explanation: primary.alertMessage,
      recommendation: primary.alertMessage,
      status: "ACTIVE"
    };

    // Prepend if unique
    if (!this.alertHistory.some(a => a.alertId === newRecord.alertId)) {
      this.alertHistory.unshift(newRecord);
    }
  }

  showToastNotification(alert) {
    if (!this.toastContainer) return;

    let toastClass = "toast-high-risk";
    let icon = "🔴";
    if (alert.severity === "CRITICAL") { toastClass = "toast-critical"; icon = "🟣"; }
    else if (alert.severity === "WARNING") { toastClass = "toast-warning"; icon = "🟡"; }
    else if (alert.severity === "NORMAL") { toastClass = "toast-normal"; icon = "🟢"; }

    const toast = document.createElement('div');
    toast.className = `toast-item ${toastClass}`;
    toast.innerHTML = `
      <div class="toast-header">
        <span class="toast-icon">${icon}</span>
        <strong>${alert.severity.replace('_', ' ')}: ${alert.assetId}</strong>
        <span class="toast-time">${alert.timestamp}</span>
      </div>
      <p class="toast-msg">${alert.alertTitle}</p>
    `;

    this.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('toast-fade-out');
      setTimeout(() => toast.remove(), 400);
    }, 4500);
  }

  renderAlertsTable() {
    if (!this.alertsContainer) return;

    let filtered = this.alertHistory;
    if (this.currentFilter !== 'all') {
      filtered = this.alertHistory.filter(a => a.riskLevel === this.currentFilter);
    }

    this.alertsContainer.innerHTML = filtered.map(a => {
      let borderClass = "border-normal";
      if (a.riskLevel === "CRITICAL") borderClass = "border-critical";
      else if (a.riskLevel === "HIGH_RISK") borderClass = "border-high-risk";
      else if (a.riskLevel === "WARNING") borderClass = "border-warning";

      return `
        <div class="alert-card-row ${borderClass}">
          <div class="alert-row-header">
            <div class="alert-row-title">
              <span class="alert-state-icon">${a.icon}</span>
              <strong>[${a.alertId}] ${a.assetId}</strong>
              <span class="badge badge-alert-level ${a.riskLevel.toLowerCase()}">${a.riskLevel.replace('_', ' ')}</span>
            </div>
            <span class="alert-row-time"><i data-lucide="clock" style="width:12px"></i> ${a.timestamp}</span>
          </div>

          <div class="alert-row-body">
            <div class="alert-field">
              <span class="field-label">AI Detected Condition:</span>
              <p>${a.detectedCondition}</p>
            </div>
            
            <div class="alert-field mt-2">
              <span class="field-label">AI Explanation:</span>
              <p class="text-muted">${a.explanation}</p>
            </div>

            <div class="alert-field mt-2">
              <span class="field-label">Prescriptive Recommendation:</span>
              <p class="text-accent">“${a.recommendation}”</p>
            </div>
          </div>

          <div class="alert-row-footer">
            <span class="status-indicator-tag">Status: <strong>${a.status}</strong></span>
            <button class="btn btn-sm btn-outline" onclick="window.app.switchSection('command-center')">
              Inspect in 3D Network
            </button>
          </div>
        </div>
      `;
    }).join('');

    if (window.lucide) window.lucide.createIcons();
  }
}

// Replace in window module space
window.AlertsViewComponent = AlertsViewComponent;
