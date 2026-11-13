/**
 * Lightweight procedural Web Audio synthesizer for Pocket Party.
 * Zero external audio assets required.
 */
export class PartyAudio {
  constructor() {
    this.enabled = false;
    this.ctx = null;
  }

  setEnabled(on) {
    this.enabled = Boolean(on);
    if (this.enabled) {
      this._ensureContext();
      this.chime();
    }
  }

  _ensureContext() {
    if (!this.ctx) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return null;
      this.ctx = new Ctx();
    }
    if (this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
    return this.ctx;
  }

  _tone({ freq = 440, endFreq = null, type = "sine", delay = 0, duration = 0.16, gain = 0.06 }) {
    if (!this.enabled) return;
    const ctx = this._ensureContext();
    if (!ctx) return;
    try {
      const now = ctx.currentTime + delay;
      const osc = ctx.createOscillator();
      const vol = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, now);
      if (endFreq !== null) {
        osc.frequency.exponentialRampToValueAtTime(Math.max(20, endFreq), now + duration);
      }
      vol.gain.setValueAtTime(0.0001, now);
      vol.gain.linearRampToValueAtTime(gain, now + 0.015);
      vol.gain.exponentialRampToValueAtTime(0.0001, now + duration);
      osc.connect(vol);
      vol.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + duration + 0.03);
    } catch {
      // Ignore blocked audio context before user interaction
    }
  }

  click() {
    this._tone({ freq: 620, endFreq: 420, type: "triangle", duration: 0.055, gain: 0.04 });
  }

  chime() {
    [523.25, 659.25, 783.99].forEach((freq, i) => {
      this._tone({ freq, type: "triangle", delay: i * 0.065, duration: 0.22, gain: 0.045 });
    });
  }

  diceRoll() {
    [0, 0.09, 0.19, 0.3, 0.43].forEach((delay, i) => {
      this._tone({
        freq: 260 + i * 35,
        endFreq: 180,
        type: "triangle",
        delay,
        duration: 0.06,
        gain: 0.045,
      });
    });
  }

  diceLand() {
    this._tone({ freq: 220, endFreq: 95, type: "triangle", duration: 0.16, gain: 0.08 });
    this._tone({ freq: 587, type: "sine", delay: 0.04, duration: 0.22, gain: 0.05 });
  }

  step(index = 0) {
    const scale = [392, 440, 493.88, 523.25, 587.33, 659.25, 783.99];
    const freq = scale[index % scale.length];
    this._tone({ freq, endFreq: freq * 1.05, type: "sine", duration: 0.1, gain: 0.045 });
  }

  keys() {
    [659.25, 880, 1046.5].forEach((freq, i) => {
      this._tone({ freq, type: "sine", delay: i * 0.055, duration: 0.2, gain: 0.045 });
    });
  }

  heal() {
    [440, 554.37, 659.25, 880].forEach((freq, i) => {
      this._tone({ freq, type: "sine", delay: i * 0.07, duration: 0.28, gain: 0.04 });
    });
  }

  trap() {
    this._tone({ freq: 240, endFreq: 85, type: "sawtooth", duration: 0.28, gain: 0.05 });
    this._tone({ freq: 180, endFreq: 70, type: "triangle", delay: 0.08, duration: 0.28, gain: 0.06 });
  }

  trophy() {
    [523.25, 659.25, 783.99, 1046.5].forEach((freq, i) => {
      this._tone({
        freq,
        type: "triangle",
        delay: i * 0.085,
        duration: i === 3 ? 0.55 : 0.22,
        gain: 0.065,
      });
    });
  }

  shield() {
    this._tone({ freq: 330, endFreq: 660, type: "sine", duration: 0.26, gain: 0.055 });
    this._tone({ freq: 660, endFreq: 990, type: "triangle", delay: 0.08, duration: 0.25, gain: 0.04 });
  }

  rocket() {
    this._tone({ freq: 320, endFreq: 860, type: "sawtooth", duration: 0.42, gain: 0.04 });
    this._tone({ freq: 140, endFreq: 55, type: "triangle", delay: 0.48, duration: 0.35, gain: 0.08 });
  }

  magnet() {
    this._tone({ freq: 280, endFreq: 520, type: "sine", duration: 0.35, gain: 0.05 });
    this._tone({ freq: 784, endFreq: 1046, type: "triangle", delay: 0.25, duration: 0.22, gain: 0.045 });
  }

  swap() {
    this._tone({ freq: 587, endFreq: 293, type: "sine", duration: 0.22, gain: 0.05 });
    this._tone({ freq: 293, endFreq: 784, type: "sine", delay: 0.22, duration: 0.26, gain: 0.05 });
  }

  portal() {
    this._tone({ freq: 340, endFreq: 880, type: "sine", duration: 0.34, gain: 0.05 });
    this._tone({ freq: 520, endFreq: 1040, type: "triangle", delay: 0.1, duration: 0.32, gain: 0.035 });
  }

  tick() {
    this._tone({ freq: 740, type: "sine", duration: 0.05, gain: 0.03 });
  }

  bomb() {
    this._tone({ freq: 160, endFreq: 52, type: "sawtooth", duration: 0.3, gain: 0.06 });
  }
}
