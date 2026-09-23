/**
 * AI INSIGHTS & EXPLANATION ENGINE COMPONENT
 * Renders AI Analysis statements, risk trend trajectory, detection history,
 * and prescriptive operator recommendations in clear non-technical language.
 */

class AiInsightsComponent {
  constructor(dataService) {
    this.dataService = dataService;
    this.statementsList = document.getElementById('insights-analysis-statements');
    this.historyList = document.getElementById('insights-detection-history');
    this.recommendationsList = document.getElementById('insights-recommendations-list');
    this.assetTag = document.getElementById('insights-asset-tag');

    this.init();
  }

  init() {
    this.dataService.subscribe(data => this.render(data));
  }

  render(data) {
    if (!data) return;

    const alert = data.primaryAlert;
    if (this.assetTag && alert) {
      this.assetTag.textContent = `TARGET: ${alert.assetId || 'T-104'}`;
    }

    // Render Detection History
    if (this.historyList && data.recentAiEvents) {
      this.historyList.innerHTML = data.recentAiEvents.map(ev => `
        <div class="history-item">
          <div class="history-time">${ev.time}</div>
          <div class="history-content">
            <strong>${ev.message}</strong>
            <p>AI model evaluated background continuous dataset stream.</p>
          </div>
          <span class="badge badge-risk">FLAGGED</span>
        </div>
      `).join('');
    }

    if (window.lucide) window.lucide.createIcons();
  }
}

window.AiInsightsComponent = AiInsightsComponent;
