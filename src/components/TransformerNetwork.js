/**
 * TRANSFORMER NETWORK COMPONENT
 * Renders the fleet-wide grid transformer inventory table and handles filtering.
 */

class TransformerNetworkComponent {
  constructor(dataService) {
    this.dataService = dataService;
    this.tableBody = document.getElementById('transformer-network-table-body');
    this.filterButtons = document.querySelectorAll('.btn-filter');
    this.currentFilter = 'all';

    this.init();
  }

  init() {
    this.dataService.subscribe(data => this.render(data.transformers));
    
    this.filterButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.filterButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentFilter = btn.getAttribute('data-filter');
        const data = this.dataService.getSnapshot();
        this.render(data.transformers);
      });
    });
  }

  render(transformers) {
    if (!this.tableBody || !transformers) return;

    let filtered = transformers;
    if (this.currentFilter === 'critical') {
      filtered = transformers.filter(t => t.riskLevel === 'CRITICAL' || t.riskLevel === 'WARNING');
    } else if (this.currentFilter === 'normal') {
      filtered = transformers.filter(t => t.riskLevel === 'NORMAL');
    }

    this.tableBody.innerHTML = filtered.map(tf => {
      let badgeClass = 'badge-info';
      if (tf.riskLevel === 'CRITICAL') badgeClass = 'badge-risk';
      else if (tf.riskLevel === 'WARNING') badgeClass = 'badge-count';

      return `
        <tr>
          <td><strong>${tf.id}</strong></td>
          <td>${tf.substation}</td>
          <td>${tf.ratedCapacity}</td>
          <td>
            <strong class="${tf.riskLevel === 'CRITICAL' ? 'danger-text' : ''}">${tf.riskScore}% Failure Risk</strong>
          </td>
          <td>${tf.predictedFailureWindow}</td>
          <td><span class="badge ${badgeClass}">${tf.aiStatus}</span></td>
          <td>
            <button class="btn btn-sm btn-outline" onclick="window.app.switchSection('command-center')">
              Inspect AI Diagnostics
            </button>
          </td>
        </tr>
      `;
    }).join('');
  }
}

window.TransformerNetworkComponent = TransformerNetworkComponent;
