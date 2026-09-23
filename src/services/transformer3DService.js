/**
 * 3D TRANSFORMER NETWORK VISUALIZER SERVICE & COMPONENT
 * Functional Three.js WebGL spatial infrastructure model.
 * Renders realistic transformer models (T-101 to T-106), power lines,
 * power-flow pulse particles, glowing status indicators, AI diagnostic side panel, raycaster selection, and camera controls.
 */

class Transformer3DNetwork {
  constructor(containerId, dataService) {
    this.container = document.getElementById(containerId);
    this.dataService = dataService;

    if (!this.container) return;

    if (!window.THREE || !this.isWebGLAvailable()) {
      console.warn('[3D Network] WebGL context or Three.js unavailable. Displaying graceful fallback.');
      this.showFallbackMessage();
      return;
    }

    this.transformersMap = new Map();
    this.selectableMeshes = [];
    this.powerLinesList = [];
    this.flowPulseParticles = [];
    this.selectedTransformerId = null;

    this.initScene();
    this.initLights();
    this.initSubstationEnvironment();
    this.initEventListeners();
    this.animate();

    // Subscribe to AI state updates
    this.dataService.subscribe(data => this.updateStatusFromData(data.transformers));
  }

  initScene() {
    const width = this.container.clientWidth || 800;
    const height = this.container.clientHeight || 450;

    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x050811);
    this.scene.fog = new THREE.FogExp2(0x050811, 0.015);

    // Camera
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    this.defaultCameraPos = new THREE.Vector3(0, 24, 40);
    this.camera.position.copy(this.defaultCameraPos);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // Clear container and append canvas
    this.container.innerHTML = '';
    this.container.appendChild(this.renderer.domElement);

    // OrbitControls (Rotate, Zoom, Pan)
    if (window.THREE.OrbitControls) {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;
      this.controls.maxPolarAngle = Math.PI / 2.05; // Stay above ground
      this.controls.minDistance = 6;
      this.controls.maxDistance = 85;
      this.controls.target.set(0, 0, 0);
    }

