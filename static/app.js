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
