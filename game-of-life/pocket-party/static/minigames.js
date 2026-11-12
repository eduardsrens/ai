/**
 * Interactive, animated skill minigames for Pocket Party.
 * Server validates every score submission.
 */

export const MINI_INFO = {
  reaction: [
    "Sweet Spot",
    "Stop the glowing spark right in the golden center. One shot—make it shine!",
  ],
  memory: [
    "Gem Scramble",
    "Count every GOLD crystal in 3 seconds before the velvet tray flips closed.",
  ],
  mash: [
    "Pocket Rush",
    "Charge the crystal core! Tap or press Space as fast as you can for 5 seconds.",
  ],
  reflex: [
    "Star Snatch",
    "Tap the popping golden stars (+10) across the meadow—and dodge coral bombs (−10)!",
  ],
};

function el(tag, cls = "", text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function launchMinigame({ game, dialog, audio, onSubmit }) {
  const m = game.mini;
  const p = game.players[m.index];
  const label = dialog.querySelector("#mini-label");
  const title = dialog.querySelector("#mini-title");
  const instructions = dialog.querySelector("#mini-instructions");
  const stage = dialog.querySelector("#mini-stage");
  const controls = dialog.querySelector("#mini-controls");

  label.textContent = `${p.name.toUpperCase()} · ROUND ${game.round}`;
  label.style.setProperty("--player-color", p.color);
  title.textContent = MINI_INFO[m.kind][0];
  instructions.textContent = MINI_INFO[m.kind][1];
  stage.replaceChildren();
  controls.replaceChildren();

  if (!dialog.open) dialog.showModal();

  let cleaned = false;
  let cleanupFn = () => {};
  const cleanup = () => {
    if (cleaned) return;
    cleaned = true;
    cleanupFn();
  };

  if (m.kind === "reaction") {
    const wrap = el("div", "mini-reaction-wrap");
    const bar = el("div", "mini-bar");
    const zoneOuter = el("div", "mini-zone-outer");
    const zoneInner = el("div", "mini-target");
    const trail = el("div", "mini-trail");
    const cursor = el("div", "mini-cursor");
    const readout = el("div", "mini-callout", "Watch the rhythm…");
    bar.append(zoneOuter, zoneInner, trail, cursor);
    wrap.append(bar, readout);
    stage.append(wrap);

    const start = performance.now();
    let raf = 0;
    let done = false;

    const frame = () => {
      const elapsed = performance.now() - start;
      const x = (Math.sin((elapsed / 1000) * 3.4 - Math.PI / 2) + 1) / 2;
      cursor.style.left = `calc(${x * 100}% - 5px)`;
      trail.style.left = `${Math.max(0, x * 100 - 8)}%`;
      trail.style.width = "16%";
      if (!done) raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    const stop = () => {
      if (done) return;
      done = true;
      cancelAnimationFrame(raf);
      const elapsed = Math.min(10000, performance.now() - start);
      const pos = (Math.sin((elapsed / 1000) * 3.4 - Math.PI / 2) + 1) / 2;
      const previewScore = Math.round(100 * (1 - Math.abs(pos - 0.5) * 2));
      bar.classList.add("locked");
      readout.textContent =
        previewScore >= 90
          ? `BULLSEYE! ${previewScore} pts`
          : previewScore >= 65
            ? `SHARP! ${previewScore} pts`
            : `${previewScore} pts`;
      readout.classList.add("pop");
      if (previewScore >= 75) audio?.trophy();
      else audio?.click();
      stopBtn.disabled = true;
      const submitTimer = setTimeout(() => {
        cleanup();
        onSubmit({ elapsed });
      }, 620);
      cleanupFn = () => {
        clearTimeout(submitTimer);
        cancelAnimationFrame(raf);
        document.removeEventListener("keydown", onKey);
      };
    };

    const stopBtn = el("button", "primary-button mini-action-btn", "STOP! · Space");
    stopBtn.type = "button";
    stopBtn.onclick = stop;
    controls.append(stopBtn);

    const onKey = (e) => {
      if (e.code === "Space" && !e.repeat) {
        e.preventDefault();
        stop();
      }
    };
    document.addEventListener("keydown", onKey);
    const maxTimer = setTimeout(stop, 9500);
    cleanupFn = () => {
      cancelAnimationFrame(raf);
      clearTimeout(maxTimer);
      document.removeEventListener("keydown", onKey);
    };
  } else if (m.kind === "memory") {
    const grid = el("div", "gem-grid");
    (m.gems || []).forEach((c, idx) => {
      const gem = el("div", `gem ${c}`);
      gem.style.animationDelay = `${(idx % 5) * 70}ms`;
      gem.innerHTML = `<svg viewBox="0 0 36 36" aria-hidden="true"><polygon points="18,2 33,13 27,33 9,33 3,13" class="gem-body"/><polygon points="18,2 25,13 18,22 11,13" class="gem-facet"/></svg>`;
      grid.append(gem);
    });
    const countdown = el("div", "mini-ring-timer");
    countdown.innerHTML = `<svg viewBox="0 0 60 60"><circle cx="30" cy="30" r="24" class="ring-bg"/><circle cx="30" cy="30" r="24" class="ring-fg"/></svg><span>3</span>`;
    stage.append(grid);
    controls.append(countdown);

    let secondsLeft = 3;
    audio?.tick();
    const interval = setInterval(() => {
      secondsLeft -= 1;
      const span = countdown.querySelector("span");
      if (span) span.textContent = String(Math.max(0, secondsLeft));
      if (secondsLeft > 0) audio?.tick();
    }, 1000);

    const revealTimeout = setTimeout(() => {
      clearInterval(interval);
      audio?.chime();
      instructions.textContent = "How many GOLD crystals were on the tray?";
      const hidden = el("div", "mini-mystery-card");
      hidden.innerHTML = `<span class="mystery-gem">◆</span><p>Pick your answer below</p>`;
      stage.replaceChildren(hidden);
      controls.replaceChildren();

      const keypad = el("div", "gem-keypad");
      for (let n = 0; n <= 20; n++) {
        const key = el("button", "gem-num-btn", String(n));
        key.type = "button";
        key.onclick = () => {
          audio?.click();
          cleanup();
          onSubmit({ answer: n });
        };
        keypad.append(key);
      }
      controls.append(keypad);
    }, 3000);

    cleanupFn = () => {
      clearInterval(interval);
      clearTimeout(revealTimeout);
    };
  } else if (m.kind === "reflex") {
    const hud = el("div", "mini-reflex-hud");
    const timer = el("div", "mini-time", "6.0s");
    const liveScore = el("div", "mini-callout", "0 pts");
    hud.append(timer, liveScore);

    const pad = el("div", "reflex-grid");
    const cells = [];
    for (let i = 0; i < 9; i++) {
      const cell = el("button", "reflex-cell");
      cell.type = "button";
      cell.setAttribute("aria-label", `Meadow pad ${i + 1}`);
      cells.push(cell);
      pad.append(cell);
    }
    stage.append(hud, pad);
    controls.append(el("p", "mini-subnote", "Tap stars quickly! Keyboard 1–9 also works."));

    const events = m.events || [];
    const hits = new Set();
    let score = 0;
    let finished = false;
    const start = performance.now();
    const activeBySlot = new Map();

    const triggerHit = (slot) => {
      if (finished) return;
      const active = activeBySlot.get(slot);
      if (!active || hits.has(active.id)) return;
      hits.add(active.id);
      activeBySlot.delete(slot);
      const cell = cells[slot];
      cell.classList.remove("is-star", "is-bomb");
      if (active.kind === "star") {
        score = Math.min(100, score + 10);
        cell.classList.add("hit-star");
        audio?.keys();
      } else {
        score = Math.max(0, score - 10);
        cell.classList.add("hit-bomb");
        audio?.bomb();
      }
      liveScore.textContent = `${score} pts`;
      setTimeout(() => cell.classList.remove("hit-star", "hit-bomb"), 260);
    };

    cells.forEach((cell, idx) => {
      cell.onpointerdown = (e) => {
        e.preventDefault();
        triggerHit(idx);
      };
    });

    const onKey = (e) => {
      const num = Number(e.key);
      if (num >= 1 && num <= 9) {
        e.preventDefault();
        triggerHit(num - 1);
      }
    };
    document.addEventListener("keydown", onKey);

    const timers = [];
    events.forEach((ev) => {
      const showTimer = setTimeout(() => {
        if (finished) return;
        const cell = cells[ev.slot];
        activeBySlot.set(ev.slot, ev);
        cell.classList.remove("is-star", "is-bomb");
        cell.classList.add(ev.kind === "star" ? "is-star" : "is-bomb");
        cell.innerHTML =
          ev.kind === "star"
            ? `<span class="reflex-icon star">★</span>`
            : `<span class="reflex-icon bomb">✹</span>`;
      }, ev.at);
      const hideTimer = setTimeout(() => {
        const cur = activeBySlot.get(ev.slot);
        if (cur && cur.id === ev.id) {
          activeBySlot.delete(ev.slot);
          cells[ev.slot].classList.remove("is-star", "is-bomb");
          cells[ev.slot].replaceChildren();
        }
      }, ev.at + ev.ttl);
      timers.push(showTimer, hideTimer);
    });

    const tickInterval = setInterval(() => {
      const rem = Math.max(0, 6 - (performance.now() - start) / 1000);
      timer.textContent = `${rem.toFixed(1)}s`;
    }, 50);

    const finishTimer = setTimeout(() => {
      finished = true;
      cleanup();
      onSubmit({ hits: Array.from(hits) });
    }, 6050);

    cleanupFn = () => {
      clearInterval(tickInterval);
      clearTimeout(finishTimer);
      timers.forEach((t) => clearTimeout(t));
      document.removeEventListener("keydown", onKey);
    };
  } else {
    // Pocket Rush (mash)
    let taps = 0;
    let done = false;
    const timer = el("div", "mini-time", "5.0s");
    const scoreEl = el("div", "mini-score", "0");
    const meterWrap = el("div", "rush-meter-track");
    const meterFill = el("div", "rush-meter-fill");
    meterWrap.append(meterFill);
    stage.append(timer, scoreEl, meterWrap);

    const mashBtn = el("button", "mash-button");
    mashBtn.type = "button";
    mashBtn.innerHTML = `<span>TAP! · Space</span><small>Charge the core</small>`;
    controls.append(mashBtn);

    const tap = () => {
      if (done) return;
      taps = Math.min(100, taps + 1);
      scoreEl.textContent = String(taps);
      meterFill.style.width = `${Math.min(100, taps * 2)}%`;
      mashBtn.classList.remove("pulse");
      void mashBtn.offsetWidth;
      mashBtn.classList.add("pulse");
      audio?.step(taps);
    };

    mashBtn.onpointerdown = (e) => {
      e.preventDefault();
      tap();
    };
    const onKey = (e) => {
      if (e.code === "Space") {
        e.preventDefault();
        if (!e.repeat) tap();
      }
    };
    document.addEventListener("keydown", onKey);

    const start = performance.now();
    const interval = setInterval(() => {
      const rem = Math.max(0, 5 - (performance.now() - start) / 1000);
      timer.textContent = `${rem.toFixed(1)}s`;
    }, 50);

    const finishTimer = setTimeout(() => {
      done = true;
      mashBtn.disabled = true;
      cleanup();
      onSubmit({ taps });
    }, 5050);

    cleanupFn = () => {
      clearInterval(interval);
      clearTimeout(finishTimer);
      document.removeEventListener("keydown", onKey);
    };
  }

  return cleanup;
}
