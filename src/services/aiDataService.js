/**
 * AI DATA SERVICE & ABSTRACTION LAYER
 * 
 * Provides a clean boundary between the UI components and backend AI inference engines.
 * Designed to easily switch between Mock Stream (Dev), REST API Endpoint, or WebSocket streams.
 */

class AIDataService {
  constructor() {
    this.subscribers = [];
    this.currentProviderMode = 'mock-stream';
    this.apiEndpoint = 'https://api.gridguard-ai.internal/v1/infer/transformers';
    this.pollingIntervalMs = 5000;
    this.timerId = null;

    // Standardized Initial AI State (Not hardcoded into UI components)
    this.aiState = {
      sentinelStatus: {
        active: true,
        latencyMs: 42,
        modelName: "TransfRisk-v4.8 (LSTM+Transformer)",
        evaluationRatePerSec: 120,
        lastInferenceTimestamp: new Date().toISOString()
      },
      networkSummary: {
        totalTransformers: 14,
        normalCount: 11,
        warningCount: 1,
        highRiskCount: 1,
        criticalCount: 1,
        activeAlerts: 3
      },
      globalGridRisk: {
        level: "1 HIGH RISK", // Network Risk Status
        maxProbability: 78.4,
        timeToFailureHours: 18,
        activeAlertCount: 3,
        networkHealthIndex: 82.1
      },
      recentAiEvents: [
        { time: "13:42:08", message: "T-104 abnormal pattern detected" },
        { time: "13:42:12", message: "Continuous overheating identified" },
        { time: "13:42:15", message: "Risk increased to HIGH" },
        { time: "13:42:16", message: "Preventive alert generated" }
      ],
      transformers: [
        {
          id: "T-101",
          name: "Transformer T-101",
          substation: "Substation Alpha - North Substation",
          ratedCapacity: "150 MVA",
          voltageLevel: "230kV / 69kV",
          riskScore: 5.2,
          riskLevel: "NORMAL", // Normal (Green)
          predictedFailureWindow: "Nominal Baseline",
          aiStatus: "NORMAL MONITORING",
          position3D: { x: -14, y: 1.5, z: -10 },
          anomalies: []
        },
        {
          id: "T-102",
          name: "Transformer T-102",
          substation: "Substation Alpha - East Node",
          ratedCapacity: "200 MVA",
          voltageLevel: "500kV / 230kV",
          riskScore: 8.4,
          riskLevel: "NORMAL", // Normal (Green)
          predictedFailureWindow: "Nominal Baseline",
          aiStatus: "NORMAL MONITORING",
          position3D: { x: 0, y: 1.5, z: -12 },
          anomalies: []
        },
        {
          id: "T-103",
          name: "Transformer T-103",
          substation: "Substation Beta - Central Loop",
          ratedCapacity: "180 MVA",
          voltageLevel: "230kV / 115kV",
          riskScore: 38.5,
          riskLevel: "WARNING", // Warning (Yellow/Orange)
          predictedFailureWindow: "5 - 8 Days",
          aiStatus: "UNUSUAL OPERATING PATTERN",
          position3D: { x: 14, y: 1.5, z: -10 },
          anomalies: ["Elevated mechanical vibration harmonic frequency drift"]
        },
        {
          id: "T-104",
          name: "Transformer T-104",
          substation: "Substation Beta - West High Voltage Node",
          ratedCapacity: "150 MVA",
          voltageLevel: "230kV / 69kV",
          riskScore: 78.4,
          riskLevel: "HIGH_RISK", // High Risk (Red) - Prominently Highlighted
          predictedFailureWindow: "18 - 24 Hours",
          aiStatus: "HIGH RISK DETECTED",
          position3D: { x: -10, y: 1.5, z: 10 },
          anomalies: [
            "Continuous overheating pattern",
            "Abnormal current increase",
            "Increasing risk trend"
          ],
          recommendation: "Inspect Transformer T-104 and its connected electrical line before the condition develops into a major failure."
        },
        {
          id: "T-105",
          name: "Transformer T-105",
          substation: "Substation Gamma - South Substation",
          ratedCapacity: "250 MVA",
          voltageLevel: "500kV / 230kV",
          riskScore: 6.8,
          riskLevel: "NORMAL", // Normal (Green)
          predictedFailureWindow: "Nominal Baseline",
          aiStatus: "NORMAL MONITORING",
          position3D: { x: 4, y: 1.5, z: 10 },
          anomalies: []
        },
        {
          id: "T-106",
          name: "Transformer T-106",
          substation: "Substation Gamma - Metro Feeder",
          ratedCapacity: "100 MVA",
          voltageLevel: "115kV / 13.8kV",
          riskScore: 94.2,
          riskLevel: "CRITICAL", // Critical (Purple)
          predictedFailureWindow: "4 - 8 Hours",
          aiStatus: "CRITICAL FAULT IMPENDING",
          position3D: { x: 16, y: 1.5, z: 12 },
          anomalies: [
            "Cellulose paper thermal breakdown signature",
            "Incipient dielectric arcing pattern"
          ],
          recommendation: "Execute emergency load shed on T-106 feeder line immediately."
        }
      ],
      primaryAlert: {
        id: "ALT-8902",
        assetId: "TX-104",
        substationNode: "Substation Beta - West High Voltage Node",
        alertTitle: "Critical Incipient Bushing Dielectric & Arcing Pattern Flagged",
        timestamp: "2 mins ago (14:02:10)",
        severity: "CRITICAL",
        failureProbability: "78.4%",
        estimatedTimeToFailure: "18 Hours",
        detectedAbnormalCondition: "High-frequency ultrasonic acoustic transient discharge coupled with localized oil temperature delta spike.",
        alertMessage: "GridGuard AI detected non-linear thermal escalation in Bushing B exceeding healthy transformer baseline envelope."
      },
      aiExplanation: {
        modelConfidence: "94.8%",
        signatureMatch: "Cellulose Paper Thermal Breakdown & Incipient Arcing Signature (Ref Pattern #B-402)",
        explanationText: "The AI anomaly detection ensemble identified a simultaneous divergence across acoustic ultrasonic energy signatures and oil thermal rate-of-rise. The pattern closely matches historical transformer winding insulation breakdown profiles recorded prior to catastrophic dielectric rupture.",
        featureAttributions: [
          { featureName: "Acoustic Partial Discharge Energy (kHz)", weight: 42 },
          { featureName: "Bushing B Temp Gradient ΔT/dt", weight: 35 },
          { featureName: "Dissolved Gas Ratio Dynamic Shift", weight: 15 },
          { featureName: "Vibration Harmonic Delta", weight: 8 }
        ]
      },
      recommendations: [
        {
          step: 1,
          title: "Immediate Grid Load Shedding / Rerouting",
          description: "Initiate remote load transfer to decrease current stress on TX-104 by at least 25% within 2 hours.",
          urgency: "HIGH"
        },
        {
          step: 2,
          title: "Dispatch Field Diagnostic Team with Infrared / Acoustic Sensors",
          description: "Inspect Bushing B thermal imaging camera feed and conduct dissolved gas sample analysis.",
          urgency: "HIGH"
        },
        {
          step: 3,
          title: "Prepare Emergency Transformer Isolation Playbook",
          description: "Pre-authorize Substation Beta automatic breaker opening if risk score exceeds 85%.",
          urgency: "MEDIUM"
        }
      ]
    };

    this.startStreaming();
  }

