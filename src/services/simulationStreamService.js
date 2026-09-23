/**
 * SIMULATION DATA STREAM SERVICE
 * Sequential Dataset Batch Pipeline Simulator.
 * Simulates real-time incoming transformer dataset records flowing through:
 * Dataset Record -> Backend Data Pipeline -> AI Risk Model -> AI Diagnosis -> Real-Time UI & 3D Updates
 */

class SimulationStreamService {
  constructor(aiDataService) {
    this.aiDataService = aiDataService;
    this.isRunning = true;
    this.streamSpeedMs = 4000; // New AI evaluation result every 4 seconds
    this.datasetSequenceIndex = 0;
    this.timerId = null;

    // Prototype Dataset Stream Records (Sequentially processed records)
    this.datasetStreamRecords = [
      {
        recordId: "BATCH-8901",
        timestamp: "14:45:02",
        targetAssetId: "T-104",
        aiInference: {
          riskScore: 84.2,
          riskLevel: "CRITICAL",
          aiStatus: "INCIPIENT FAULT DETECTED",
          timeToFailure: "18 Hours",
          alertMessage: "High-frequency ultrasonic acoustic transient discharge coupled with localized oil thermal delta spike.",
          xaiFeatures: [
            { featureName: "Acoustic Partial Discharge Energy (kHz)", weight: 44 },
            { featureName: "Bushing B Temp Gradient ΔT/dt", weight: 34 },
            { featureName: "Dissolved Gas Ratio Dynamic Shift", weight: 14 },
            { featureName: "Vibration Harmonic Delta", weight: 8 }
          ],
          recommendationText: "“Inspect Transformer T-104 and its connected electrical line before the condition develops into a major failure.”"
        },
        eventLog: "14:45:02 — GridGuard AI flagged acoustic surge pattern on T-104"
      },
      {
        recordId: "BATCH-8902",
        timestamp: "14:45:06",
        targetAssetId: "T-105",
        aiInference: {
          riskScore: 71.5,
          riskLevel: "HIGH_RISK",
          aiStatus: "THERMAL OVERHEATING PATTERN",
          timeToFailure: "28 Hours",
          alertMessage: "Sustained load thermal buildup detected on T-105 radiator cooling fins.",
          xaiFeatures: [
            { featureName: "Radiator Thermal Gradient ΔT", weight: 52 },
            { featureName: "Load Current Escalation Ratio", weight: 28 },
            { featureName: "Oil Circulation Velocity Delta", weight: 20 }
          ],
          recommendationText: "“Initiate auxiliary cooling pumps on T-105 and monitor winding thermal trajectory.”"
        },
        eventLog: "14:45:06 — T-105 thermal overheating trend classified by model"
      },
      {
        recordId: "BATCH-8903",
        timestamp: "14:45:10",
        targetAssetId: "T-102",
        aiInference: {
          riskScore: 42.0,
          riskLevel: "WARNING",
          aiStatus: "ELEVATED VIBRATION DRIFT",
          timeToFailure: "5 Days",
          alertMessage: "Harmonic mechanical frequency distortion detected on T-102 core assembly.",
          xaiFeatures: [
            { featureName: "Harmonic Mechanical Frequency", weight: 60 },
            { featureName: "Acoustic Noise Floor Shift", weight: 25 },
            { featureName: "Core Clamping Pressure Proxy", weight: 15 }
          ],
          recommendationText: "“Schedule vibration spectrum analysis on T-102 during upcoming maintenance window.”"
        },
        eventLog: "14:45:10 — T-102 mechanical vibration drift evaluated"
      },
      {
        recordId: "BATCH-8904",
        timestamp: "14:45:14",
        targetAssetId: "T-104",
        aiInference: {
          riskScore: 91.8,
          riskLevel: "CRITICAL",
          aiStatus: "INCIPIENT DIELECTRIC RUPTURE",
          timeToFailure: "12 Hours",
          alertMessage: "Non-linear thermal escalation in Bushing B exceeding health baseline safety envelope.",
          xaiFeatures: [
            { featureName: "Acoustic Partial Discharge Energy (kHz)", weight: 48 },
            { featureName: "Bushing B Temp Gradient ΔT/dt", weight: 36 },
            { featureName: "Dissolved Gas Ratio Dynamic Shift", weight: 16 }
          ],
          recommendationText: "“CRITICAL PREVENTIVE ACTION: Execute remote load shed on T-104 immediately.”"
        },
        eventLog: "14:45:14 — Risk score for T-104 escalated to 91.8% CRITICAL"
      }
    ];

    this.startSimulation();
  }

  startSimulation() {
    if (this.timerId) clearInterval(this.timerId);

    this.timerId = setInterval(() => {
      if (!this.isRunning) return;
      this.processNextRecordBatch();
    }, this.streamSpeedMs);
  }

  processNextRecordBatch() {
    const record = this.datasetStreamRecords[this.datasetSequenceIndex];
    this.datasetSequenceIndex = (this.datasetSequenceIndex + 1) % this.datasetStreamRecords.length;

    // Pulse live stream status indicator in UI
    this.updateLiveIndicator(record);

    // Apply dataset record result to AI Data Service
    this.aiDataService.applyDatasetInference(record);
  }

  updateLiveIndicator(record) {
    const pulseEl = document.getElementById('live-stream-pulse-badge');
    if (pulseEl) {
      pulseEl.classList.add('pulse-flash');
      setTimeout(() => pulseEl.classList.remove('pulse-flash'), 600);
    }

    const batchMetaEl = document.getElementById('live-batch-meta');
    if (batchMetaEl) {
      batchMetaEl.textContent = `Batch: ${record.recordId} • Asset: ${record.targetAssetId} (${record.timestamp})`;
    }
  }

  togglePause() {
    this.isRunning = !this.isRunning;
    return this.isRunning;
  }
}

window.SimulationStreamService = SimulationStreamService;
