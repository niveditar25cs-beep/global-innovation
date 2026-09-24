document.addEventListener('DOMContentLoaded', () => {
    // ---- Tab navigation ----
    const navLinks = document.querySelectorAll('.nav-link[data-tab]');
    const panels = document.querySelectorAll('.tab-panel');

    navLinks.forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            const tab = link.dataset.tab;
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            panels.forEach(p => p.classList.remove('active'));
            document.getElementById('tab-' + tab).classList.add('active');
            if (tab === 'history') {
    loadHistoricalCharts();
}
        });
    });

    // ---- Health check ----
    fetch('/api/health').then(r => r.json()).then(d => {
        document.getElementById('healthBadge').querySelector('.dot').className = 'dot green';
        document.getElementById('healthBadge').querySelector('span:last-child') || null;
        if (d.classification_model) {
            document.getElementById('clsModelBadge').textContent = 'Classification: ' + d.classification_model;
        }
        if (d.regression_model) {
            document.getElementById('regModelBadge').textContent = 'Regression: ' + d.regression_model;
        }
    }).catch(() => {
        document.getElementById('healthBadge').innerHTML = '<span class="dot" style="background:#ef4444;box-shadow:0 0 8px #ef4444"></span> Offline';
    });
        // ---- Load latest transformer reading + ML risk ----
    async function loadLatestTransformer() {
        try {
            const response = await fetch('/api/transformer/latest');

            if (!response.ok) {
                throw new Error('Failed to load transformer data');
            }

            const data = await response.json();

            if (data.status !== 'success') {
                throw new Error(data.message || 'No transformer data available');
            }

            const reading = data.reading;
            const risk = data.risk;

            // Helper: update an element only if it exists
            function updateElement(id, value) {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = value;
                }
            }

            // Basic transformer information
            updateElement('transformerId', data.transformer_id);
            updateElement('lastUpdate', new Date(reading.DeviceTimeStamp).toLocaleString());

            // Sensor values
            updateElement('otiValue', reading.OTI + ' °C');
            updateElement('wtiValue', reading.WTI + ' °C');
            updateElement('atiValue', reading.ATI + ' °C');

            updateElement('voltageL1', reading.VL1 + ' V');
            updateElement('voltageL2', reading.VL2 + ' V');
            updateElement('voltageL3', reading.VL3 + ' V');

            updateElement('currentL1', reading.IL1 + ' A');
            updateElement('currentL2', reading.IL2 + ' A');
            updateElement('currentL3', reading.IL3 + ' A');

            updateElement('powerValue', reading.KW + ' kW');
            updateElement('powerFactorValue', reading.Avg_PF);

            // ML risk result
            updateElement('monitorRiskLevel', risk.predicted_risk_level);
updateElement('monitorPredTemp', risk.predicted_oil_temperature_celsius + ' °C');
updateElement('monitorProbNormal', (risk.probabilities.Normal * 100).toFixed(1) + '%');
updateElement('monitorProbWarning', (risk.probabilities.Warning * 100).toFixed(1) + '%');
updateElement('monitorProbCritical', (risk.probabilities.Critical_Alarm * 100).toFixed(1) + '%');

            // Overall safety status
            const statusElement = document.getElementById('transformerStatus');

            if (statusElement) {
                statusElement.textContent = risk.safety_status;
                statusElement.className = 'status-value ' +
                    risk.safety_status.toLowerCase();
            }

            console.log('Transformer data updated:', data);

        } catch (error) {
            console.error('Transformer API error:', error);
        }
    }

    // Load transformer data once when dashboard opens
    loadLatestTransformer();
        // ---- Automatic transformer monitoring ----
    setInterval(() => {
        loadLatestTransformer();
    }, 10000);
    // ---- Load dashboard data ----
    fetch('/api/metadata').then(r => r.json()).then(meta => {
        // Classification report
        if (meta.classification_results) {
            let txt = 'Model Comparison:\n\n';
            for (const [name, m] of Object.entries(meta.classification_results)) {
                txt += `${name}:\n  Train Acc: ${m.train_accuracy}  Test Acc: ${m.test_accuracy}  F1: ${m.test_f1_macro}\n\n`;
            }
            txt += `Best Model: ${meta.best_classification_model}\n`;
            document.getElementById('clsReport').textContent = txt;
        }
        // Regression metrics
        if (meta.regression_results) {
            let txt = 'Model Comparison:\n\n';
            for (const [name, m] of Object.entries(meta.regression_results)) {
                txt += `${name}:\n  RMSE: ${m.test_rmse}  MAE: ${m.test_mae}  R2: ${m.test_r2}\n\n`;
            }
            txt += `Best Model: ${meta.best_regression_model}\n`;
            document.getElementById('regMetrics').textContent = txt;
        }
    }).catch(() => {});

    // ---- Single prediction form ----
    const predictForm = document.getElementById('predictForm');
    const predictBtn = document.getElementById('predictBtn');
    const resultPanel = document.getElementById('resultPanel');

    predictForm.addEventListener('submit', async e => {
        e.preventDefault();
        predictBtn.disabled = true;
        predictBtn.innerHTML = '<span class="btn-icon">...</span> Analyzing...';

        const formData = new FormData(predictForm);
        const payload = {};
        for (const [key, val] of formData.entries()) {
            payload[key] = parseFloat(val) || 0;
        }

        try {
            const resp = await fetch('/api/predict/alarm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();

            resultPanel.classList.remove('hidden');

            // Status indicator
            const si = document.getElementById('statusIndicator');
            const icon = document.getElementById('statusIcon');
            const label = document.getElementById('statusLabel');
            const sub = document.getElementById('statusSub');

            si.className = 'status-indicator';
            if (data.safety_status === 'CRITICAL') {
                si.classList.add('critical');
                icon.textContent = '🚨';
                label.textContent = 'CRITICAL ALARM';
                sub.textContent = 'Risk Level 2 - Immediate attention required!';
            } else if (data.safety_status === 'WARNING') {
                si.classList.add('warning');
                icon.textContent = '⚠️';
                label.textContent = 'WARNING';
                sub.textContent = 'Risk Level 1 - Pre-alarm condition detected';
            } else {
                si.classList.add('optimal');
                icon.textContent = '✅';
                label.textContent = 'OPTIMAL';
                sub.textContent = 'Risk Level 0 - Normal Operation';
            }

            document.getElementById('riskLevel').textContent = data.predicted_risk_level;
            document.getElementById('predTemp').textContent = data.predicted_oil_temperature_celsius + ' C';
            document.getElementById('probNormal').textContent = (data.probabilities.Normal * 100).toFixed(1) + '%';
            document.getElementById('probWarning').textContent = (data.probabilities.Warning * 100).toFixed(1) + '%';
            document.getElementById('probCritical').textContent = (data.probabilities.Critical_Alarm * 100).toFixed(1) + '%';

            resultPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } catch (err) {
            alert('Prediction failed: ' + err.message);
        } finally {
            predictBtn.disabled = false;
            predictBtn.innerHTML = '<span class="btn-icon">&#9889;</span> Analyze &amp; Predict';
        }
    });

    // ---- Batch upload ----
    const batchForm = document.getElementById('batchForm');
    batchForm.addEventListener('submit', async e => {
        e.preventDefault();
        const fileInput = document.getElementById('csvFile');
        if (!fileInput.files.length) return alert('Please select a CSV file');

        const fd = new FormData();
        fd.append('file', fileInput.files[0]);

        try {
            const resp = await fetch('/api/predict/batch', { method: 'POST', body: fd });
            const data = await resp.json();

            const batchResult = document.getElementById('batchResult');
            batchResult.classList.remove('hidden');

            // Summary
            const summary = document.getElementById('batchSummary');
            summary.innerHTML = `<p><strong>${data.total_rows}</strong> rows processed. 
                Risk Distribution: Normal=${data.risk_distribution['0'] || 0}, 
                Warning=${data.risk_distribution['1'] || 0}, 
                Critical=${data.risk_distribution['2'] || 0}</p>`;

            // Table preview (first 20 rows)
            const tableDiv = document.getElementById('batchTable');
            if (data.preview && data.preview.length) {
                const cols = Object.keys(data.preview[0]);
                let html = '<table><thead><tr>';
                cols.forEach(c => html += `<th>${c}</th>`);
                html += '</tr></thead><tbody>';
                data.preview.forEach(row => {
                    html += '<tr>';
                    cols.forEach(c => html += `<td>${row[c]}</td>`);
                    html += '</tr>';
                });
                html += '</tbody></table>';
                tableDiv.innerHTML = html;
            }
        } catch (err) {
            alert('Batch prediction failed: ' + err.message);
        }
    });

    // Drag & drop visual feedback
    const zone = document.getElementById('uploadZone');
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.style.borderColor = '#6366f1'; });
    zone.addEventListener('dragleave', () => { zone.style.borderColor = ''; });
    zone.addEventListener('drop', () => { zone.style.borderColor = ''; });
});
// ============================================================
// Historical Transformer Trends
// ============================================================