  /**
   * Subscribe to AI state updates
   * @param {Function} callback 
   */
  subscribe(callback) {
    this.subscribers.push(callback);
    // Push immediate state on subscription
    callback(this.aiState);
    return () => {
      this.subscribers = this.subscribers.filter(cb => cb !== callback);
    };
  }

  notify() {
    this.subscribers.forEach(cb => cb(this.aiState));
  }

  /**
   * Return current snapshot of AI telemetry
   */
  getSnapshot() {
    return this.aiState;
  }

  /**
   * Set API Service Mode
   */
  setProviderMode(mode, endpoint) {
    this.currentProviderMode = mode;
    if (endpoint) this.apiEndpoint = endpoint;
    console.log(`[AIDataService] Switched data provider to: ${mode} (${this.apiEndpoint})`);
  }

  /**
   * Simulated Real-Time AI Inference Engine (Mimics background backend updates)
   */
  startStreaming() {
    if (this.timerId) clearInterval(this.timerId);

    this.timerId = setInterval(() => {
      if (this.currentProviderMode === 'mock-stream') {
        // Minor dynamic jitter to prove live monitoring
        const delta = (Math.random() - 0.48) * 0.4;
        const currentScore = this.aiState.transformers[0].riskScore;
        const newScore = Math.min(99.9, Math.max(50.0, currentScore + delta));
        
        this.aiState.transformers[0].riskScore = parseFloat(newScore.toFixed(1));
        this.aiState.globalGridRisk.maxProbability = parseFloat(newScore.toFixed(1));
        this.aiState.primaryAlert.failureProbability = `${newScore.toFixed(1)}%`;
        this.aiState.sentinelStatus.lastInferenceTimestamp = new Date().toISOString();

        this.notify();
      }
    }, this.pollingIntervalMs);
  }

