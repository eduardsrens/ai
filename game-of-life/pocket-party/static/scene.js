import * as THREE from "./vendor/three.module.js";

const TILE_LABELS = {
  start: "Portal Gate · Start & Wrap",
  meadow: "Sunny Meadow · +3 Keys",
  payday: "Key Stash · +8 Keys",
  campfire: "Cozy Campfire · Heal +6 HP",
  chance: "Mystery Drop · Random Item",
  trap: "Bramble Trap · −4 HP",
  chest: "Trophy Shrine · 20 Keys → 1 ★",
};

const PLAYER_COLORS = [0xe06d53, 0x4c96a8, 0x7da657, 0xa47bb8];

// One small texture per tile label. A shared atlas let the mipmaps of
// neighbouring cells bleed into each other, which gave smudged labels.
const LABEL_SIZE = 256;
const LABEL_ICONS = {
  49: { text: "PORTAL", font: "800 50px Outfit, sans-serif", color: "#fff8e6" },
  50: { text: "◆", font: "700 124px sans-serif", color: "#fff8e6" },
  51: { text: "+", font: "800 148px Outfit, sans-serif", color: "#fff8e6" },
  52: { text: "★", font: "700 132px sans-serif", color: "#fff6cc" },
  53: { text: "?", font: "800 136px Outfit, sans-serif", color: "#fff9e8" },
  54: { text: "!", font: "800 144px Outfit, sans-serif", color: "#fff5ec" },
};
const labelTextureCache = new Map();

