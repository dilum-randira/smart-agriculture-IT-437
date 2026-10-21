import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

/** Entire module (including Three.js) is a separately loaded, optional chunk. */
export default function FarmScene({ node, onNodeChange, onUnavailable, allowedNodes = ["NODE_01", "NODE_02"] }) {
  const mount = useRef(null);
  const runtime = useRef(null);
  const [hover, setHover] = useState("");
  const [playing, setPlaying] = useState(() => !window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  useEffect(() => {
    const host = mount.current;
    let renderer;
    try {
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("webgl2", { antialias: true, alpha: true, powerPreference: "low-power" });
      if (!context) { onUnavailable(); return undefined; }
      renderer = new THREE.WebGLRenderer({ canvas, context, antialias: true, alpha: true, powerPreference: "low-power" });
    }
    catch { onUnavailable(); return undefined; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.setClearColor("#edf2e9", 0);
    renderer.domElement.setAttribute("aria-label", "Conceptual pepper cultivation field. Drag to orbit, pinch to zoom. No real installation is represented.");
    renderer.domElement.setAttribute("role", "img");
    host.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, .1, 100);
    camera.position.set(8.3, 6.2, 8.3);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, .2, 0);
    controls.enableDamping = false;
    controls.enablePan = false;
    controls.minDistance = 6.5;
    controls.maxDistance = 18;
    controls.minPolarAngle = .35;
    controls.maxPolarAngle = Math.PI / 2.3;
    controls.autoRotateSpeed = .35;
    controls.update();
    scene.add(new THREE.HemisphereLight("#fff9e8", "#71866c", 3));
    const sunlight = new THREE.DirectionalLight("#fff5db", 3.5);
    sunlight.position.set(-5, 10, 5); sunlight.castShadow = true;
    sunlight.shadow.mapSize.set(512, 512);
    Object.assign(sunlight.shadow.camera, { left: -7, right: 7, top: 7, bottom: -7, near: .1, far: 30 });
    sunlight.shadow.normalBias = .04;
    scene.add(sunlight);
    const materials = new Map();
    const material = (color) => {
      if (!materials.has(color)) materials.set(color, new THREE.MeshStandardMaterial({ color, roughness: .88 }));
      return materials.get(color);
    };
    const box = new THREE.BoxGeometry(1, 1, 1);
    const sphere = new THREE.SphereGeometry(1, 8, 6);
    const cylinder = new THREE.CylinderGeometry(1, 1, 1, 8);
    function mesh(geometry, color, position, scale, parent = scene) {
      const obj = new THREE.Mesh(geometry, material(color));
      obj.position.set(...position); obj.scale.set(...scale); obj.castShadow = true; obj.receiveShadow = true;
      parent.add(obj); return obj;
    }
    mesh(box, "#a68055", [0, -.85, 0], [8.2, .35, 6.1]);
    mesh(box, "#85603e", [0, -.55, 0], [8.2, .25, 6.1]);
    mesh(box, "#58472e", [0, -.25, 0], [8.2, .35, 6.1]);
    mesh(box, "#71804b", [0, -.04, 0], [8.25, .08, 6.15]);
    for (let row = 0; row < 4; row++) {
      const z = -1.9 + row * 1.24;
      mesh(box, "#715039", [-.35, .04, z], [6.2, .16, .7]);
      mesh(box, "#344539", [-.35, .14, z + .25], [6.4, .035, .035]);
      for (let col = 0; col < 6; col++) {
        const x = -2.9 + col * 1.03;
        const plant = new THREE.Group(); plant.position.set(x, .13, z); scene.add(plant);
        mesh(cylinder, "#547c38", [0, .32, 0], [.035, .65, .035], plant);
        for (let leaf = 0; leaf < 6; leaf++) {
          const angle = leaf * Math.PI * 2 / 3 + row * .4;
          const height = .3 + leaf * .075;
          const obj = mesh(sphere, leaf % 2 ? "#517d35" : "#2f633e", [Math.cos(angle) * .17, height, Math.sin(angle) * .17], [.27, .075, .14], plant);
          obj.rotation.set(.2, -angle, leaf % 2 ? -.35 : .35);
        }
        const pepper = mesh(sphere, (row + col) % 3 ? "#d88935" : "#b74a32", [.13, .37, .13], [.07, .11, .065], plant);
        pepper.rotation.z = .15;
      }
    }
    // Irrigation lines and monitoring forms are conceptual, not connected hardware.
    mesh(box, "#344539", [-3.8, .14, -.1], [.045, .045, 4.7]);
    const sensors = [];
    const highlights = {};
    for (const [name, position] of [["NODE_01", [-2.5, 0, 2.5]], ["NODE_02", [2, 0, -2.6]]]) {
      const [x, , z] = position;
      mesh(cylinder, "#e7e9df", [x, .65, z], [.04, 1.35, .04]);
      const sensor = mesh(box, "#f7f7ed", [x, 1.3, z], [.3, .38, .25]);
      sensor.userData.label = `${name} · Air temperature & humidity sensor; soil index probe`;
      sensors.push(sensor);
      highlights[name] = mesh(cylinder, "#9fb697", [x, .17, z], [.27, .035, .27]);
      mesh(cylinder, "#b1b6a0", [x + .18, .03, z + .12], [.025, .5, .025]);
    }
    const station = new THREE.Group(); station.position.set(3.35, 0, 1.5); scene.add(station);
    mesh(cylinder, "#d8ddd1", [0, 1.15, 0], [.045, 2.3, .045], station);
    mesh(box, "#f0f0e2", [0, 1.4, 0], [.4, .42, .35], station);
    const panel = mesh(box, "#324f5d", [.15, 1.98, .04], [.8, .06, .5], station); panel.rotation.z = -.3;
    const wind = mesh(box, "#c6cebd", [0, 2.42, 0], [.8, .025, .06], station);
    wind.userData.label = "Conceptual environmental monitoring station · not live hardware"; sensors.push(wind);
    mesh(sphere, "#e0e4d4", [-.35, 2.42, 0], [.1, .06, .1], station);
    mesh(sphere, "#e0e4d4", [.35, 2.42, 0], [.1, .06, .1], station);
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const onPointer = (event) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1);
      raycaster.setFromCamera(pointer, camera);
      setHover(raycaster.intersectObjects(sensors)[0]?.object.userData.label || "");
    };
    renderer.domElement.addEventListener("pointermove", onPointer);
    const onLeave = () => setHover("");
    renderer.domElement.addEventListener("pointerleave", onLeave);
    const lost = (event) => { event.preventDefault(); onUnavailable(); };
    renderer.domElement.addEventListener("webglcontextlost", lost);
    const draw = () => renderer.render(scene, camera);
    controls.addEventListener("change", draw);
    const resize = new ResizeObserver(() => {
      if (!host.clientWidth) return;
      renderer.setSize(host.clientWidth, host.clientHeight);
      camera.aspect = host.clientWidth / host.clientHeight; camera.updateProjectionMatrix(); draw();
    });
    resize.observe(host);
    let visible = false, frame = 0, last = 0;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const state = { controls, camera, highlights, draw, playing: false };
    runtime.current = state;
    function tick(now) {
      frame = 0;
      if (!visible || document.hidden || !state.playing || reduced.matches) return;
      if (now - last >= 40) { controls.update(.04); draw(); last = now; }
      frame = requestAnimationFrame(tick);
    }
    const sync = () => {
      controls.autoRotate = state.playing && !reduced.matches;
      cancelAnimationFrame(frame); frame = 0;
      if (visible && !document.hidden && controls.autoRotate) frame = requestAnimationFrame(tick);
      draw();
    };
    state.sync = sync;
    const visibility = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); });
    visibility.observe(host); document.addEventListener("visibilitychange", sync); reduced.addEventListener("change", sync);
    return () => {
      runtime.current = null; cancelAnimationFrame(frame);
      resize.disconnect(); visibility.disconnect(); reduced.removeEventListener("change", sync); document.removeEventListener("visibilitychange", sync);
      renderer.domElement.removeEventListener("pointermove", onPointer); renderer.domElement.removeEventListener("pointerleave", onLeave); renderer.domElement.removeEventListener("webglcontextlost", lost);
      controls.removeEventListener("change", draw); controls.dispose();
      box.dispose(); sphere.dispose(); cylinder.dispose(); materials.forEach((m) => m.dispose());
      renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove();
    };
  }, [onUnavailable]);
  useEffect(() => { if (runtime.current) { runtime.current.playing = playing; runtime.current.sync(); } }, [playing]);
  useEffect(() => {
    if (!runtime.current) return;
    Object.entries(runtime.current.highlights).forEach(([key, obj]) => { obj.material = new THREE.MeshStandardMaterial({ color: key === node ? "#e7b45a" : "#9fb697", roughness: .9 }); });
    runtime.current.draw();
    const highlights = Object.values(runtime.current.highlights);
    return () => highlights.forEach((obj) => obj.material.dispose());
  }, [node]);
  const rotate = (direction) => {
    const r = runtime.current; if (!r) return;
    r.camera.position.sub(r.controls.target).applyAxisAngle(new THREE.Vector3(0, 1, 0), direction * .25).add(r.controls.target);
    r.controls.update(); r.draw();
  };
  const zoom = (factor) => {
    const r = runtime.current; if (!r) return;
    const offset = r.camera.position.clone().sub(r.controls.target);
    const distance = Math.min(r.controls.maxDistance, Math.max(r.controls.minDistance, offset.length() * factor));
    r.camera.position.copy(offset.normalize().multiplyScalar(distance).add(r.controls.target));
    r.controls.update(); r.draw();
  };
  return <><div className="mc-farm-canvas" ref={mount} />
    <div className="mc-scene-node-controls" aria-label="Conceptual sensor node selection">{["NODE_01", "NODE_02"].map((id) => <button key={id} type="button" disabled={!allowedNodes.includes(id)} aria-pressed={node === id} onClick={() => onNodeChange(id)}><span />{id}</button>)}</div>
    <div className="mc-scene-toolbar"><button type="button" aria-label="Rotate farm left" onClick={() => rotate(-1)}>↶</button><button type="button" aria-label="Rotate farm right" onClick={() => rotate(1)}>↷</button><button type="button" aria-label="Zoom farm in" onClick={() => zoom(.85)}>+</button><button type="button" aria-label="Zoom farm out" onClick={() => zoom(1.15)}>−</button><button type="button" onClick={() => setPlaying((p) => !p)} aria-pressed={playing}>{playing ? "Pause orbit" : "Orbit slowly"}</button></div>
    <p className="mc-scene-tooltip" role="status">{hover || `${node} · Conceptual air temperature, humidity & soil index sensing`}</p>
  </>;
}