  /**
   * Apply sequential dataset record inference from SimulationStreamService
   */
  applyDatasetInference(record) {
    if (!record || !record.aiInference) return;

    const inf = record.aiInference;
    const targetTf = this.aiState.transformers.find(t => t.id === record.targetAssetId);

    if (targetTf) {
      targetTf.riskScore = inf.riskScore;
      targetTf.riskLevel = inf.riskLevel;
      targetTf.aiStatus = inf.aiStatus;
      targetTf.predictedFailureWindow = inf.timeToFailure;
    }

    // Update Global Risk Metrics
    this.aiState.globalGridRisk.maxProbability = inf.riskScore;
    this.aiState.globalGridRisk.timeToFailureHours = inf.timeToFailure;
    this.aiState.sentinelStatus.lastInferenceTimestamp = new Date().toISOString();

    // Update Primary Alert
    this.aiState.primaryAlert = {
      id: record.recordId,
      assetId: record.targetAssetId,
      substationNode: targetTf ? targetTf.substation : "Substation Beta",
      alertTitle: `${inf.riskLevel.replace('_', ' ')}: ${inf.aiStatus}`,
      timestamp: `${record.timestamp} (Simulated Record)`,
      severity: inf.riskLevel,
      failureProbability: `${inf.riskScore}%`,
      estimatedTimeToFailure: inf.timeToFailure,
      detectedAbnormalCondition: inf.alertMessage,
      alertMessage: inf.alertMessage
    };

    // Update XAI Feature Attribution
    if (inf.xaiFeatures) {
      this.aiState.aiExplanation.featureAttributions = inf.xaiFeatures;
    }

    // Update Recommendation Text
    if (inf.recommendationText) {
      this.aiState.recommendations[0].description = inf.recommendationText;
    }

    // Prepend to Live Events Timeline
    if (record.eventLog) {
      this.aiState.recentAiEvents.unshift({
        time: record.timestamp,
        message: record.eventLog
      });
      if (this.aiState.recentAiEvents.length > 8) {
        this.aiState.recentAiEvents.pop();
      }
    }

    // Recalculate summary counters
    let normal = 0, warning = 0, highRisk = 0, critical = 0;
    this.aiState.transformers.forEach(t => {
      if (t.riskLevel === 'NORMAL') normal++;
      else if (t.riskLevel === 'WARNING') warning++;
      else if (t.riskLevel === 'HIGH_RISK') highRisk++;
      else if (t.riskLevel === 'CRITICAL') critical++;
    });

    this.aiState.networkSummary.normalCount = normal;
    this.aiState.networkSummary.warningCount = warning;
    this.aiState.networkSummary.highRiskCount = highRisk;
    this.aiState.networkSummary.criticalCount = critical;

    this.notify();
  }

  /**
   * Manual Refresh Trigger
   */
  triggerManualInference() {
    this.aiState.sentinelStatus.lastInferenceTimestamp = new Date().toISOString();
    this.notify();
  }
}

// Global Singleton Instance for application-wide service usage
window.aiDataService = new AIDataService();
