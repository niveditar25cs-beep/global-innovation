/**
 * AI COMMAND CENTER COMPONENT
 * Primary dashboard view displaying AI Status, Overview Counters, 3D Transformer Network,
 * Prominent AI Alert, AI Recommendation, and Recent AI Events Timeline.
 */

class CommandCenterComponent {
  constructor(dataService) {
    this.dataService = dataService;
    
    // UI Selectors
    this.primaryAlertBox = document.getElementById('primary-alert-box');
    this.aiRecommendationBox = document.getElementById('ai-recommendation-box');
    this.spatialNodesWrapper = document.getElementById('spatial-nodes-wrapper');
    this.recentAiEventsBox = document.getElementById('recent-ai-events-box');

    // Counters
    this.countTotal = document.getElementById('count-total');
    this.countNormal = document.getElementById('count-normal');
    this.countWarning = document.getElementById('count-warning');
    this.countHighRisk = document.getElementById('count-high-risk');
    this.countCritical = document.getElementById('count-critical');
    this.countAlerts = document.getElementById('count-alerts');

    this.globalRiskText = document.getElementById('global-risk-text');

    this.init();
  }

  init() {
    // Subscribe to AI Data Stream
    this.dataService.subscribe(data => this.render(data));
  }

  render(data) {
    if (!data) return;

    // 1. Update Counters
    if (data.networkSummary) {
      this.animateCounter(this.countTotal, data.networkSummary.totalTransformers);
      this.animateCounter(this.countNormal, data.networkSummary.normalCount);
      this.animateCounter(this.countWarning, data.networkSummary.warningCount);
      this.animateCounter(this.countHighRisk, data.networkSummary.highRiskCount);
      this.animateCounter(this.countCritical, data.networkSummary.criticalCount);
      this.animateCounter(this.countAlerts, data.networkSummary.activeAlerts);
    }

    if (this.globalRiskText) {
      const highRiskCount = data.networkSummary ? data.networkSummary.highRiskCount : 1;
      this.globalRiskText.textContent = `${highRiskCount} HIGH RISK`;
    }

    // 2. Render Spatial Network Nodes
    this.renderSpatialNodes(data.transformers);

    // 3. Render Prominent AI Alert Panel
    this.renderPrimaryAlert(data.primaryAlert);

    // 4. Render AI Recommendation Panel
    this.renderRecommendations(data.recommendations);

    // 5. Render Recent AI Events Live Timeline
    this.renderRecentAiEvents(data.recentAiEvents);
    
    // Re-initialize Lucide icons for dynamically added content
    if (window.lucide) window.lucide.createIcons();
  }

  animateCounter(element, targetVal) {
    if (!element) return;
    element.textContent = targetVal;
  }

  renderSpatialNodes(transformers) {
    if (!this.spatialNodesWrapper) return;
    
    this.spatialNodesWrapper.innerHTML = transformers.map(tf => {
      let riskClass = "node-safe";
      if (tf.riskLevel === "CRITICAL") riskClass = "node-critical";
      else if (tf.riskLevel === "HIGH_RISK") riskClass = "node-high-risk";
      else if (tf.riskLevel === "WARNING") riskClass = "node-warning";

      return `
        <div class="spatial-node ${riskClass}" style="left: ${tf.spatialCoords.x}%; top: ${tf.spatialCoords.y}%;" title="Click to inspect ${tf.id} AI Diagnostic">
          <div class="node-icon-box">
            <i data-lucide="zap"></i>
          </div>
          <div class="node-label">${tf.id}</div>
          <div class="node-risk-tag">${tf.riskScore}% Risk</div>
        </div>
      `;
    }).join('');
  }

  renderPrimaryAlert(alert) {
    if (!this.primaryAlertBox || !alert) return;

    this.primaryAlertBox.innerHTML = `
      <div class="alert-header-block high-risk-block">
        <div class="alert-subtitle-tag"><i data-lucide="alert-triangle"></i> HIGH RISK DETECTED</div>
        <div class="alert-title">Transformer T-104</div>
        <div class="alert-timestamp">AI detected an abnormal operating pattern</div>
      </div>

      <div class="alert-detected-list mt-3">
        <h4 class="section-micro-title">Detected Abnormal Features:</h4>
        <ul class="detected-bullets">
          <li><i data-lucide="flame" class="icon-danger"></i> Continuous overheating pattern</li>
          <li><i data-lucide="trending-up" class="icon-warning"></i> Abnormal current increase</li>
          <li><i data-lucide="arrow-up-right" class="icon-purple"></i> Increasing risk trend</li>
        </ul>
      </div>

      <div class="alert-action-footer mt-4">
        <button class="btn btn-primary btn-sm" onclick="window.app.switchSection('ai-insights')">
          <i data-lucide="search"></i> [VIEW AI ANALYSIS]
        </button>
        <button class="btn btn-outline btn-sm" onclick="window.app.switchSection('transformer-network')">
          <i data-lucide="info"></i> [VIEW DETAILS]
        </button>
      </div>
    `;
  }

  renderRecommendations(recs) {
    if (!this.aiRecommendationBox) return;

    this.aiRecommendationBox.innerHTML = `
      <div class="ai-recommendation-quote-card">
        <div class="quote-header">
          <i data-lucide="quote" class="quote-icon"></i>
          <span>PRESCRIPTIVE AI GUIDANCE</span>
        </div>
        <p class="recommendation-text">
          “Inspect Transformer T-104 and its connected electrical line before the condition develops into a major failure.”
        </p>
        <div class="quote-action-row">
          <button class="btn btn-outline btn-sm" onclick="window.app.switchSection('ai-insights')">
            <i data-lucide="brain-circuit"></i> [VIEW AI ANALYSIS]
          </button>
          <button class="btn btn-secondary btn-sm" onclick="window.app.switchSection('transformer-network')">
            <i data-lucide="list"></i> [VIEW DETAILS]
          </button>
        </div>
      </div>
    `;
  }

  renderRecentAiEvents(events) {
    if (!this.recentAiEventsBox || !events) return;

    this.recentAiEventsBox.innerHTML = `
      <div class="events-timeline-list">
        ${events.map(ev => `
          <div class="timeline-item">
            <span class="timeline-time">${ev.time}</span>
            <span class="timeline-bullet"></span>
            <span class="timeline-msg">${ev.message}</span>
          </div>
        `).join('')}
      </div>
    `;
  }
}

window.CommandCenterComponent = CommandCenterComponent;
