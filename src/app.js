/**
 * APPLICATION MAIN ENTRY POINT & BOOTSTRAPPER
 * Coordinates navigation, component instances, and AI data bindings.
 */

document.addEventListener('DOMContentLoaded', () => {
  console.log('[APP] Initializing AI Transformer Early Warning Application Architecture...');

  // Initialize Data Layer Service
  const dataService = window.aiDataService;

  // Initialize UI Components & Services
  const navigation = new window.NavigationComponent();
  const commandCenter = new window.CommandCenterComponent(dataService);
  const transformerNetwork = new window.TransformerNetworkComponent(dataService);
  const aiInsights = new window.AiInsightsComponent(dataService);
  const alertsView = new window.AlertsViewComponent(dataService);
  const reportsView = new window.ReportsViewComponent(dataService);
  const settingsView = new window.SettingsViewComponent(dataService);

  // Initialize Interactive 3D Transformer Network Services
  const transformer3DCommand = new window.Transformer3DNetwork('network-canvas-container', dataService);
  const transformer3DGrid = new window.Transformer3DNetwork('grid-view-3d-container', dataService);

  // Initialize Real-time Sequential Dataset Simulation Stream Pipeline
  const simulationStream = new window.SimulationStreamService(dataService);

  // Global App Controller Reference
  window.app = {
    dataService,
    simulationStream,
    navigation,
    commandCenter,
    transformerNetwork,
    transformer3DCommand,
    transformer3DGrid,
    switchSection: (sectionId) => navigation.switchTab(sectionId)
  };

  // Manual Inference Refresh Button
  const btnRefresh = document.getElementById('btn-refresh-inference');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => {
      btnRefresh.style.transform = 'rotate(360deg)';
      btnRefresh.style.transition = 'transform 0.5s ease';
      dataService.triggerManualInference();
      setTimeout(() => { btnRefresh.style.transform = 'none'; }, 500);
    });
  }

  // Initialize Lucide Icons
  if (window.lucide) {
    window.lucide.createIcons();
  }

  console.log('[APP] Application booted successfully. GridGuard AI stream active.');
});