    // Raycaster for click selection
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
  }

  initLights() {
    // Ambient Light
    const ambientLight = new THREE.AmbientLight(0x1e293b, 1.3);
    this.scene.add(ambientLight);

    // Main Sunlight / Grid Spot
    const dirLight = new THREE.DirectionalLight(0x38bdf8, 1.6);
    dirLight.position.set(20, 40, 20);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    this.scene.add(dirLight);

    // Substation Ambient Cyan Glow
    const pointLight = new THREE.PointLight(0x06b6d4, 1.2, 50);
    pointLight.position.set(0, 15, 0);
    this.scene.add(pointLight);
  }

  initSubstationEnvironment() {
    // Concrete Substation Ground Plane
    const groundGeo = new THREE.PlaneGeometry(90, 70);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x0b101d,
      roughness: 0.8,
      metalness: 0.2
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    this.scene.add(ground);

    // Subtle Linear Grid Overlay
    const gridHelper = new THREE.GridHelper(90, 45, 0x0ea5e9, 0x1e293b);
    gridHelper.position.y = 0.01;
    this.scene.add(gridHelper);

    // Substation Steel Gantry Towers
    this.createGantryTower(-38, -26);
    this.createGantryTower(38, -26);
    this.createGantryTower(-38, 26);
    this.createGantryTower(38, 26);
  }

  createGantryTower(x, z) {
    const towerGroup = new THREE.Group();
    towerGroup.position.set(x, 0, z);

    const legMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.8, roughness: 0.3 });
    const legGeo = new THREE.CylinderGeometry(0.3, 0.4, 14, 6);

    for (let i = 0; i < 4; i++) {
      const offsetX = (i % 2 === 0 ? 1 : -1) * 1.5;
      const offsetZ = (i < 2 ? 1 : -1) * 1.5;
      const leg = new THREE.Mesh(legGeo, legMat);
      leg.position.set(offsetX, 7, offsetZ);
      leg.castShadow = true;
      towerGroup.add(leg);
    }

    const barGeo = new THREE.BoxGeometry(4.5, 0.4, 4.5);
    const bar = new THREE.Mesh(barGeo, legMat);
    bar.position.y = 14;
    towerGroup.add(bar);

    this.scene.add(towerGroup);
  }

  createTransformerModel(data) {
    const group = new THREE.Group();
    group.position.set(data.position3D.x, data.position3D.y, data.position3D.z);
    group.userData = { id: data.id, name: data.name, data };

    // 1. Concrete Base Pad
    const padMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.9 });
    const padGeo = new THREE.BoxGeometry(5.5, 0.4, 4.5);
    const pad = new THREE.Mesh(padGeo, padMat);
    pad.position.y = -1.3;
    pad.receiveShadow = true;
    group.add(pad);

    // 2. Transformer Main Tank Body
    const isCritical = data.riskLevel === 'CRITICAL';
    const isHighRisk = data.riskLevel === 'HIGH_RISK';
    const tankMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      metalness: 0.7,
      roughness: 0.3
    });
    const tankGeo = new THREE.BoxGeometry(4, 3, 3);
    const tank = new THREE.Mesh(tankGeo, tankMat);
    tank.castShadow = true;
    tank.receiveShadow = true;
    group.add(tank);

    // 3. Conservator Tank (Top Cylinder)
    const consMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.8 });
    const consGeo = new THREE.CylinderGeometry(0.5, 0.5, 3.2, 12);
    const cons = new THREE.Mesh(consGeo, consMat);
    cons.rotation.z = Math.PI / 2;
    cons.position.set(0, 2.2, -1.2);
    group.add(cons);

    // 4. High-Voltage Bushing Insulators (Phases A, B, C)
    const bushingMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.2 });
    const bushingGeo = new THREE.CylinderGeometry(0.12, 0.25, 1.8, 8);
    for (let i = -1; i <= 1; i++) {
      const bushing = new THREE.Mesh(bushingGeo, bushingMat);
      bushing.position.set(i * 1.1, 2.3, 0.4);
      group.add(bushing);
    }

    // 5. Radiator Fins
    const radMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.5 });
    const radGeo = new THREE.BoxGeometry(0.2, 2.2, 2.2);
    const radLeft = new THREE.Mesh(radGeo, radMat);
    radLeft.position.set(-2.2, 0, 0);
    const radRight = new THREE.Mesh(radGeo, radMat);
    radRight.position.set(2.2, 0, 0);
    group.add(radLeft);
    group.add(radRight);

    // 6. Visual Status Indicators (Green Normal / Yellow Warning / Red High Risk / Purple Critical)
    const statusColor = this.getStatusHexColor(data.riskLevel);
    const statusMat = new THREE.MeshBasicMaterial({ color: statusColor });

    // Status Dome Light
    const domeGeo = new THREE.SphereGeometry(0.38, 16, 16);
    const dome = new THREE.Mesh(domeGeo, statusMat);
    dome.position.set(0, 3.2, 0);
    group.add(dome);

    // Status Glow PointLight
    const statusLight = new THREE.PointLight(statusColor, isCritical ? 3.0 : isHighRisk ? 2.2 : 1.0, 10);
    statusLight.position.set(0, 3.2, 0);
    group.add(statusLight);

    // Pulsing Warning Ring for HIGH RISK / CRITICAL
    const ringGeo = new THREE.RingGeometry(2.4, 2.7, 32);
    const ringMat = new THREE.MeshBasicMaterial({
      color: statusColor,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: (isHighRisk || isCritical) ? 0.8 : 0.0
    });
    const warningRing = new THREE.Mesh(ringGeo, ringMat);
    warningRing.rotation.x = -Math.PI / 2;
    warningRing.position.y = -1.0;
    group.add(warningRing);

    // 7. Floating Text Label Plate Sprite
    const labelSprite = this.createLabelSprite(data.id, data.riskScore, data.riskLevel);
    labelSprite.position.set(0, 4.4, 0);
    group.add(labelSprite);

    // Register tank for raycasting click selection
    tank.userData = { parentGroup: group, assetId: data.id };
    this.selectableMeshes.push(tank);

    this.scene.add(group);
    this.transformersMap.set(data.id, {
      group,
      tank,
      dome,
      statusLight,
      statusMat,
      warningRing,
      ringMat,
      labelSprite,
      data
    });
  }

  createLabelSprite(text, riskScore, riskLevel) {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 80;
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = 'rgba(11, 16, 29, 0.88)';
    ctx.strokeStyle = riskLevel === 'CRITICAL' ? '#a855f7' : riskLevel === 'HIGH_RISK' ? '#ef4444' : riskLevel === 'WARNING' ? '#f59e0b' : '#10b981';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.roundRect(4, 4, 248, 72, 12);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'Bold 28px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(text, 128, 36);

    ctx.fillStyle = riskLevel === 'CRITICAL' ? '#e9d5ff' : riskLevel === 'HIGH_RISK' ? '#fca5a5' : riskLevel === 'WARNING' ? '#fcd34d' : '#6ee7b7';
    ctx.font = 'Bold 20px Inter, sans-serif';
    ctx.fillText(`${riskLevel.replace('_', ' ')} (${riskScore}%)`, 128, 62);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(4.2, 1.3, 1);
    return sprite;
  }

  getStatusHexColor(riskLevel) {
    switch (riskLevel) {
      case 'CRITICAL': return 0xa855f7;  // Purple
      case 'HIGH_RISK': return 0xef4444; // Red
      case 'WARNING': return 0xf59e0b;   // Yellow/Orange
      case 'NORMAL':
      default: return 0x10b981;          // Green
    }
  }

  connectPowerLines(fromId, toId) {
    const t1 = this.transformersMap.get(fromId);
    const t2 = this.transformersMap.get(toId);
    if (!t1 || !t2) return;

    const p1 = t1.group.position.clone().add(new THREE.Vector3(0, 2.5, 0));
    const p2 = t2.group.position.clone().add(new THREE.Vector3(0, 2.5, 0));

    // Catenary Curve Sag for transmission lines
    const midPoint = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
    midPoint.y -= 1.8;

    const curve = new THREE.QuadraticBezierCurve3(p1, midPoint, p2);
    const points = curve.getPoints(28);
    const lineGeo = new THREE.BufferGeometry().setFromPoints(points);

    const isHighRiskLine = t1.data.riskLevel === 'HIGH_RISK' || t2.data.riskLevel === 'HIGH_RISK' || t1.data.riskLevel === 'CRITICAL' || t2.data.riskLevel === 'CRITICAL';
    const lineColor = isHighRiskLine ? (t1.data.riskLevel === 'CRITICAL' || t2.data.riskLevel === 'CRITICAL' ? 0xa855f7 : 0xef4444) : 0x0ea5e9;

    const lineMat = new THREE.LineBasicMaterial({
      color: lineColor,
      linewidth: isHighRiskLine ? 3 : 2
    });

    const line = new THREE.Line(lineGeo, lineMat);
    this.scene.add(line);

    // Power-flow animated pulse particle along cable
    const particleGeo = new THREE.SphereGeometry(0.2, 8, 8);
    const particleMat = new THREE.MeshBasicMaterial({ color: lineColor });
    const particle = new THREE.Mesh(particleGeo, particleMat);
    this.scene.add(particle);

    this.powerLinesList.push({ line, lineMat, curve, particle, t1, t2 });
  }

  updateStatusFromData(transformers) {
    if (!transformers) return;

    // First load: Create 3D Models and Electrical Connections
    if (this.transformersMap.size === 0) {
      transformers.forEach(tf => this.createTransformerModel(tf));

      // Connect interconnected electrical network grid
      this.connectPowerLines('T-101', 'T-102');
      this.connectPowerLines('T-102', 'T-103');
      this.connectPowerLines('T-101', 'T-104');
      this.connectPowerLines('T-104', 'T-105');
      this.connectPowerLines('T-105', 'T-106');
      this.connectPowerLines('T-103', 'T-106');
      return;
    }

    // Dynamic AI Status Updates (Reacts to data service changes automatically)
    transformers.forEach(tf => {
      const entry = this.transformersMap.get(tf.id);
      if (entry) {
        entry.data = tf;
        const color = this.getStatusHexColor(tf.riskLevel);
        entry.statusMat.color.setHex(color);
        entry.statusLight.color.setHex(color);
        
        const isCritical = tf.riskLevel === 'CRITICAL';
        const isHighRisk = tf.riskLevel === 'HIGH_RISK';
        
        entry.ringMat.color.setHex(color);
        entry.ringMat.opacity = (isHighRisk || isCritical) ? 0.8 : 0.0;
        entry.statusLight.intensity = isCritical ? 3.0 : isHighRisk ? 2.2 : 1.0;
      }
    });

    // Update connection line colors if risk status changed
    this.powerLinesList.forEach(pl => {
      const isHighRiskLine = pl.t1.data.riskLevel === 'HIGH_RISK' || pl.t2.data.riskLevel === 'HIGH_RISK' || pl.t1.data.riskLevel === 'CRITICAL' || pl.t2.data.riskLevel === 'CRITICAL';
      const lineColor = pl.t1.data.riskLevel === 'CRITICAL' || pl.t2.data.riskLevel === 'CRITICAL' ? 0xa855f7 : isHighRiskLine ? 0xef4444 : 0x0ea5e9;
      pl.lineMat.color.setHex(lineColor);
      pl.particle.material.color.setHex(lineColor);
    });

    // Update Side Panel if active asset updated
    if (this.selectedTransformerId) {
      const selectedEntry = this.transformersMap.get(this.selectedTransformerId);
      if (selectedEntry) this.updateDiagnosticSidePanel(selectedEntry.data);
    }
  }

  initEventListeners() {
    // Window Resize Handler
    window.addEventListener('resize', () => {
      if (!this.container) return;
      const w = this.container.clientWidth;
      const h = this.container.clientHeight;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    });

    // Raycast click handler
    this.renderer.domElement.addEventListener('pointerdown', (e) => this.onPointerDown(e));

    // Reset View Buttons (Command Center & Grid View Section)
    ['btn-3d-reset-cam', 'btn-3d-reset-cam-grid'].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) btn.addEventListener('click', () => this.resetCamera());
    });

    // Focus High Risk Buttons
    ['btn-3d-focus-risk', 'btn-3d-focus-risk-grid'].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) btn.addEventListener('click', () => this.focusHighRisk());
    });
  }

  onPointerDown(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(this.selectableMeshes);

    if (intersects.length > 0) {
      const clickedMesh = intersects[0].object;
      const parentGroup = clickedMesh.userData.parentGroup;
      if (parentGroup && parentGroup.userData) {
        this.selectTransformer(parentGroup.userData.id);
      }
    }
  }

  selectTransformer(id) {
    const entry = this.transformersMap.get(id);
    if (!entry) return;

    this.selectedTransformerId = id;
    console.log(`[3D Network] Selected Transformer: ${id}`);

    // Focus camera smoothly
    const targetPos = entry.group.position.clone();
    this.animateCameraTo(targetPos.x, targetPos.y + 4, targetPos.z + 14, targetPos);

    // Update AI Diagnostic Side Panel
    this.updateDiagnosticSidePanel(entry.data);
  }

  updateDiagnosticSidePanel(data) {
    if (!data) return;

    const nameEl = document.getElementById('diag-asset-name');
    const subEl = document.getElementById('diag-asset-substation');
    const riskEl = document.getElementById('diag-risk-level');
    const badgeEl = document.getElementById('diag-panel-badge');
    const condsListEl = document.getElementById('diag-conditions-list');
    const recTextEl = document.getElementById('diag-recommendation-text');

    if (nameEl) nameEl.textContent = `TRANSFORMER ${data.id}`;
    if (subEl) subEl.textContent = data.substation;

    if (riskEl) {
      let riskColorClass = "normal-text";
      if (data.riskLevel === "CRITICAL") riskColorClass = "purple-text";
      else if (data.riskLevel === "HIGH_RISK") riskColorClass = "danger-text";
      else if (data.riskLevel === "WARNING") riskColorClass = "warning-text";

      riskEl.className = `risk-score-display ${riskColorClass}`;
      riskEl.textContent = `${data.riskLevel.replace('_', ' ')} (${data.riskScore}%)`;
    }

    if (badgeEl) {
      let badgeClass = "badge-info";
      if (data.riskLevel === "CRITICAL") badgeClass = "badge-risk";
      else if (data.riskLevel === "HIGH_RISK") badgeClass = "badge-high-risk";
      else if (data.riskLevel === "WARNING") badgeClass = "badge-count";
      badgeEl.className = `badge ${badgeClass}`;
      badgeEl.textContent = `${data.riskLevel.replace('_', ' ')} DETECTED`;
    }

    if (condsListEl) {
      if (data.anomalies && data.anomalies.length > 0) {
        condsListEl.innerHTML = data.anomalies.map(anom => `
          <li><i data-lucide="alert-triangle" class="icon-warning"></i> ${anom}</li>
        `).join('');
      } else {
        condsListEl.innerHTML = `<li><i data-lucide="check-circle-2" class="icon-teal"></i> No abnormal condition detected. Nominal operational baseline.</li>`;
      }
    }

    if (recTextEl) {
      recTextEl.textContent = data.recommendation ? `“${data.recommendation}”` : `“Continue standard continuous background GridGuard AI monitoring.”`;
    }

    if (window.lucide) window.lucide.createIcons();
  }

  focusHighRisk() {
    let highRiskOrCriticalAsset = Array.from(this.transformersMap.values())
      .find(t => t.data.riskLevel === 'HIGH_RISK' || t.data.riskLevel === 'CRITICAL');

    if (highRiskOrCriticalAsset) {
      this.selectTransformer(highRiskOrCriticalAsset.data.id);
    }
  }

  resetCamera() {
    this.animateCameraTo(this.defaultCameraPos.x, this.defaultCameraPos.y, this.defaultCameraPos.z, new THREE.Vector3(0, 0, 0));
  }

  animateCameraTo(px, py, pz, tx) {
    const startPos = this.camera.position.clone();
    const endPos = new THREE.Vector3(px, py, pz);
    const startTarget = this.controls ? this.controls.target.clone() : new THREE.Vector3();
    let progress = 0;

    const anim = () => {
      progress += 0.05;
      this.camera.position.lerpVectors(startPos, endPos, progress);
      if (this.controls) {
        this.controls.target.lerpVectors(startTarget, tx, progress);
        this.controls.update();
      }
      if (progress < 1) requestAnimationFrame(anim);
    };
    anim();
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    const time = Date.now() * 0.003;

    // 1. Animate Power-Flow pulses along high-voltage transmission lines
    this.powerLinesList.forEach((pl, idx) => {
      const progress = (time * 0.4 + idx * 0.25) % 1.0;
      const point = pl.curve.getPoint(progress);
      pl.particle.position.copy(point);
    });

    // 2. Animate High Risk (T-104) & Critical (T-106) Warning Rings & Status Light Intensity
    this.transformersMap.forEach(entry => {
      if (entry.data.riskLevel === 'HIGH_RISK') {
        const pulse = 1 + Math.sin(time * 3) * 0.12;
        entry.warningRing.scale.set(pulse, pulse, pulse);
        entry.statusLight.intensity = 2.0 + Math.sin(time * 3) * 1.0;
      } else if (entry.data.riskLevel === 'CRITICAL') {
        const pulse = 1 + Math.sin(time * 5) * 0.18;
        entry.dome.scale.set(pulse, pulse, pulse);
        entry.warningRing.scale.set(pulse * 1.1, pulse * 1.1, pulse * 1.1);
        entry.statusLight.intensity = 2.8 + Math.sin(time * 5) * 1.5;
      }
    });

    if (this.controls) this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  isWebGLAvailable() {
    try {
      const canvas = document.createElement('canvas');
      return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
    } catch (e) {
      return false;
    }
  }

  showFallbackMessage() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="webgl-fallback-box" style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:#94a3b8; text-align:center; padding:20px;">
        <i data-lucide="alert-triangle" style="width:48px; height:48px; color:#f59e0b; margin-bottom:12px;"></i>
        <h3 style="color:#f8fafc; font-size:1.1rem; margin-bottom:6px;">3D Visualization Unavailable</h3>
        <p style="font-size:0.85rem; max-width:400px;">3D visualization unavailable. Please enable WebGL or use a supported browser to view the interactive spatial transformer network.</p>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();
  }
}

window.Transformer3DNetwork = Transformer3DNetwork;
