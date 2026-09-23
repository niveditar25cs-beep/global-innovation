/**
 * NAVIGATION COMPONENT
 * Handles section switching, top header title updates, and mobile/desktop responsive state.
 */

class NavigationComponent {
  constructor() {
    this.navButtons = document.querySelectorAll('.nav-item');
    this.viewSections = document.querySelectorAll('.view-section');
    this.pageTitleEl = document.getElementById('page-title');
    
    this.sectionTitles = {
      'command-center': 'GRIDGUARD AI — Transformer Risk Monitoring',
      'interactive-3d': 'GRIDGUARD AI — Interactive 3D Grid View',
      'transformer-network': 'GRIDGUARD AI — Transformer Network',
      'ai-insights': 'GRIDGUARD AI — Insights & XAI',
      'alerts': 'GRIDGUARD AI — Alerts & Playbooks',
      'reports': 'GRIDGUARD AI — Risk & Health Reports',
      'settings': 'GRIDGUARD AI — Model Settings & API'
    };

    this.initEvents();
  }

  initEvents() {
    this.navButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetSection = btn.getAttribute('data-section');
        this.switchTab(targetSection);
      });
    });
  }

  switchTab(sectionId) {
    // Update active nav button
    this.navButtons.forEach(btn => {
      if (btn.getAttribute('data-section') === sectionId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Update section visibility
    this.viewSections.forEach(section => {
      const sectionName = section.id.replace('section-', '');
      if (sectionName === sectionId) {
        section.classList.add('active');
      } else {
        section.classList.remove('active');
      }
    });

    // Update Header Title
    if (this.pageTitleEl && this.sectionTitles[sectionId]) {
      this.pageTitleEl.textContent = this.sectionTitles[sectionId];
    }

    // Trigger Resize for WebGL canvas container recalculations
    window.dispatchEvent(new Event('resize'));
  }
}

window.NavigationComponent = NavigationComponent;