function createLabelTexture(cellIndex, maxAnisotropy) {
  if (labelTextureCache.has(cellIndex)) return labelTextureCache.get(cellIndex);
  const canvas = document.createElement("canvas");
  canvas.width = LABEL_SIZE;
  canvas.height = LABEL_SIZE;
  const c = canvas.getContext("2d");
  c.translate(LABEL_SIZE / 2, LABEL_SIZE / 2);
  c.textAlign = "center";
  c.textBaseline = "middle";
  const icon = LABEL_ICONS[cellIndex];
  if (icon) {
    c.font = icon.font;
    c.fillStyle = "rgba(0,0,0,0.18)";
    c.fillText(icon.text, 0, 10);
    c.fillStyle = icon.color;
    c.fillText(icon.text, 0, 4);
  } else {
    c.font = "700 88px Outfit, sans-serif";
    c.fillStyle = "rgba(70, 82, 58, 0.72)";
    c.fillText(String(cellIndex).padStart(2, "0"), 0, 8);
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = maxAnisotropy;
  labelTextureCache.set(cellIndex, tex);
  return tex;
}

function createPipTexture(value) {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 128;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = "#fff9ea";
  ctx.fillRect(0, 0, 128, 128);
  ctx.strokeStyle = "#dfd5b9";
  ctx.lineWidth = 8;
  ctx.strokeRect(4, 4, 120, 120);

  const pips = {
    1: [[64, 64]],
    2: [[34, 34], [94, 94]],
    3: [[34, 34], [64, 64], [94, 94]],
    4: [[34, 34], [94, 34], [34, 94], [94, 94]],
    5: [[34, 34], [94, 34], [64, 64], [34, 94], [94, 94]],
    6: [[36, 30], [92, 30], [36, 64], [92, 64], [36, 98], [92, 98]],
  }[value];

  ctx.fillStyle = value === 1 ? "#d9674e" : "#30453b";
  for (const [x, y] of pips) {
    ctx.beginPath();
    ctx.arc(x, y, value === 1 ? 15 : 11, 0, Math.PI * 2);
    ctx.fill();
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  return tex;
}

export class PartyWorld {
  constructor(container, types, { audio = null, onTileHover = null } = {}) {
    this.el = container;
    this.types = types;
    this.audio = audio;
    this.onTileHover = onTileHover;

    this.angle = 0.16;
    this.targetAngle = 0.16;
    this.angleVel = 0;
    this.zoom = 1.0;
    this.targetZoom = 1.0;
    this.preset = "diorama";
    this.time = 0;
    this.cinematic = false;
    this.skipShot = false;
    this.shotEntering = false;
    this.shotEnding = false;
    this.followId = 0;
    this.shakeTime = 0;
    this.shakeAmp = 0;
    this.activePlayer = 0;
    this.isFinished = false;
    this.confettiCooldown = 0;
    this.hoveredTile = -1;

    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.Fog(0xdff0e8, 38, 92);

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.shadowMap.autoUpdate = false;
    this.renderer.shadowMap.needsUpdate = true;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.06;
    container.appendChild(this.renderer.domElement);

    this.camera = new THREE.PerspectiveCamera(41, 1, 0.2, 180);
    this.cameraLook = new THREE.Vector3(0, 0.35, -0.6);
    this.overviewLook = new THREE.Vector3(0, 0.35, -0.6);

    this.hud = document.createElement("div");
    this.hud.className = "cinematic-hud";
    this.hud.innerHTML =
      '<div class="shot-top"><span class="shot-brand">POCKET PARTY <i>SUNLIT DIORAMA CAM</i></span><button class="shot-skip" type="button">Back to board <span>Esc</span></button></div>' +
      '<div class="shot-caption"><span class="shot-player"></span><h2></h2><p></p><span class="shot-status">THIRD-PERSON CAMERA · FOLLOWING THE ACTION</span></div>';
    container.append(this.hud);
    this.hud.querySelector("button").onclick = () => {
      this.skipShot = true;
    };
    this._onKeyDown = (e) => {
      if (this.cinematic && e.code === "Escape") {
        e.preventDefault();
        this.skipShot = true;
      }
    };
    document.addEventListener("keydown", this._onKeyDown);

    this.mats = new Map();
    this.world = new THREE.Group();
    this.scene.add(this.world);

    this.tileMeshes = [];
    this.chests = new Map();
    this.floatingProps = [];
    this.clouds = [];
    this.birds = [];
    this.smokePuffs = [];
    this.embers = [];
    this.campFlames = [];
    this.particles = [];
    this.diceMeshes = [];
    this.raycaster = new THREE.Raycaster();
    this.pointerNDC = new THREE.Vector2(-9, -9);

    this._setupLights();
    this._buildSky();
    this._buildOcean();
    this._buildIsland();
    this._buildBoard();
    this._buildVillageAndNature();
    this._makePawns();
    this._buildParticlePool();
    this._buildDicePool();
    this._setupControls();

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container);
    this.resize();
    this._animate();
  }

  mat(color, opts = {}) {
    const key = `${color}_${opts.roughness ?? 0.85}_${opts.metalness ?? 0.0}_${opts.emissive ?? 0}`;
    if (!this.mats.has(key)) {
      this.mats.set(
        key,
        new THREE.MeshStandardMaterial({
          color,
          roughness: opts.roughness ?? 0.85,
          metalness: opts.metalness ?? 0.0,
          emissive: opts.emissive ?? 0x000000,
          emissiveIntensity: opts.emissiveIntensity ?? 0,
          flatShading: opts.flatShading ?? true,
        })
      );
    }
    return this.mats.get(key);
  }

  mesh(geo, col, x, y, z, parent = this.world, opts = {}) {
    const m = new THREE.Mesh(geo, this.mat(col, opts));
    m.position.set(x, y, z);
    m.castShadow = opts.castShadow ?? true;
    m.receiveShadow = opts.receiveShadow ?? true;
    parent.add(m);
    return m;
  }

  box(x, y, z, w, h, d, c, parent = this.world, opts = {}) {
    return this.mesh(new THREE.BoxGeometry(w, h, d), c, x, y, z, parent, opts);
  }

  roundShape(w, d, r) {
    const s = new THREE.Shape();
    s.moveTo(-w / 2 + r, -d / 2);
    s.lineTo(w / 2 - r, -d / 2);
    s.quadraticCurveTo(w / 2, -d / 2, w / 2, -d / 2 + r);
    s.lineTo(w / 2, d / 2 - r);
    s.quadraticCurveTo(w / 2, d / 2, w / 2 - r, d / 2);
    s.lineTo(-w / 2 + r, d / 2);
    s.quadraticCurveTo(-w / 2, d / 2, -w / 2, d / 2 - r);
    s.lineTo(-w / 2, -d / 2 + r);
    s.quadraticCurveTo(-w / 2, -d / 2, -w / 2 + r, -d / 2);
    return s;
  }

  slab(w, d, h, r, col, y, parent = this.world) {
    const geo = new THREE.ExtrudeGeometry(this.roundShape(w, d, r), {
      depth: h,
      bevelEnabled: true,
      bevelSegments: 2,
      steps: 1,
      bevelSize: 0.16,
      bevelThickness: 0.12,
      curveSegments: 6,
    });
    geo.rotateX(-Math.PI / 2);
    return this.mesh(geo, col, 0, y, 0, parent);
  }

  _setupLights() {
    this.scene.add(new THREE.HemisphereLight(0xd9f2ff, 0x73935a, 1.25));

    const sun = new THREE.DirectionalLight(0xfff4d6, 2.25);
    sun.position.set(-16, 26, 14);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    Object.assign(sun.shadow.camera, {
      left: -17,
      right: 17,
      top: 17,
      bottom: -17,
      near: 2,
      far: 62,
    });
    sun.shadow.normalBias = 0.04;
    sun.shadow.bias = -0.0002;
    this.scene.add(sun);

    const rim = new THREE.DirectionalLight(0xaee5ef, 0.65);
    rim.position.set(16, 11, -14);
    this.scene.add(rim);

    this.campLight = new THREE.PointLight(0xff9b42, 1.4, 6.5, 1.8);
    this.campLight.position.set(-8.3, 1.2, 1.8);
    this.scene.add(this.campLight);
  }

  _buildSky() {
    const skyGeo = new THREE.SphereGeometry(92, 24, 16);
    const skyMat = new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      fog: false,
      uniforms: {
        uSunDir: { value: new THREE.Vector3(-16, 26, 14).normalize() },
      },
      vertexShader: `
        varying vec3 vDir;
        void main() {
          vDir = normalize(position);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 uSunDir;
        varying vec3 vDir;
        void main() {
          float h = clamp(vDir.y * 0.5 + 0.5, 0.0, 1.0);
          vec3 zenith = vec3(0.47, 0.78, 0.92);
          vec3 mid = vec3(0.80, 0.92, 0.93);
          vec3 horizon = vec3(0.98, 0.94, 0.85);
          vec3 col = mix(horizon, mid, smoothstep(0.42, 0.66, h));
          col = mix(col, zenith, smoothstep(0.62, 0.95, h));
          float sunAmt = max(dot(normalize(vDir), uSunDir), 0.0);
          col += vec3(1.0, 0.93, 0.74) * pow(sunAmt, 14.0) * 0.45;
          col += vec3(1.0, 0.98, 0.90) * smoothstep(0.996, 0.999, sunAmt) * 0.7;
          gl_FragColor = vec4(col, 1.0);
        }
      `,
    });
    this.scene.add(new THREE.Mesh(skyGeo, skyMat));

    // Drifting low-poly clouds
    const cloudMat = new THREE.MeshStandardMaterial({
      color: 0xfffcf5,
      roughness: 0.95,
      flatShading: true,
    });
    const puffGeo = new THREE.IcosahedronGeometry(1, 1);
    const placements = [
      [-18, 9.5, -14, 1.15, 0.25],
      [15, 10.5, -16, 1.35, -0.2],
      [-22, 8.8, 10, 1.0, 0.18],
      [20, 9.2, 11, 1.1, -0.15],
      [2, 11.4, -22, 1.4, 0.14],
      [-5, 10.0, 21, 0.95, 0.22],
    ];
    for (const [x, y, z, s, speed] of placements) {
      const g = new THREE.Group();
      g.position.set(x, y, z);
      g.scale.setScalar(s);
      for (const [px, py, pz, ps] of [
        [0, 0, 0, 1.0],
        [-0.95, -0.15, 0.15, 0.75],
        [1.0, -0.18, -0.1, 0.78],
        [0.25, 0.35, 0.1, 0.68],
      ]) {
        const m = new THREE.Mesh(puffGeo, cloudMat);
        m.position.set(px, py, pz);
        m.scale.set(ps * 1.25, ps * 0.68, ps * 0.9);
        g.add(m);
      }
      this.scene.add(g);
      this.clouds.push({ g, baseX: x, baseY: y, speed, phase: x * 0.4 });
    }

    // Circling stylized seabirds
    const birdMat = this.mat(0xfaf7eb, { roughness: 0.7 });
    const wingGeo = new THREE.BoxGeometry(0.32, 0.03, 0.12);
    for (let i = 0; i < 4; i++) {
      const bird = new THREE.Group();
      const lw = new THREE.Mesh(wingGeo, birdMat);
      lw.position.x = -0.14;
      const rw = new THREE.Mesh(wingGeo, birdMat);
      rw.position.x = 0.14;
      bird.add(lw, rw);
      this.scene.add(bird);
      this.birds.push({ bird, lw, rw, angle: (i * Math.PI) / 2, radius: 9.5 + i * 1.6, y: 5.5 + (i % 2) * 0.9 });
    }
  }

  _buildOcean() {
    const geo = new THREE.PlaneGeometry(180, 180, 28, 28);
    geo.rotateX(-Math.PI / 2);
    this.oceanMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uSunDir: { value: new THREE.Vector3(-16, 26, 14).normalize() },
      },
      vertexShader: `
        uniform float uTime;
        varying vec3 vWorldPos;
        varying float vWave;
        void main() {
          vec3 p = position;
          float w = sin(p.x * 0.38 + uTime * 1.35) * 0.065 + cos(p.z * 0.45 - uTime * 1.1) * 0.055;
          p.y += w;
          vWave = w;
          vec4 wp = modelMatrix * vec4(p, 1.0);
          vWorldPos = wp.xyz;
          gl_Position = projectionMatrix * viewMatrix * wp;
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform vec3 uSunDir;
        varying vec3 vWorldPos;
        varying float vWave;

        float sdRoundedBox(vec2 p, vec2 b, float r) {
          vec2 q = abs(p) - b + r;
          return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
        }

        void main() {
          float dist = sdRoundedBox(vWorldPos.xz, vec2(13.4, 9.6), 3.3);
          float shallow = 1.0 - smoothstep(0.0, 4.8, dist);
          float mid = 1.0 - smoothstep(2.0, 15.0, dist);

          vec3 deepCol = vec3(0.17, 0.50, 0.65);
          vec3 tealCol = vec3(0.28, 0.72, 0.74);
          vec3 lagoonCol = vec3(0.55, 0.88, 0.84);
          vec3 col = mix(deepCol, tealCol, mid);
          col = mix(col, lagoonCol, shallow * 0.85);

          // Animated shoreline foam bands hugging the island beach
          float ripple = sin(dist * 5.2 - uTime * 2.2) * 0.5 + 0.5;
          float foam1 = smoothstep(0.6, 0.0, abs(dist - 0.35 - sin(uTime * 1.6 + vWorldPos.x * 0.5) * 0.16));
          float foam2 = smoothstep(0.32, 0.0, abs(dist - 1.35)) * ripple * 0.65;
          col = mix(col, vec3(0.95, 0.99, 0.98), clamp(foam1 * 0.75 + foam2, 0.0, 0.88));

          // Sunlit water shimmer
          vec3 n = normalize(vec3(
            cos(vWorldPos.x * 0.7 + uTime * 1.7) * 0.14,
            1.0,
            sin(vWorldPos.z * 0.65 - uTime * 1.4) * 0.14
          ));
          vec3 viewDir = normalize(cameraPosition - vWorldPos);
          vec3 halfDir = normalize(uSunDir + viewDir);
          float spec = pow(max(dot(n, halfDir), 0.0), 48.0);
          col += vec3(1.0, 0.96, 0.84) * spec * 0.42;
          col += vWave * 0.28;

          // Blend smoothly into atmospheric horizon
          float fogFactor = smoothstep(32.0, 86.0, length(vWorldPos.xz));
          col = mix(col, vec3(0.87, 0.94, 0.91), fogFactor);

          gl_FragColor = vec4(col, 1.0);
        }
      `,
    });
    const ocean = new THREE.Mesh(geo, this.oceanMat);
    ocean.position.y = -0.3;
    this.scene.add(ocean);
  }

  _buildIsland() {
    // Under-cliff, sandy beach, and lush meadow plateau (meadow flat top = -0.02 + 0.14 + 0.12 = +0.24)
    this.slab(26.8, 19.2, 0.44, 3.4, 0x9b846b, -0.68);
    this.slab(26.2, 18.6, 0.26, 3.2, 0xeee0b6, -0.24);
    this.slab(25.2, 17.6, 0.14, 3.0, 0x8db86c, -0.02);

    // Sculpted rolling northern hills
    // [x, z, radius x, radius z, height]. The hills stay between the trail
    // and the island edge. Larger hills covered tiles and hung over the beach.
    const hillSpecs = [
      [-5.0, -7.6, 2.0, 0.95, 0.9, 0x80ab60],
      [-1.6, -7.7, 2.4, 1.0, 1.15, 0x8bb669],
      [2.0, -7.6, 1.8, 0.9, 0.8, 0x7ba45c],
      [4.9, -7.5, 1.3, 0.8, 0.6, 0x7da75d],
      [-11.7, -0.2, 0.8, 1.3, 0.55, 0x86b064],
    ];
    const hillGeo = new THREE.IcosahedronGeometry(1, 1);
    this.hills = [];
    for (const [x, z, rx, rz, h, c] of hillSpecs) {
      const m = this.mesh(hillGeo, c, x, 0.2, z);
      m.scale.set(rx, h, rz);
      this.hills.push({ x, z, rx, rz });
    }

    // Instanced coastal boulders & beach rocks (1 draw call)
    const coastRocks = [
      [-12.6, -6.2, 0.65, 1.0], [-13.1, 2.2, 0.72, 0.85], [-10.5, 8.9, 0.62, 1.1],
      [-3.4, 9.3, 0.54, 0.9], [4.6, 9.2, 0.68, 0.95], [11.8, 7.6, 0.76, 1.1],
      [13.1, 0.4, 0.64, 0.9], [12.5, -5.8, 0.7, 1.05], [9.4, -8.8, 0.66, 0.95],
      [-0.5, -9.2, 0.6, 0.85], [-8.4, -9.1, 0.72, 1.0], [12.8, 4.1, 0.46, 0.8],
    ];
    const rockGeo = new THREE.DodecahedronGeometry(0.85, 0);
    const rockInst = new THREE.InstancedMesh(rockGeo, this.mat(0x9a9688), coastRocks.length);
    rockInst.castShadow = true;
    rockInst.receiveShadow = true;
    const dummyRock = new THREE.Object3D();
    coastRocks.forEach(([x, z, s, squash], i) => {
      dummyRock.position.set(x, -0.08 + s * 0.12, z);
      dummyRock.scale.set(s * 1.25, s * 0.68 * squash, s);
      dummyRock.rotation.set(i * 0.3, i * 1.1, i * 0.2);
      dummyRock.updateMatrix();
      rockInst.setMatrixAt(i, dummyRock.matrix);
    });
    rockInst.instanceMatrix.needsUpdate = true;
    this.world.add(rockInst);

    // Crystal village lake tucked cleanly in the east pocket (center 7.35, -1.25)
    const lakeX = 7.35;
    const lakeZ = -1.25;
    const rimGeo = new THREE.CircleGeometry(1.82, 24);
    rimGeo.rotateX(-Math.PI / 2);
    const lakeRim = new THREE.Mesh(rimGeo, this.mat(0xe6dab3, { roughness: 0.92 }));
    lakeRim.scale.set(1.12, 1, 0.85);
    lakeRim.position.set(lakeX, 0.252, lakeZ);
    lakeRim.receiveShadow = true;
    this.world.add(lakeRim);

    const lakeGeo = new THREE.CircleGeometry(1.64, 24);
    lakeGeo.rotateX(-Math.PI / 2);
    this.lakeMat = new THREE.ShaderMaterial({
      uniforms: { uTime: { value: 0 } },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        varying vec2 vUv;
        void main() {
          vec2 p = vUv - 0.5;
          float r = length(p);
          float ring = sin(r * 30.0 - uTime * 2.8) * 0.5 + 0.5;
          vec3 col = mix(vec3(0.28, 0.71, 0.76), vec3(0.62, 0.90, 0.87), smoothstep(0.12, 0.48, r));
          col += vec3(0.14) * ring * smoothstep(0.5, 0.0, r);
          gl_FragColor = vec4(col, 1.0);
        }
      `,
    });
    const lake = new THREE.Mesh(lakeGeo, this.lakeMat);
    lake.scale.set(1.12, 1, 0.85);
    lake.position.set(lakeX, 0.268, lakeZ);
    this.world.add(lake);

    // Cute floating lily pads & lotus flower
    const padGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.025, 7);
    const padMat = this.mat(0x649a56);
    for (const [lx, lz, ls] of [
      [lakeX - 0.65, lakeZ + 0.45, 1.0],
      [lakeX - 0.32, lakeZ + 0.68, 0.78],
      [lakeX + 0.95, lakeZ - 0.42, 0.92],
    ]) {
      const pad = new THREE.Mesh(padGeo, padMat);
      pad.scale.setScalar(ls);
      pad.position.set(lx, 0.28, lz);
      this.world.add(pad);
    }
    this.mesh(new THREE.OctahedronGeometry(0.08, 0), 0xf6a9b6, lakeX - 0.65, 0.33, lakeZ + 0.45);

    // Waterfall bluff cascading into north edge of the lake
    this.waterfallMat = new THREE.ShaderMaterial({
      uniforms: { uTime: { value: 0 } },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        varying vec2 vUv;
        void main() {
          float flow = fract(vUv.y * 2.2 + uTime * 1.45);
          float streak = smoothstep(0.32, 0.68, sin(vUv.x * 16.0) * 0.5 + 0.5) * smoothstep(0.18, 0.85, flow);
          vec3 base = mix(vec3(0.45, 0.83, 0.87), vec3(0.94, 0.99, 0.99), streak * 0.7);
          gl_FragColor = vec4(base, 1.0);
        }
      `,
    });
    const cliffRock = this.mesh(new THREE.DodecahedronGeometry(0.76, 0), 0x8f8a7a, lakeX, 0.62, lakeZ - 1.42);
    cliffRock.scale.set(1.28, 0.88, 0.82);
    const fall = new THREE.Mesh(new THREE.PlaneGeometry(0.56, 1.02), this.waterfallMat);
    fall.position.set(lakeX, 0.66, lakeZ - 0.84);
    fall.rotation.x = -0.34;
    this.world.add(fall);
    this.splashRing = new THREE.Mesh(
      new THREE.RingGeometry(0.22, 0.36, 16),
      new THREE.MeshBasicMaterial({ color: 0xf4ffff, transparent: true, opacity: 0.78, side: THREE.DoubleSide })
    );
    this.splashRing.rotation.x = -Math.PI / 2;
    this.splashRing.position.set(lakeX, 0.278, lakeZ - 0.68);
    this.world.add(this.splashRing);

    // Wooden dock on west bank + bobbing sailboat on the lake
    const dockX = 5.95;
    this.box(dockX, 0.35, lakeZ, 0.95, 0.08, 0.48, 0xa8825b);
    for (const dx of [dockX - 0.36, dockX + 0.36]) {
      for (const dz of [lakeZ - 0.18, lakeZ + 0.18]) {
        this.box(dx, 0.27, dz, 0.08, 0.26, 0.08, 0x7b5c3d);
      }
    }
    this.boat = new THREE.Group();
    this.boat.position.set(lakeX + 0.22, 0.3, lakeZ + 0.14);
    this.boat.scale.setScalar(0.84);
    this.box(0, 0.06, 0, 0.42, 0.14, 0.85, 0xb87353, this.boat);
    this.box(0, 0.45, 0, 0.045, 0.75, 0.045, 0x785b3f, this.boat);
    const sail = this.mesh(new THREE.ConeGeometry(0.32, 0.58, 3), 0xfff9ea, 0.05, 0.52, 0.04, this.boat);
    sail.scale.set(0.2, 1, 1.1);
    this.world.add(this.boat);

    // Northeast bluff Lighthouse with rotating beacon beam (clear of all track tiles)
    const lhX = 7.9;
    const lhZ = -6.4;
    const lhPlinth = this.mesh(new THREE.DodecahedronGeometry(0.85, 0), 0x8d897b, lhX, 0.32, lhZ);
    lhPlinth.scale.set(1.25, 0.52, 1.1);
    this.mesh(new THREE.CylinderGeometry(0.3, 0.48, 0.9, 8), 0xf6efdc, lhX, 0.72, lhZ);
    this.mesh(new THREE.CylinderGeometry(0.27, 0.3, 0.55, 8), 0xd8795b, lhX, 1.42, lhZ);
    this.mesh(new THREE.CylinderGeometry(0.25, 0.27, 0.45, 8), 0xf6efdc, lhX, 1.89, lhZ);
    this.mesh(new THREE.CylinderGeometry(0.36, 0.36, 0.36, 8), 0xffe49c, lhX, 2.27, lhZ, this.world, {
      emissive: 0xffd268,
      emissiveIntensity: 0.75,
    });
    this.mesh(new THREE.ConeGeometry(0.55, 0.48, 8), 0xc9694f, lhX, 2.65, lhZ);
    this.lighthouseBeam = new THREE.Group();
    this.lighthouseBeam.position.set(lhX, 2.27, lhZ);
    const beamGeo = new THREE.ConeGeometry(0.95, 5.2, 12, 1, true);
    beamGeo.translate(0, -2.6, 0);
    beamGeo.rotateX(Math.PI / 2);
    // Additive glow: a normal transparent cone washed out the trees behind it.
    const beamMat = new THREE.MeshBasicMaterial({
      color: 0xffe89e,
      transparent: true,
      opacity: 0.07,
      side: THREE.DoubleSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      fog: false,
    });
    this.lighthouseBeam.add(new THREE.Mesh(beamGeo, beamMat));
    this.world.add(this.lighthouseBeam);
  }

  _buildBoard() {
    this.path = new THREE.CatmullRomCurve3(
      [
        [-10, 0, 5.4],
        [-5, 0, 6.4],
        [1, 0, 6.4],
        [7.7, 0, 5.5],
        [10.2, 0, 2.4],
        [9.5, 0, -2.5],
        [6, 0, -5.3],
        [0, 0, -5.6],
        [-6.6, 0, -5],
        [-10, 0, -2],
        [-8.3, 0, 1.4],
        [-4, 0, 2.6],
        [1.4, 0, 2.5],
        [5.3, 0, 0.8],
        [4, 0, -1.8],
        [0.3, 0, -1.9],
        [-2.7, 0, -0.6],
      ].map((p) => new THREE.Vector3(...p)),
      false,
      "catmullrom",
      0.35
    );

    // Continuous cobblestone roadbed visible above grass plateau under the tiles
    const roadGeo = new THREE.TubeGeometry(this.path, 160, 0.7, 6, false);
    const road = this.mesh(roadGeo, 0xd8ceb2, 0, 0.23, 0);
    road.scale.y = 0.085;
    road.castShadow = false;

    this.points = this.path.getSpacedPoints(48);
    const tileGeo = new THREE.ExtrudeGeometry(this.roundShape(1.02, 1.28, 0.14), {
      depth: 0.16,
      bevelEnabled: true,
      bevelSegments: 2,
      steps: 1,
      bevelSize: 0.045,
      bevelThickness: 0.04,
      curveSegments: 4,
    });
    tileGeo.rotateX(-Math.PI / 2);

    const tileColors = {
      start: 0xd97d60,
      meadow: 0xf4ebd3,
      payday: 0x74a36e,
      campfire: 0xdf9876,
      chest: 0x5f9da8,
      trap: 0xd9735d,
      chance: 0xe6b553,
    };
    const iconCellMap = {
      start: 49,
      payday: 50,
      campfire: 51,
      chest: 52,
      chance: 53,
      trap: 54,
    };

    const maxAniso = this.renderer.capabilities.getMaxAnisotropy();
    const labelGeo = new THREE.PlaneGeometry(0.84, 0.84);
    const labelMats = new Map();
    const labelMat = (cell) => {
      if (!labelMats.has(cell)) {
        labelMats.set(
          cell,
          new THREE.MeshBasicMaterial({
            map: createLabelTexture(cell, maxAniso),
            transparent: true,
            depthWrite: false,
            // Keep the label in front of the tile top at all camera distances.
            polygonOffset: true,
            polygonOffsetFactor: -2,
            polygonOffsetUnits: -2,
          })
        );
      }
      return labelMats.get(cell);
    };

    const keyGeo = new THREE.CylinderGeometry(0.11, 0.11, 0.04, 8);
    const keyMat = this.mat(0xf5c84c, { roughness: 0.35, metalness: 0.45, emissive: 0x7a5108, emissiveIntensity: 0.25 });
    const giftGeo = new THREE.BoxGeometry(0.24, 0.24, 0.24);
    const giftMat = this.mat(0xf5bf52, { roughness: 0.4, emissive: 0x5c3c05, emissiveIntensity: 0.18 });
    const starGeo = new THREE.OctahedronGeometry(0.18, 0);
    const starMat = this.mat(0xffda6b, { roughness: 0.28, metalness: 0.4, emissive: 0x996510, emissiveIntensity: 0.35 });

    for (let i = 0; i < this.points.length; i++) {
      const p = this.points[i];
      const t = this.path.getTangentAt(i / 48);
      const kind = this.types[i];
      const tile = this.mesh(tileGeo, tileColors[kind] || tileColors.meadow, p.x, 0.26, p.z);
      tile.rotation.y = Math.atan2(t.x, t.z);
      tile.userData.tileIndex = i;
      this.tileMeshes.push(tile);

      const cell = iconCellMap[kind] ?? i;
      const lbl = new THREE.Mesh(labelGeo, labelMat(cell));
      // Keep tile numbers and icons upright toward the primary diorama viewer
      lbl.rotation.set(-Math.PI / 2, 0, 0);
      lbl.position.set(p.x, 0.468, p.z);
      this.world.add(lbl);

      // Subtle animated 3D tokens above special tiles
      if (kind === "payday") {
        const token = new THREE.Mesh(keyGeo, keyMat);
        token.rotation.x = Math.PI / 2;
        token.position.set(p.x, 0.82, p.z);
        this.world.add(token);
        this.floatingProps.push({ mesh: token, baseY: 0.82, phase: i * 0.7, spin: 1.5 });
      } else if (kind === "chance") {
        const gift = new THREE.Mesh(giftGeo, giftMat);
        gift.position.set(p.x, 0.85, p.z);
        this.world.add(gift);
        this.floatingProps.push({ mesh: gift, baseY: 0.85, phase: i * 0.9, spin: 1.2 });
      }
    }

    // Glowing Arcane Portal Archways behind Space 0 & End Marker at Space 48
    this._buildPortalArch(this.points[0], this.path.getTangentAt(0));
    const endP = this.points[48];
    this.flag(endP.x - 0.65, endP.z - 0.3, 0xf2d179);

    // Ornate Treasure Chests at Trophy Shrines (7, 21, 35)
    for (const index of [7, 21, 35]) {
      const p = this.points[index];
      const t = this.path.getTangentAt(index / 48);
      const nx = t.z;
      const nz = -t.x;
      const cx = p.x + nx * 1.05;
      const cz = p.z + nz * 1.05;
      const chestGroup = new THREE.Group();
      chestGroup.position.set(cx, 0.24, cz);
      chestGroup.rotation.y = Math.atan2(-nx, -nz);

      this.box(0, 0.08, 0, 0.92, 0.16, 0.76, 0x9aa9a0, chestGroup);
      this.box(0, 0.34, 0, 0.7, 0.38, 0.5, 0xa8763e, chestGroup);
      for (const ox of [-0.24, 0.24]) {
        this.box(ox, 0.35, 0, 0.08, 0.4, 0.53, 0xf3cc69, chestGroup, { roughness: 0.35, metalness: 0.4 });
      }
      this.box(0, 0.38, 0.27, 0.14, 0.16, 0.05, 0xffe48f, chestGroup, { roughness: 0.35, metalness: 0.4 });

      const lidPivot = new THREE.Group();
      lidPivot.position.set(0, 0.53, -0.25);
      this.box(0, 0.07, 0.25, 0.74, 0.14, 0.54, 0xd8a84e, lidPivot, { roughness: 0.4, metalness: 0.25 });
      chestGroup.add(lidPivot);

      const crown = new THREE.Mesh(starGeo, starMat);
      crown.position.set(0, 1.08, 0);
      chestGroup.add(crown);
      this.floatingProps.push({ mesh: crown, baseY: 1.08, phase: index, spin: 1.7 });

      this.world.add(chestGroup);
      this.chests.set(index, { group: chestGroup, lid: lidPivot, crown });
    }

    // Hover & Active tile highlight rings
    this.hoverRing = new THREE.Mesh(
      new THREE.RingGeometry(0.54, 0.67, 24),
      new THREE.MeshBasicMaterial({ color: 0xffe885, transparent: true, opacity: 0.9, side: THREE.DoubleSide })
    );
    this.hoverRing.rotation.x = -Math.PI / 2;
    this.hoverRing.position.y = 0.475;
    this.hoverRing.visible = false;
    this.world.add(this.hoverRing);

    // Center island emblem plaque
    const emblem = new THREE.Mesh(
      new THREE.CylinderGeometry(1.15, 1.25, 0.14, 12),
      this.mat(0xe7dec0)
    );
    emblem.position.set(-0.3, 0.29, 0.55);
    this.world.add(emblem);
    const sundial = new THREE.Mesh(
      new THREE.OctahedronGeometry(0.32, 0),
      this.mat(0xf0c259, { roughness: 0.3, metalness: 0.4 })
    );
    sundial.position.set(-0.3, 0.74, 0.55);
    this.world.add(sundial);
    this.floatingProps.push({ mesh: sundial, baseY: 0.74, phase: 0.4, spin: 0.9 });
  }

  _buildPortalArch(p, tangent) {
    const arch = new THREE.Group();
    arch.position.set(p.x - tangent.x * 0.45, 0.42, p.z - tangent.z * 0.45);
    arch.rotation.y = Math.atan2(tangent.x, tangent.z);

    this.box(-0.78, 0.62, 0, 0.22, 1.24, 0.24, 0x8f9d95, arch);
    this.box(0.78, 0.62, 0, 0.22, 1.24, 0.24, 0x8f9d95, arch);
    this.box(0, 1.28, 0, 1.82, 0.22, 0.28, 0xa2b0a6, arch);

    this.portalMat = new THREE.ShaderMaterial({
      transparent: true,
      side: THREE.DoubleSide,
      depthWrite: false,
      uniforms: { uTime: { value: 0 } },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        varying vec2 vUv;
        void main() {
          vec2 uv = (vUv - 0.5) * 2.0;
          float r = length(uv);
          float a = atan(uv.y, uv.x);
          float swirl = sin(a * 3.0 + r * 8.0 - uTime * 3.4) * 0.5 + 0.5;
          float ring = smoothstep(1.0, 0.68, r) * smoothstep(0.06, 0.34, r);
          vec3 col = mix(vec3(0.35, 0.88, 0.84), vec3(1.0, 0.82, 0.42), swirl);
          float alpha = ring * (0.48 + 0.45 * swirl);
          gl_FragColor = vec4(col, alpha);
        }
      `,
    });
    const disc = new THREE.Mesh(new THREE.CircleGeometry(0.64, 24), this.portalMat);
    disc.position.set(0, 0.66, 0);
    arch.add(disc);
    this.world.add(arch);
  }

  _buildVillageAndNature() {
    // Cozy storybook cottages with glowing amber windows and chimney smoke
    const cottages = [
      [-5.9, -1.3, 1.05, -0.18, 0xf6ebd2],
      [-3.3, -2.5, 0.78, 0.22, 0xf2e7ce],
      [-0.7, -3.6, 0.68, -0.14, 0xf4ead4],
      [6.1, 3.6, 0.7, -0.45, 0xf5ebd5],
      [-9.0, 3.3, 0.68, 0.32, 0xf3e8ce],
    ];
    for (const [x, z, s, rot, col] of cottages) {
      const g = new THREE.Group();
      g.position.set(x, 0.24, z);
      g.rotation.y = rot;
      g.scale.setScalar(s);
      this.box(0, 0.65, 0, 1.4, 1.3, 1.2, col, g);
      const roof = this.mesh(new THREE.ConeGeometry(1.24, 0.9, 4), 0xc96e52, 0, 1.65, 0, g);
      roof.rotation.y = Math.PI / 4;
      roof.scale.z = 0.92;
      this.box(0.42, 1.85, -0.2, 0.22, 0.68, 0.22, 0xcab08c, g);
      this.box(0, 0.4, 0.61, 0.32, 0.8, 0.04, 0x728a72, g);
      for (const xx of [-0.43, 0.43]) {
        this.box(xx, 0.8, 0.61, 0.28, 0.33, 0.03, 0xffd782, g, {
          emissive: 0xffb347,
          emissiveIntensity: 0.45,
        });
      }
      this.box(0, 0.05, 0.88, 0.72, 0.09, 0.5, 0xd8ceb2, g);
      this.world.add(g);

      const smoke = this.mesh(new THREE.IcosahedronGeometry(0.14, 0), 0xf9f7ef, x + 0.4 * s, 0.24 + 2.25 * s, z - 0.18 * s, this.world, {
        castShadow: false,
      });
      this.smokePuffs.push({ mesh: smoke, x: x + 0.4 * s, y: 0.24 + 2.22 * s, z: z - 0.18 * s, phase: x + z });
    }

    // White picket fence
    for (let i = 0; i < 8; i++) {
      this.box(-7.35 + i * 0.38, 0.54, -2.8, 0.07, 0.6, 0.07, 0xf9f3e2);
      if (i < 7) this.box(-7.16 + i * 0.38, 0.58, -2.8, 0.38, 0.07, 0.05, 0xf9f3e2);
    }

    // Cozy stone-ringed campfires near campfire tiles (11, 26, 41)
    const pebbleGeo = new THREE.DodecahedronGeometry(0.085, 0);
    for (const idx of [11, 26, 41]) {
      const p = this.points[idx];
      const t = this.path.getTangentAt(idx / 48);
      const fx = p.x - t.z * 0.95;
      const fz = p.z + t.x * 0.95;
      for (let k = 0; k < 6; k++) {
        const a = (k / 6) * Math.PI * 2;
        this.mesh(pebbleGeo, 0x8f958a, fx + Math.cos(a) * 0.3, 0.26, fz + Math.sin(a) * 0.3);
      }
      const log1 = this.box(fx, 0.29, fz, 0.48, 0.09, 0.11, 0x7a5738);
      log1.rotation.y = 0.6;
      const log2 = this.box(fx, 0.29, fz, 0.48, 0.09, 0.11, 0x7a5738);
      log2.rotation.y = -0.6;
      const flame = this.mesh(new THREE.ConeGeometry(0.17, 0.42, 5), 0xff9a3c, fx, 0.48, fz, this.world, {
        emissive: 0xff6b1a,
        emissiveIntensity: 0.9,
        castShadow: false,
      });
      this.campFlames.push({ mesh: flame, phase: idx });
    }

    // Instanced Pine & Blossom Trees (zero overlap with tiles or lake)
    const pines = [
      [-10.2, -4.1, 1.05], [-9.0, -5.7, 1.2], [-7.8, -6.7, 0.9], [-6.0, -6.9, 1.15],
      [-4.0, -7.5, 0.95], [3.0, -6.9, 0.95], [5.1, -6.7, 1.1], [9.6, -5.4, 0.95],
      [10.8, -4.2, 0.9], [11.5, 1.2, 0.85], [10.8, 4.0, 0.68], [8.0, 6.9, 0.72],
      [-11.0, 2.6, 0.74], [-7.4, 7.2, 0.72], [-6.0, 4.4, 0.68], [-1.8, 4.5, 0.58],
      [3.6, 4.5, 0.68], [2.0, -0.1, 0.74], [-7.0, -2.5, 0.85], [10.6, 0.2, 0.72],
    ];
    // Move each tree off the trail and out of the hills, so no crown covers
    // a tile or its label and no tree sticks out of a hill.
    const clearOfTrack = (list, crownRadius) => {
      for (const tree of list) {
        const r = crownRadius * tree[2];
        for (let pass = 0; pass < 8; pass++) {
          let moved = false;
          for (const p of this.points) {
            const need = 0.95 + r;
            const dx = tree[0] - p.x;
            const dz = tree[1] - p.z;
            const d = Math.hypot(dx, dz) || 0.001;
            if (d < need) {
              tree[0] = p.x + (dx / d) * need;
              tree[1] = p.z + (dz / d) * need;
              moved = true;
            }
          }
          for (const h of this.hills) {
            const ex = (tree[0] - h.x) / (h.rx + r);
            const ez = (tree[1] - h.z) / (h.rz + r);
            const e = Math.hypot(ex, ez);
            if (e < 1) {
              const k = 1 / Math.max(e, 0.001);
              tree[0] = h.x + (tree[0] - h.x) * k;
              tree[1] = h.z + (tree[1] - h.z) * k;
              moved = true;
            }
          }
          // Keep the tree on the meadow.
          tree[0] = THREE.MathUtils.clamp(tree[0], -11.8 + r, 11.8 - r);
          tree[1] = THREE.MathUtils.clamp(tree[1], -8.1 + r, 8.1 - r);
          if (!moved) break;
        }
      }
    };
    clearOfTrack(pines, 0.76);

    const trunkGeo = new THREE.CylinderGeometry(0.08, 0.11, 0.85, 6);
    const trunkInst = new THREE.InstancedMesh(trunkGeo, this.mat(0x876c4b), pines.length + 8);
    trunkInst.castShadow = true;
    const coneLowGeo = new THREE.ConeGeometry(0.76, 1.25, 6);
    const coneTopGeo = new THREE.ConeGeometry(0.58, 1.35, 6);
    const pineLowInst = new THREE.InstancedMesh(coneLowGeo, this.mat(0x6d935c), pines.length);
    const pineTopInst = new THREE.InstancedMesh(coneTopGeo, this.mat(0x5c804c), pines.length);
    pineLowInst.castShadow = true;
    pineTopInst.castShadow = true;

    const dummy = new THREE.Object3D();
    pines.forEach(([x, z, s], i) => {
      dummy.position.set(x, 0.22 + 0.42 * s, z);
      dummy.scale.setScalar(s);
      dummy.rotation.y = i * 0.7;
      dummy.updateMatrix();
      trunkInst.setMatrixAt(i, dummy.matrix);

      dummy.position.set(x, 0.22 + 0.95 * s, z);
      dummy.updateMatrix();
      pineLowInst.setMatrixAt(i, dummy.matrix);

      dummy.position.set(x, 0.22 + 1.48 * s, z);
      dummy.updateMatrix();
      pineTopInst.setMatrixAt(i, dummy.matrix);
    });

    const roundTrees = [
      [-7.5, -1.0, 1.0, 0x8dad69], [-3.5, -3.9, 0.82, 0xf2b5aa], [0.6, -3.6, 0.85, 0x93b26e],
      [5.5, -3.2, 0.82, 0xf3c0b4], [8.0, 2.0, 0.85, 0x89aa65], [-10.9, -0.3, 0.72, 0xf4bbb0],
      [-4.0, 4.5, 0.74, 0x91b06c], [0.0, 4.4, 0.68, 0xf3c2b6],
    ];
    clearOfTrack(roundTrees, 0.84);
    const crownGeo = new THREE.IcosahedronGeometry(0.84, 0);
    const crownMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.88, flatShading: true });
    const roundInst = new THREE.InstancedMesh(crownGeo, crownMat, roundTrees.length);
    roundInst.castShadow = true;
    const tmpColor = new THREE.Color();
    roundTrees.forEach(([x, z, s, hex], i) => {
      dummy.position.set(x, 0.22 + 0.42 * s, z);
      dummy.scale.setScalar(s);
      dummy.rotation.y = i * 1.1;
      dummy.updateMatrix();
      trunkInst.setMatrixAt(pines.length + i, dummy.matrix);

      dummy.position.set(x, 0.22 + 1.25 * s, z);
      dummy.updateMatrix();
      roundInst.setMatrixAt(i, dummy.matrix);
      roundInst.setColorAt(i, tmpColor.setHex(hex));
    });
    trunkInst.instanceMatrix.needsUpdate = true;
    pineLowInst.instanceMatrix.needsUpdate = true;
    pineTopInst.instanceMatrix.needsUpdate = true;
    roundInst.instanceMatrix.needsUpdate = true;
    if (roundInst.instanceColor) roundInst.instanceColor.needsUpdate = true;
    this.world.add(trunkInst, pineLowInst, pineTopInst, roundInst);

    // Instanced Wildflowers & Shrubs (sits cleanly on meadow y=0.24 avoiding lake & board)
    let seed = 23;
    const rand = () => {
      seed = (seed * 16807) % 2147483647;
      return (seed - 1) / 2147483646;
    };
    const placements = [];
    for (let i = 0; i < 180 && placements.length < 110; i++) {
      const x = rand() * 22.8 - 11.4;
      const z = rand() * 14.8 - 7.4;
      if (this.points.some((p) => Math.hypot(p.x - x, p.z - z) < 0.98)) continue;
      if (Math.hypot((x - 7.35) / 1.15, z + 1.25) < 2.2) continue;
      placements.push([x, z, 0.1 + rand() * 0.17, i]);
    }
    const tuftGeo = new THREE.IcosahedronGeometry(1, 0);
    const tuftMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9, flatShading: true });
    const tuftInst = new THREE.InstancedMesh(tuftGeo, tuftMat, placements.length);
    const flowerColors = [0xf5d06e, 0xf2a799, 0xfaf6df, 0x7ea661, 0x89b36b];
    placements.forEach(([x, z, s, i], idx) => {
      dummy.position.set(x, 0.26, z);
      dummy.scale.set(s, s * 0.85, s);
      dummy.rotation.y = rand() * Math.PI;
      dummy.updateMatrix();
      tuftInst.setMatrixAt(idx, dummy.matrix);
      tuftInst.setColorAt(idx, tmpColor.setHex(i % 3 === 0 ? flowerColors[i % 3] : flowerColors[3 + (i % 2)]));
    });
    tuftInst.instanceMatrix.needsUpdate = true;
    if (tuftInst.instanceColor) tuftInst.instanceColor.needsUpdate = true;
    this.world.add(tuftInst);

    // Fluttering sunlit butterflies dancing around meadows & cottages
    this.butterflies = [];
    const bfColors = [0xffe073, 0xf6a3b5, 0x8ae2de, 0xffc66e, 0xf8f3dc, 0xb8a3f5];
    const wingGeo = new THREE.PlaneGeometry(0.11, 0.08);
    const bfOrigins = [
      [-6.5, 1.0, -0.5], [-1.8, 1.1, 0.4], [5.8, 1.05, 2.5],
      [7.2, 0.95, -0.4], [-4.4, 1.0, 4.0], [1.2, 1.1, -3.2],
    ];
    bfOrigins.forEach(([bx, by, bz], i) => {
      const g = new THREE.Group();
      const mat = new THREE.MeshBasicMaterial({ color: bfColors[i], side: THREE.DoubleSide });
      const lw = new THREE.Mesh(wingGeo, mat);
      lw.rotation.x = -Math.PI / 2;
      lw.position.x = -0.055;
      const rw = new THREE.Mesh(wingGeo, mat);
      rw.rotation.x = -Math.PI / 2;
      rw.position.x = 0.055;
      g.add(lw, rw);
      this.world.add(g);
      this.butterflies.push({ g, lw, rw, bx, by, bz, phase: i * 1.3 });
    });
  }

  flag(x, z, color) {
    this.box(x, 1.05, z, 0.05, 1.65, 0.05, 0xf7f1dc);
    const banner = this.mesh(new THREE.BoxGeometry(0.62, 0.36, 0.04), color, x + 0.32, 1.66, z);
    banner.rotation.z = -0.05;
  }

  _makePawns() {
    this.pawns = [];
    for (let i = 0; i < 4; i++) {
      const root = new THREE.Group();
      const body = new THREE.Group();
      root.add(body);
      root.visible = false;
      this.world.add(root);

      const col = PLAYER_COLORS[i];
      // Rounded tunic + backpack
      this.mesh(new THREE.CylinderGeometry(0.21, 0.26, 0.5, 8), col, 0, 0.72, 0, body);
      this.box(0, 0.74, -0.22, 0.26, 0.32, 0.14, 0xd8c39b, body);

      // Expressive head + blinking eyes + rosy cheeks
      this.mesh(new THREE.IcosahedronGeometry(0.26, 1), 0xf6d8b5, 0, 1.18, 0, body);
      const eyeL = this.box(-0.09, 1.2, 0.225, 0.05, 0.065, 0.025, 0x2f3e34, body);
      const eyeR = this.box(0.09, 1.2, 0.225, 0.05, 0.065, 0.025, 0x2f3e34, body);
      this.box(-0.15, 1.13, 0.205, 0.06, 0.035, 0.02, 0xf09c89, body);
      this.box(0.15, 1.13, 0.205, 0.06, 0.035, 0.02, 0xf09c89, body);

      // Signature hat/accessory per character
      if (i === 0) {
        this.mesh(new THREE.CylinderGeometry(0.28, 0.26, 0.12, 8), col, 0, 1.42, 0, body);
        this.mesh(new THREE.ConeGeometry(0.06, 0.16, 5), 0x8ab95c, 0, 1.56, 0, body);
      } else if (i === 1) {
        this.mesh(new THREE.CylinderGeometry(0.24, 0.26, 0.15, 8), col, 0, 1.42, 0, body);
        this.box(0, 1.37, 0.2, 0.34, 0.04, 0.16, 0xf6eedb, body);
      } else if (i === 2) {
        this.mesh(new THREE.ConeGeometry(0.3, 0.34, 6), col, 0, 1.5, 0, body);
      } else {
        const wiz = this.mesh(new THREE.ConeGeometry(0.29, 0.44, 7), col, 0, 1.54, 0, body);
        wiz.rotation.z = -0.14;
        this.mesh(new THREE.OctahedronGeometry(0.07, 0), 0xf6cf63, 0.06, 1.76, 0, body, {
          emissive: 0x996b0f,
          emissiveIntensity: 0.4,
        });
      }

      const limbs = [];
      for (const sign of [-1, 1]) {
        const leg = new THREE.Group();
        leg.position.set(sign * 0.12, 0.48, 0);
        body.add(leg);
        this.box(0, -0.2, 0, 0.14, 0.4, 0.16, 0x4f6150, leg);
        this.box(0, -0.38, 0.04, 0.18, 0.1, 0.25, 0xf6eedb, leg);
        limbs.push(leg);

        const arm = new THREE.Group();
        arm.position.set(sign * 0.28, 0.9, 0);
        body.add(arm);
        this.box(0, -0.17, 0, 0.13, 0.32, 0.14, col, arm);
        this.mesh(new THREE.SphereGeometry(0.08, 6, 5), 0xf6d8b5, 0, -0.35, 0, arm);
        limbs.push(arm);
      }

      // Active player beacon ring + floating bobbing chevron
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(0.38, 0.47, 24),
        new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.85, side: THREE.DoubleSide })
      );
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.02;
      root.add(ring);

      const arrow = new THREE.Mesh(
        new THREE.ConeGeometry(0.14, 0.24, 4),
        this.mat(0xffda6b, { emissive: 0xa67414, emissiveIntensity: 0.45 })
      );
      arrow.rotation.x = Math.PI;
      arrow.position.y = 2.05;
      root.add(arrow);

      // Iridescent Fresnel Bubble Shield shader
      const shieldMat = new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        uniforms: { uTime: { value: 0 } },
        vertexShader: `
          varying vec3 vNormal;
          varying vec3 vView;
          void main() {
            vec4 mv = modelViewMatrix * vec4(position, 1.0);
            vNormal = normalize(normalMatrix * normal);
            vView = normalize(-mv.xyz);
            gl_Position = projectionMatrix * mv;
          }
        `,
        fragmentShader: `
          uniform float uTime;
          varying vec3 vNormal;
          varying vec3 vView;
          void main() {
            float fresnel = pow(1.0 - max(dot(vNormal, vView), 0.0), 2.2);
            vec3 c1 = vec3(0.45, 0.92, 0.88);
            vec3 c2 = vec3(0.95, 0.85, 0.65);
            vec3 col = mix(c1, c2, sin(uTime * 2.5 + vNormal.y * 4.0) * 0.5 + 0.5);
            gl_FragColor = vec4(col, clamp(fresnel * 0.72 + 0.08, 0.0, 0.78));
          }
        `,
      });
      const shield = new THREE.Mesh(new THREE.SphereGeometry(0.88, 18, 14), shieldMat);
      shield.position.y = 0.85;
      shield.visible = false;
      root.add(shield);

      root.scale.setScalar(0.9);
      this.pawns.push({ root, body, limbs, eyes: [eyeL, eyeR], ring, arrow, shield, shieldMat, position: 0 });
    }
  }

  _buildParticlePool() {
    const geo = new THREE.IcosahedronGeometry(0.08, 0);
    for (let i = 0; i < 84; i++) {
      const mat = new THREE.MeshBasicMaterial({ color: 0xf7d06b, transparent: true, opacity: 1 });
      const m = new THREE.Mesh(geo, mat);
      m.visible = false;
      this.world.add(m);
      this.particles.push({
        mesh: m,
        active: false,
        life: 0,
        maxLife: 1,
        vel: new THREE.Vector3(),
        gravity: 5,
        spin: 0,
      });
    }
  }

  _spawnParticles(origin, count, { color = 0xf5cd68, speed = 2.6, up = 2.8, gravity = 6.2, life = 0.65, scale = 1 } = {}) {
    let spawned = 0;
    for (const p of this.particles) {
      if (p.active) continue;
      p.active = true;
      p.life = 0;
      p.maxLife = life * (0.75 + Math.random() * 0.45);
      p.gravity = gravity;
      p.spin = (Math.random() - 0.5) * 10;
      const a = Math.random() * Math.PI * 2;
      const sp = speed * (0.4 + Math.random() * 0.75);
      p.vel.set(Math.cos(a) * sp, up * (0.55 + Math.random() * 0.65), Math.sin(a) * sp);
      p.mesh.position.copy(origin);
      p.mesh.scale.setScalar(scale);
      p.mesh.material.color.setHex(Array.isArray(color) ? color[spawned % color.length] : color);
      p.mesh.material.opacity = 1;
      p.mesh.visible = true;
      spawned += 1;
      if (spawned >= count) break;
    }
  }

  _buildDicePool() {
    // Material face order: +X(3), -X(4), +Y(1), -Y(6), +Z(2), -Z(5)
    const faceOrder = [3, 4, 1, 6, 2, 5];
    const mats = faceOrder.map(
      (val) =>
        new THREE.MeshStandardMaterial({
          map: createPipTexture(val),
          roughness: 0.35,
          metalness: 0.05,
        })
    );
    const geo = new THREE.BoxGeometry(0.95, 0.95, 0.95);
    for (let i = 0; i < 2; i++) {
      const die = new THREE.Mesh(geo, mats);
      die.castShadow = true;
      die.visible = false;
      this.world.add(die);
      this.diceMeshes.push(die);
    }
  }

  _dieRotationForValue(val) {
    return {
      1: [0, 0, 0],
      2: [-Math.PI / 2, 0, 0],
      3: [0, 0, Math.PI / 2],
      4: [0, 0, -Math.PI / 2],
      5: [Math.PI / 2, 0, 0],
      6: [Math.PI, 0, 0],
    }[val] || [0, 0, 0];
  }

  async rollDice(diceValues = [1]) {
    const vals = diceValues.length ? diceValues : [1];
    this.audio?.diceRoll();
    const center = new THREE.Vector3(-0.3, 0.95, 0.55);
    const targets = vals.length === 2 ? [new THREE.Vector3(-1.05, 0.95, 0.55), new THREE.Vector3(0.45, 0.95, 0.55)] : [center];

    const startRots = vals.map(() => [Math.random() * 4, Math.random() * 4, Math.random() * 4]);
    const endRots = vals.map((v) => {
      const [rx, ry, rz] = this._dieRotationForValue(v);
      return [rx + Math.PI * 4, ry + (Math.random() - 0.5) * 0.5, rz + Math.PI * 2];
    });

    vals.forEach((_, i) => {
      this.diceMeshes[i].visible = true;
      this.diceMeshes[i].scale.setScalar(1);
    });
    if (vals.length === 1) this.diceMeshes[1].visible = false;

    let bounced = false;
    await this.tween(0.88, (t, raw) => {
      const bounce = Math.abs(Math.sin(raw * Math.PI * 2.2)) * (1 - raw) * 2.4;
      if (raw > 0.45 && !bounced) {
        bounced = true;
        this.audio?.diceLand();
      }
      vals.forEach((_, i) => {
        const d = this.diceMeshes[i];
        d.position.set(targets[i].x, targets[i].y + bounce, targets[i].z);
        d.rotation.set(
          THREE.MathUtils.lerp(startRots[i][0], endRots[i][0], t),
          THREE.MathUtils.lerp(startRots[i][1], endRots[i][1], t),
          THREE.MathUtils.lerp(startRots[i][2], endRots[i][2], t)
        );
      });
    });

    targets.forEach((pos) => this._spawnParticles(pos, 10, { color: 0xf7d26b, speed: 2.2, up: 2.2 }));
    await this.tween(0.45, (t) => {
      vals.forEach((_, i) => {
        const s = t > 0.6 ? 1 - (t - 0.6) / 0.4 : 1;
        this.diceMeshes[i].scale.setScalar(Math.max(0.01, s));
      });
    });
    this.diceMeshes.forEach((d) => {
      d.visible = false;
      d.scale.setScalar(1);
    });
  }

  placePawn(id, progress) {
    const pawn = this.pawns[id];
    const wrapped = ((progress % 49) + 49) % 49;
    const t = Math.min(wrapped, 48) / 48;
    const p = this.path.getPointAt(t);
    const dir = this.path.getTangentAt(t);
    const offsets = [
      [-0.2, -0.17],
      [0.2, -0.17],
      [-0.2, 0.17],
      [0.2, 0.17],
    ];
    pawn.root.position.set(p.x + offsets[id][0], 0.44, p.z + offsets[id][1]);
    pawn.root.rotation.y = Math.atan2(dir.x, dir.z);
  }

  neutralPose(p) {
    p.body.position.set(0, 0, 0);
    p.body.rotation.set(0, 0, 0);
    p.body.scale.setScalar(1);
    p.limbs.forEach((l) => l.rotation.set(0, 0, 0));
  }

  setState(g) {
    this.lastState = structuredClone(g);
    this.activePlayer = g.current || 0;
    this.isFinished = g.phase === "finished";
    this.pawns.forEach((p, i) => {
      const state = g.players[i];
      p.root.visible = Boolean(state);
      if (state) {
        p.position = state.position;
        p.shield.visible = state.shield;
        this.placePawn(i, state.position);
        const isCurrent = i === g.current && g.phase !== "setup" && g.phase !== "finished";
        p.ring.visible = isCurrent;
        p.arrow.visible = isCurrent;
        this.neutralPose(p);
      }
    });
    this.renderer.shadowMap.needsUpdate = true;
  }

  tween(seconds, fn = () => {}) {
    return new Promise((resolve) => {
      this.timeline = {
        start: performance.now(),
        duration: Math.max(16, seconds * 1000),
        fn,
        resolve,
      };
    });
  }

  caption(title, text = "") {
    this.hud.querySelector("h2").textContent = title;
    this.hud.querySelector(".shot-caption p").textContent = text;
  }

  async beginShot(g, id, title) {
    this.skipShot = false;
    this.cinematic = true;
    this.followId = id;
    this.shotEnding = false;
    this.hud.querySelector(".shot-player").textContent = `${g.players[id].name.toUpperCase()} · ROUND ${g.round}`;
    this.hud.style.setProperty("--player-color", g.players[id].color);
    this.caption(title);
    this.el.classList.add("cinematic");
    document.body.classList.add("action-playing");
    this.el.dataset.shot = "enter";
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.resize();
    this.shotEntering = true;
    const from = this.camera.position.clone();
    const fromLook = this.cameraLook.clone();
    const pose = this.followPose();
    await this.tween(0.75, (t) => {
      this.camera.position.lerpVectors(from, pose.position, t);
      this.cameraLook.lerpVectors(fromLook, pose.look, t);
      this.camera.lookAt(this.cameraLook);
    });
    this.shotEntering = false;
  }

  async endShot(g) {
    this.setState(g);
    this.caption("Your move. Your moment.", g.event.text);
    await this.tween(0.55);
    this.shotEnding = true;
    const from = this.camera.position.clone();
    const look = this.cameraLook.clone();
    const to = this.overviewPosition();
    this.el.dataset.shot = "return";
    await this.tween(0.7, (t) => {
      this.camera.position.lerpVectors(from, to, t);
      this.cameraLook.lerpVectors(look, this.overviewLook, t);
      this.camera.lookAt(this.cameraLook);
    });
    this.cinematic = false;
    this.el.classList.remove("cinematic");
    document.body.classList.remove("action-playing");
    delete this.el.dataset.shot;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.resize();
    this.shotEnding = false;
  }

  async moveTo(g) {
    const move = g.last_move || {};
    const id = move.player ?? g.current;
    const from = move.from ?? this.pawns[id].position;
    const roll = move.roll ?? g.roll ?? 1;
    const wrapped = Boolean(move.wrapped);
    const to = g.players[id].position;
    const p = this.pawns[id];

    await this.beginShot(g, id, "Rolling onto the trail…");
    this.el.dataset.shot = "running";
    this.caption(`${g.players[id].name} is on the move.`, `${roll} spaces · Adventure awaits.`);

    let lastStep = -1;
    for (let step = 0; step < roll; step++) {
      const curPos = (from + step) % 49;
      const nextPos = (from + step + 1) % 49;
      const isPortalJump = curPos === 48 && nextPos === 0;
      if (isPortalJump) {
        this.audio?.portal();
        this._spawnParticles(p.root.position.clone().add(new THREE.Vector3(0, 0.8, 0)), 18, {
          color: [0x59e0d8, 0xf6cf63],
          speed: 3.2,
          up: 3.4,
        });
        await this.tween(0.32, (t) => p.body.scale.setScalar(Math.max(0.05, 1 - t)));
        this.placePawn(id, 0);
        this._spawnParticles(p.root.position.clone().add(new THREE.Vector3(0, 0.8, 0)), 18, {
          color: [0x59e0d8, 0xf6cf63],
          speed: 3.2,
          up: 3.4,
        });
        await this.tween(0.32, (t) => p.body.scale.setScalar(Math.max(0.05, t)));
        p.body.scale.setScalar(1);
        continue;
      }

      await this.tween(0.28, (t, raw) => {
        const progress = curPos + raw;
        this.placePawn(id, progress);
        const hop = Math.sin(raw * Math.PI);
        p.body.position.y = hop * 0.42;
        p.body.scale.set(1 + (1 - hop) * 0.08, 1 - (1 - hop) * 0.08, 1 + (1 - hop) * 0.08);
        p.body.rotation.x = 0.14 * hop;
        p.limbs[0].rotation.x = Math.sin(raw * Math.PI) * 0.65;
        p.limbs[2].rotation.x = -Math.sin(raw * Math.PI) * 0.65;
        p.limbs[1].rotation.x = -Math.sin(raw * Math.PI) * 0.7;
        p.limbs[3].rotation.x = Math.sin(raw * Math.PI) * 0.7;
      });
      if (step !== lastStep) {
        lastStep = step;
        this.audio?.step(step);
        this._spawnParticles(p.root.position.clone().add(new THREE.Vector3(0, 0.08, 0)), 4, {
          color: 0xeae2c6,
          speed: 1.1,
          up: 0.9,
          life: 0.32,
          scale: 0.75,
        });
      }
    }

    this.setState(g);
    const landedKind = move.landed_kind || this.types[to];
    await this.landing(g, landedKind, wrapped, move);
    await this.endShot(g);
  }

  makeProp(kind) {
    const group = new THREE.Group();
    this.world.add(group);
    if (kind === "keys") {
      this.mesh(new THREE.TorusGeometry(0.16, 0.055, 6, 12), 0xf5c84c, 0, 0.2, 0, group, { roughness: 0.35, metalness: 0.4 });
      this.box(0, -0.09, 0, 0.07, 0.4, 0.07, 0xf5c84c, group);
      this.box(0.08, -0.23, 0, 0.16, 0.07, 0.07, 0xf5c84c, group);
    } else if (kind === "trophy") {
      this.mesh(new THREE.CylinderGeometry(0.24, 0.12, 0.32, 8), 0xf6ce58, 0, 0.16, 0, group, { roughness: 0.3, metalness: 0.45 });
      this.box(0, -0.12, 0, 0.08, 0.25, 0.08, 0xd4a43f, group);
      this.box(0, -0.28, 0, 0.38, 0.1, 0.28, 0x997942, group);
      for (const x of [-0.24, 0.24]) {
        const handle = this.mesh(new THREE.TorusGeometry(0.12, 0.035, 5, 8), 0xf6ce58, x, 0.16, 0, group);
        handle.scale.y = 0.9;
      }
    } else if (kind === "rocket") {
      const body = this.mesh(new THREE.CylinderGeometry(0.095, 0.095, 0.36, 8), 0xf4ecd4, 0, 0, 0, group);
      body.rotation.x = Math.PI / 2;
      const nose = this.mesh(new THREE.ConeGeometry(0.11, 0.2, 8), 0xe06950, 0, 0, 0.27, group);
      nose.rotation.x = Math.PI / 2;
      const flame = this.mesh(new THREE.ConeGeometry(0.085, 0.32, 6), 0xffb347, 0, 0, -0.32, group, {
        emissive: 0xff771f,
        emissiveIntensity: 0.9,
      });
      flame.rotation.x = -Math.PI / 2;
    } else if (kind === "heal") {
      this.box(0, 0, 0, 0.16, 0.52, 0.12, 0x8bc978, group);
      this.box(0, 0, 0, 0.48, 0.16, 0.12, 0x8bc978, group);
    } else {
      this.box(0, 0, 0, 0.44, 0.44, 0.44, 0xedb74e, group);
      this.box(0, 0, 0, 0.47, 0.09, 0.47, 0xfff3c4, group);
      this.box(0, 0, 0, 0.09, 0.47, 0.47, 0xfff3c4, group);
    }
    return group;
  }

  disposeProp(prop) {
    prop.traverse((o) => {
      if (o.isMesh) o.geometry.dispose();
    });
    prop.removeFromParent();
  }

  async pickup(g, kind = "keys") {
    const p = this.pawns[g.current];
    const prop = this.makeProp(kind);
    const forward = new THREE.Vector3(0, 0, 1).applyQuaternion(p.root.quaternion);
    const base = p.root.position.clone().addScaledVector(forward, 0.55);
    base.y = 0.7;
    prop.position.copy(base);
    this.el.dataset.shot = "pickup";
    this.caption(
      kind === "trophy"
        ? "A shiny little victory!"
        : kind === "item"
          ? "Something up your sleeve."
          : kind === "heal"
            ? "Warmth by the fire."
            : "Finders keepers!",
      g.event.text
    );

    if (kind === "trophy") this.audio?.trophy();
    else if (kind === "heal") this.audio?.heal();
    else this.audio?.keys();

    await this.tween(0.32, (t) => {
      p.body.rotation.x = t * 0.45;
      p.body.position.y = -t * 0.12;
      p.limbs[1].rotation.x = -t * 1.1;
      p.limbs[3].rotation.x = -t * 1.1;
      prop.rotation.y = t;
    });
    await this.tween(0.65, (t, raw) => {
      p.body.rotation.x = (1 - t) * 0.45;
      p.body.position.y = Math.sin(raw * Math.PI) * 0.34;
      p.limbs[1].rotation.x = -1.1 - t * 1.7;
      p.limbs[3].rotation.x = -1.1 - t * 1.7;
      prop.position.y = 0.7 + t * 1.6;
      prop.rotation.y = t * Math.PI * 2.5;
      prop.scale.setScalar(1 + t * 0.25);
    });
    this._spawnParticles(prop.position, 22, {
      color: kind === "heal" ? [0x8bc978, 0xfaf6df] : [0xf5cf5e, 0xff9e7d, 0x7bdcd4],
      speed: 3.1,
      up: 3.2,
    });
    await this.tween(0.35);
    this.disposeProp(prop);
    this.neutralPose(p);
  }

  async landing(g, kind, _wrapped, move = {}) {
    if (kind === "trap") {
      const p = this.pawns[g.current];
      this.el.dataset.shot = "hit";
      this.caption(move.shield_broken ? "Bubble shield held!" : "Ouch. That looked personal.", g.event.text);
      if (move.shield_broken) this.audio?.shield();
      else {
        this.audio?.trap();
        this.shakeAmp = 0.22;
        this.shakeTime = 0.42;
      }
      this._spawnParticles(p.root.position.clone().add(new THREE.Vector3(0, 0.8, 0)), 16, {
        color: move.shield_broken ? 0x7de0d8 : 0xe06850,
        speed: 2.8,
        up: 2.6,
      });
      await this.tween(0.65, (t, raw) => {
        p.body.rotation.z = Math.sin(raw * Math.PI * 5) * (1 - raw) * 0.32;
        p.body.position.y = Math.sin(raw * Math.PI) * 0.28;
      });
      this.neutralPose(p);
    } else if (kind === "chance") {
      await this.pickup(g, "item");
    } else if (kind === "campfire") {
      await this.pickup(g, "heal");
    } else if (kind === "chest") {
      this.el.dataset.shot = "chest";
      this.caption("Eyes on the prize.", g.pending?.text || g.event.text);
      const p = this.pawns[g.current];
      const chest = this.chests.get(g.players[g.current].position);
      await this.tween(0.7, (t, raw) => {
        p.limbs[3].rotation.x = -Math.sin(raw * Math.PI) * 1.6;
        if (chest) chest.lid.rotation.x = -Math.sin(raw * Math.PI) * 0.7;
      });
      this.neutralPose(p);
    } else {
      await this.pickup(g, "keys");
    }
  }

  async playEvent(g, { action, body }) {
    if (action === "choice" && body.option !== "buy") {
      this.setState(g);
      return;
    }
    await this.beginShot(g, g.current, action === "choice" ? "Claiming a shiny trophy!" : "A little friendly sabotage.");
    const p = this.pawns[g.current];

    if (action === "choice") {
      // Open nearest chest visually if standing on/near one
      for (const [idx, chest] of this.chests.entries()) {
        if (Math.abs(idx - g.players[g.current].position) <= 6) {
          this.tween(0.5, (t) => {
            chest.lid.rotation.x = -t * 1.15;
          });
          await this.pickup(g, "trophy");
          chest.lid.rotation.x = 0;
          break;
        }
      }
      if (!this.chests.has(g.players[g.current].position)) {
        await this.pickup(g, "trophy");
      }
    } else if (body.item === "shield") {
      this.el.dataset.shot = "shield";
      this.caption("Bubble up!", g.event.text);
      this.audio?.shield();
      p.shield.visible = true;
      await this.tween(0.7, (t, raw) => {
        p.shield.scale.setScalar(0.1 + 0.9 * t);
        p.limbs[1].rotation.x = -Math.sin(raw * Math.PI) * 2.4;
        p.limbs[3].rotation.x = -Math.sin(raw * Math.PI) * 2.4;
      });
      p.shield.scale.setScalar(1);
    } else if (body.item === "turbo") {
      this.el.dataset.shot = "shield";
      this.caption("Turbo Dice primed!", g.event.text);
      this.audio?.chime();
      this._spawnParticles(p.root.position.clone().add(new THREE.Vector3(0, 1, 0)), 18, {
        color: [0xf7d06b, 0xff9d5c],
        speed: 2.8,
        up: 3.4,
      });
      await this.tween(0.55, (t, raw) => {
        p.body.position.y = Math.sin(raw * Math.PI) * 0.45;
        p.body.rotation.y = raw * Math.PI * 2;
      });
      this.neutralPose(p);
    } else if (body.item === "swap") {
      this.el.dataset.shot = "swap";
      this.caption("Trading places!", g.event.text);
      this.audio?.swap();
      const targetPawn = this.pawns[body.target];
      this._spawnParticles(p.root.position.clone().add(new THREE.Vector3(0, 0.7, 0)), 14, { color: 0xb59bc5 });
      this._spawnParticles(targetPawn.root.position.clone().add(new THREE.Vector3(0, 0.7, 0)), 14, { color: 0x6dd6d0 });
      await this.tween(0.38, (t) => {
        p.body.scale.setScalar(Math.max(0.02, 1 - t));
        targetPawn.body.scale.setScalar(Math.max(0.02, 1 - t));
      });
      this.setState(g);
      await this.tween(0.45, (t) => {
        p.body.scale.setScalar(Math.max(0.02, t));
        targetPawn.body.scale.setScalar(Math.max(0.02, t));
      });
      this._spawnParticles(p.root.position.clone().add(new THREE.Vector3(0, 0.7, 0)), 16, { color: 0xb59bc5 });
    } else {
      const target = this.pawns[body.target];
      const direction = target.root.position.clone().sub(p.root.position).setY(0).normalize();
      p.root.rotation.y = Math.atan2(direction.x, direction.z);
      this.el.dataset.shot = "attack";
      this.caption(body.item === "rocket" ? "Special delivery!" : "Your keys? Our keys.", g.event.text);
      if (body.item === "rocket") this.audio?.rocket();
      else this.audio?.magnet();

      await this.tween(0.4, (t) => {
        p.limbs[3].rotation.x = -t * 2.2;
        p.body.rotation.z = -t * 0.12;
      });

      const prop = this.makeProp(body.item === "rocket" ? "rocket" : "keys");
      const a = (body.item === "rocket" ? p : target).root.position.clone().add(new THREE.Vector3(0, 1, 0));
      const b = (body.item === "rocket" ? target : p).root.position.clone().add(new THREE.Vector3(0, 1, 0));
      prop.position.copy(a);
      prop.lookAt(b);

      await this.tween(0.75, (t, raw) => {
        prop.position.lerpVectors(a, b, raw);
        prop.position.y += Math.sin(raw * Math.PI) * 1.8;
        p.limbs[3].rotation.x = -2.2 + raw * 1.6;
        if (Math.random() < 0.45) {
          this._spawnParticles(prop.position, 2, {
            color: body.item === "rocket" ? 0xff9f45 : 0xf7d264,
            speed: 0.7,
            up: 0.4,
            life: 0.3,
            scale: 0.7,
          });
        }
      });
      this.disposeProp(prop);

      this.followId = body.target;
      this.el.dataset.shot = "impact";
      this.shakeAmp = 0.25;
      this.shakeTime = 0.45;
      this._spawnParticles(target.root.position.clone().add(new THREE.Vector3(0, 0.9, 0)), 22, {
        color: body.item === "rocket" ? [0xff7d47, 0xffd05c] : [0xf5cf5e, 0x6dd4cc],
        speed: 3.4,
        up: 3.2,
      });
      await this.tween(0.55, (t, raw) => {
        target.body.rotation.z = Math.sin(raw * Math.PI * 4) * (1 - raw) * 0.34;
        target.body.position.y = Math.sin(raw * Math.PI) * 0.35;
      });
      this.neutralPose(target);
      this.followId = g.current;
    }

    await this.endShot(g);
  }

  setPreset(preset) {
    this.preset = preset;
    if (preset === "diorama") {
      this.targetAngle = 0.16;
      this.targetZoom = 1.0;
    } else if (preset === "scenic") {
      this.targetAngle = -0.38;
      this.targetZoom = 1.25;
    } else if (preset === "top") {
      this.targetAngle = 0.0;
      this.targetZoom = 0.92;
    }
  }

  rotate(dir) {
    if (this.cinematic) return;
    this.targetAngle += dir * 0.35;
  }

  reset() {
    if (this.cinematic) {
      this.skipShot = true;
      return;
    }
    this.setPreset("diorama");
  }

  followPose() {
    const p = this.pawns[this.followId];
    const forward = new THREE.Vector3(0, 0, 1).applyQuaternion(p.root.quaternion);
    const side = new THREE.Vector3(forward.z, 0, -forward.x);
    return {
      look: p.root.position.clone().add(new THREE.Vector3(0, 1.05, 0)).addScaledVector(forward, 0.35),
      position: p.root.position
        .clone()
        .addScaledVector(forward, -4.6)
        .addScaledVector(side, 1.7)
        .add(new THREE.Vector3(0, 2.75, 0)),
    };
  }

  overviewPosition() {
    const aspect = Math.max(0.5, this.el.clientWidth / Math.max(1, this.el.clientHeight));
    const half = (aspect < 1 ? 15 / aspect : 12.2) / this.zoom;
    const distance = half / Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    const height = this.preset === "top" ? 42 : this.preset === "scenic" ? 21 : 29;
    return new THREE.Vector3(Math.sin(this.angle) * 30 + 9, height, Math.cos(this.angle) * 30)
      .normalize()
      .multiplyScalar(distance);
  }

  _setupControls() {
    let dragging = false;
    let lastX = 0;

    this.el.addEventListener("pointerdown", (e) => {
      if (this.cinematic) return;
      dragging = true;
      lastX = e.clientX;
      this.angleVel = 0;
      this.el.setPointerCapture(e.pointerId);
    });

    this.el.addEventListener("pointermove", (e) => {
      const rect = this.el.getBoundingClientRect();
      this.pointerNDC.x = ((e.clientX - rect.left) / Math.max(1, rect.width)) * 2 - 1;
      this.pointerNDC.y = -((e.clientY - rect.top) / Math.max(1, rect.height)) * 2 + 1;

      if (dragging && !this.cinematic) {
        const dx = e.clientX - lastX;
        this.targetAngle += dx * 0.0055;
        this.angleVel = dx * 0.004;
        lastX = e.clientX;
      } else if (!this.cinematic && this.onTileHover) {
        this._checkTileHover(e.clientX, e.clientY);
      }
    });

    const release = () => {
      dragging = false;
    };
    this.el.addEventListener("pointerup", release);
    this.el.addEventListener("pointercancel", release);
    this.el.addEventListener("pointerleave", () => {
      dragging = false;
      this.hoveredTile = -1;
      this.hoverRing.visible = false;
      this.onTileHover?.(null);
    });

    this.el.addEventListener(
      "wheel",
      (e) => {
        e.preventDefault();
        if (this.cinematic) return;
        this.targetZoom = THREE.MathUtils.clamp(this.targetZoom - e.deltaY * 0.00075, 0.72, 1.7);
      },
      { passive: false }
    );
  }

  _checkTileHover(clientX, clientY) {
    this.raycaster.setFromCamera(this.pointerNDC, this.camera);
    const hits = this.raycaster.intersectObjects(this.tileMeshes, false);
    if (hits.length > 0) {
      const idx = hits[0].object.userData.tileIndex;
      const p = this.points[idx];
      this.hoverRing.position.set(p.x, 0.475, p.z);
      this.hoverRing.visible = true;
      this.hoveredTile = idx;
      const kind = this.types[idx];
      this.onTileHover({
        index: idx,
        kind,
        label: TILE_LABELS[kind] || "Trail Space",
        x: clientX,
        y: clientY,
      });
    } else if (this.hoveredTile !== -1) {
      this.hoveredTile = -1;
      this.hoverRing.visible = false;
      this.onTileHover(null);
    }
  }

  resize() {
    const w = Math.max(1, this.el.clientWidth);
    const h = Math.max(1, this.el.clientHeight);
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    if (!this.cinematic) {
      this.camera.position.copy(this.overviewPosition());
      this.camera.lookAt(this.overviewLook);
    }
    // setSize clears the canvas. Draw at once so no blank frame shows
    // when the view switches to or from the full-screen action camera.
    this.renderer.render(this.scene, this.camera);
  }

  _animate() {
    this._raf = requestAnimationFrame(() => this._animate());
    const now = performance.now();
    const dt = Math.min((now - (this.lastTime || now)) / 1000, 0.08);
    this.lastTime = now;
    this.time = now / 1000;

    // Update GPU shaders
    if (this.oceanMat) this.oceanMat.uniforms.uTime.value = this.time;
    if (this.lakeMat) this.lakeMat.uniforms.uTime.value = this.time;
    if (this.waterfallMat) this.waterfallMat.uniforms.uTime.value = this.time;
    if (this.portalMat) this.portalMat.uniforms.uTime.value = this.time;

    // Ambient diorama motion
    if (this.lighthouseBeam) this.lighthouseBeam.rotation.y += dt * 0.72;
    if (this.boat) {
      this.boat.position.y = 0.295 + Math.sin(this.time * 2.1) * 0.025;
      this.boat.rotation.z = Math.sin(this.time * 1.7) * 0.06;
      this.boat.rotation.x = Math.cos(this.time * 1.3) * 0.04;
    }
    if (this.splashRing) {
      const pulse = 0.85 + Math.sin(this.time * 4.2) * 0.18;
      this.splashRing.scale.setScalar(pulse);
      this.splashRing.material.opacity = 0.55 + Math.cos(this.time * 4.2) * 0.22;
    }
    if (this.campLight) {
      this.campLight.intensity = 1.25 + Math.sin(this.time * 14) * 0.18;
    }
    for (const f of this.campFlames) {
      const s = 0.9 + Math.sin(this.time * 11 + f.phase) * 0.18;
      f.mesh.scale.set(1, s, 1);
    }
    for (const prop of this.floatingProps) {
      prop.mesh.position.y = prop.baseY + Math.sin(this.time * 2.4 + prop.phase) * 0.08;
      prop.mesh.rotation.y += dt * prop.spin;
    }
    for (const c of this.clouds) {
      c.g.position.x = c.baseX + Math.sin(this.time * 0.08 + c.phase) * 3.5;
      c.g.position.y = c.baseY + Math.cos(this.time * 0.4 + c.phase) * 0.15;
    }
    for (const b of this.birds) {
      b.angle += dt * 0.34;
      b.bird.position.set(Math.cos(b.angle) * b.radius, b.y + Math.sin(this.time * 2 + b.angle) * 0.25, Math.sin(b.angle) * b.radius);
      b.bird.rotation.y = -b.angle;
      const flap = Math.sin(this.time * 8 + b.angle) * 0.45;
      b.lw.rotation.z = flap;
      b.rw.rotation.z = -flap;
    }
    if (this.butterflies) {
      for (const bf of this.butterflies) {
        const t = this.time * 1.15 + bf.phase;
        bf.g.position.set(
          bf.bx + Math.sin(t * 0.9) * 0.85,
          bf.by + Math.sin(t * 2.4) * 0.16,
          bf.bz + Math.cos(t * 0.75) * 0.85
        );
        bf.g.rotation.y = Math.atan2(Math.cos(t * 0.9) * 0.9, -Math.sin(t * 0.75) * 0.75);
        const flap = Math.sin(this.time * 16 + bf.phase) * 0.75;
        bf.lw.rotation.z = flap;
        bf.rw.rotation.z = -flap;
      }
    }
    for (const puff of this.smokePuffs) {
      const cycle = (this.time * 0.38 + puff.phase) % 1;
      puff.mesh.position.set(puff.x + Math.sin(cycle * 5) * 0.12, puff.y + cycle * 1.5, puff.z);
      const s = 0.45 + cycle * 1.1;
      puff.mesh.scale.setScalar(s * (1 - cycle * 0.5));
    }

    // Idle breathing, eye blinks, active halo, and shield shimmer on visible pawns
    this.pawns.forEach((p, idx) => {
      if (!p.root.visible) return;
      if (p.shield.visible) p.shieldMat.uniforms.uTime.value = this.time;
      if (!this.cinematic) {
        p.body.position.y = Math.sin(this.time * 2.8 + idx * 1.4) * 0.03;
      }
      const blink = Math.sin(this.time * 0.9 + idx * 2.1) > 0.97 ? 0.15 : 1.0;
      p.eyes[0].scale.y = blink;
      p.eyes[1].scale.y = blink;
      if (p.arrow.visible) {
        p.arrow.position.y = 2.02 + Math.sin(this.time * 4.2) * 0.12;
        p.arrow.rotation.y = this.time * 1.8;
      }
      if (p.ring.visible) {
        const pulse = 1 + Math.sin(this.time * 3.8) * 0.09;
        p.ring.scale.setScalar(pulse);
      }
    });

    // Update particle pool
    for (const p of this.particles) {
      if (!p.active) continue;
      p.life += dt;
      if (p.life >= p.maxLife) {
        p.active = false;
        p.mesh.visible = false;
        continue;
      }
      const frac = p.life / p.maxLife;
      p.vel.y -= p.gravity * dt;
      p.mesh.position.addScaledVector(p.vel, dt);
      p.mesh.rotation.x += p.spin * dt;
      p.mesh.rotation.y += p.spin * dt;
      p.mesh.material.opacity = 1 - frac;
      p.mesh.scale.setScalar(Math.max(0.05, 1 - frac * 0.7));
    }

    // Victory confetti celebration
    if (this.isFinished && !this.cinematic) {
      this.confettiCooldown -= dt;
      if (this.confettiCooldown <= 0) {
        this.confettiCooldown = 0.45;
        this._spawnParticles(new THREE.Vector3((Math.random() - 0.5) * 6, 4.8, (Math.random() - 0.5) * 4), 8, {
          color: [0xe06d53, 0x4c96a8, 0xf2c45a, 0xa47bb8, 0x7da657],
          speed: 2.2,
          up: 1.5,
          gravity: 3.2,
          life: 1.4,
        });
      }
    }

    // Active tween timeline
    const timeline = this.timeline;
    if (timeline) {
      this.renderer.shadowMap.needsUpdate = true;
      const raw = this.skipShot ? 1 : Math.min(1, (now - timeline.start) / timeline.duration);
      timeline.fn(raw * raw * (3 - 2 * raw), raw, (now - timeline.start) / 1000);
      if (raw >= 1) {
        this.timeline = null;
        timeline.resolve();
      }
    }

    // Camera interpolation & subtle inertia
    if (this.cinematic && !this.shotEnding && !this.shotEntering) {
      const pose = this.followPose();
      const lerp = 1 - Math.exp(-dt * 7.5);
      this.camera.position.lerp(pose.position, lerp);
      this.cameraLook.lerp(pose.look, lerp);
      if (this.shakeTime > 0) {
        this.shakeTime -= dt;
        const mag = this.shakeAmp * (this.shakeTime / 0.45);
        this.camera.position.x += (Math.random() - 0.5) * mag;
        this.camera.position.y += (Math.random() - 0.5) * mag;
      }
      this.camera.lookAt(this.cameraLook);
    } else if (!this.cinematic) {
      if (Math.abs(this.angleVel) > 0.0001) {
        this.targetAngle += this.angleVel;
        this.angleVel *= Math.exp(-dt * 6);
      }
      const smooth = 1 - Math.exp(-dt * 9);
      this.angle = THREE.MathUtils.lerp(this.angle, this.targetAngle, smooth);
      this.zoom = THREE.MathUtils.lerp(this.zoom, this.targetZoom, smooth);
      this.camera.position.lerp(this.overviewPosition(), smooth);
      this.cameraLook.lerp(this.overviewLook, smooth);
      this.camera.lookAt(this.cameraLook);
    }

    this.renderer.render(this.scene, this.camera);
  }

  dispose() {
    cancelAnimationFrame(this._raf);
    this.resizeObserver.disconnect();
    document.removeEventListener("keydown", this._onKeyDown);
    this.renderer.dispose();
  }
}