let temperatureChart = null;
let voltageChart = null;
let currentChart = null;
let powerChart = null;

async function loadHistoricalCharts() {
    try {
        const response = await fetch('/api/transformer/history?limit=50');

        if (!response.ok) {
            throw new Error('Failed to load historical readings');
        }

        const data = await response.json();

        if (data.status !== 'success' || !data.readings.length) {
            throw new Error('No historical readings available');
        }

        // API returns newest → oldest.
        // Reverse so charts display oldest → newest.
        const readings = [...data.readings].reverse();

        const labels = readings.map(
            reading => new Date(reading.DeviceTimeStamp).toLocaleString()
        );

        const temperatureData = {
            oti: readings.map(r => r.OTI),
            wti: readings.map(r => r.WTI),
            ati: readings.map(r => r.ATI)
        };

        const voltageData = {
            l1: readings.map(r => r.VL1),
            l2: readings.map(r => r.VL2),
            l3: readings.map(r => r.VL3)
        };

        const currentData = {
            l1: readings.map(r => r.IL1),
            l2: readings.map(r => r.IL2),
            l3: readings.map(r => r.IL3)
        };

        const powerData = readings.map(r => r.KW);

        // Destroy previous charts before recreating them
        if (temperatureChart) temperatureChart.destroy();
        if (voltageChart) voltageChart.destroy();
        if (currentChart) currentChart.destroy();
        if (powerChart) powerChart.destroy();

        // Temperature Chart
        temperatureChart = new Chart(
            document.getElementById('temperatureChart'),
            {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'OTI (°C)',
                            data: temperatureData.oti,
                            tension: 0.3
                        },
                        {
                            label: 'WTI (°C)',
                            data: temperatureData.wti,
                            tension: 0.3
                        },
                        {
                            label: 'ATI (°C)',
                            data: temperatureData.ati,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            }
        );

        // Voltage Chart
        voltageChart = new Chart(
            document.getElementById('voltageChart'),
            {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'VL1 (V)',
                            data: voltageData.l1,
                            tension: 0.3
                        },
                        {
                            label: 'VL2 (V)',
                            data: voltageData.l2,
                            tension: 0.3
                        },
                        {
                            label: 'VL3 (V)',
                            data: voltageData.l3,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            }
        );

        // Current Chart
        currentChart = new Chart(
            document.getElementById('currentChart'),
            {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'IL1 (A)',
                            data: currentData.l1,
                            tension: 0.3
                        },
                        {
                            label: 'IL2 (A)',
                            data: currentData.l2,
                            tension: 0.3
                        },
                        {
                            label: 'IL3 (A)',
                            data: currentData.l3,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            }
        );

        // Power Chart
        powerChart = new Chart(
            document.getElementById('powerChart'),
            {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Power (kW)',
                            data: powerData,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            }
        );

        console.log('Historical charts loaded:', readings.length, 'readings');

    } catch (error) {
        console.error('Historical chart error:', error);
    }
}