import { PartyAudio } from "./audio.js";
import { launchMinigame, MINI_INFO } from "./minigames.js";
import { PartyWorld } from "./scene.js";

const $ = (s) => document.querySelector(s);
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const PLAYER_COLORS = ["#e06d53", "#4c96a8", "#7da657", "#a47bb8"];
const DEFAULT_NAMES = ["Sunny", "River", "Clover", "Plum"];

const audio = new PartyAudio();

let game = null;
let world = null;
let itemTypes = {};
let busy = false;
let selectedItem = null;
let selectedCount = 4;
let selectedRounds = 8;
let actionCamEnabled = !reduceMotion;
let miniCleanup = () => {};
let miniActive = false;
let prevKeys = null;

function el(tag, cls = "", text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

function toast(text) {
  const node = $("#toast");
  node.textContent = text;
  node.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => node.classList.remove("show"), 3200);
}

async function api(action = "", body = {}) {
  const res = await fetch(
    action ? `/api/${action}` : "/api/game",
    action
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : undefined
  );
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Please try again.");
  return data;
}

function addButton(parent, label, fn, cls = "primary-button") {
  const b = el("button", cls, label);
  b.type = "button";
  b.onclick = fn;
  parent.append(b);
  return b;
}

function setHeading(title, text) {
  $("#action-content").replaceChildren(el("h2", "", title), el("p", "", text));
}

function saveSetupNames() {
  document.querySelectorAll(".setup-name").forEach((input) => {
    DEFAULT_NAMES[Number(input.dataset.index)] = input.value;
  });
}

function updateDeltaBadge(p) {
  const badge = $("#delta-badge");
  if (!p || !badge) return;
  if (prevKeys !== null && p.keys !== prevKeys) {
    const diff = p.keys - prevKeys;
    badge.textContent = diff > 0 ? `+${diff} ◆` : `${diff} ◆`;
    badge.classList.add("bump");
    clearTimeout(updateDeltaBadge._timer);
    updateDeltaBadge._timer = setTimeout(() => {
      badge.classList.remove("bump");
      badge.textContent = "◆";
    }, 1500);
  } else {
    badge.textContent = "◆";
  }
  prevKeys = p.keys;
}

function renderScoreboard() {
  const sb = $("#scoreboard");
  sb.replaceChildren();
  for (const x of game.players) {
    const isActive = x.id === game.current && game.phase !== "setup" && game.phase !== "finished";
    const row = el("div", `score-row${isActive ? " active" : ""}`);

    const avatar = el("span", "score-avatar", x.shield ? "◉" : "✳");
    avatar.style.background = x.color;

    const nameWrap = el("div", "score-name-wrap");
    nameWrap.append(el("span", "score-name", x.name));
    const hpBar = el("div", "score-hp-bar");
    const hpFill = el("div", `score-hp-fill${x.hp <= 7 ? " low" : ""}`);
    hpFill.style.width = `${Math.max(0, Math.min(100, (x.hp / 20) * 100))}%`;
    hpBar.append(hpFill);
    nameWrap.append(hpBar);

    row.append(
      avatar,
      nameWrap,
      el("span", "score-trophy", `★ ${x.trophies}`),
      el("span", "score-keys", `◆ ${x.keys}`)
    );
    sb.append(row);
  }
}

function renderInventory(p) {
  const buttons = $("#action-buttons");
  const inv = el("div", "inventory");
  const icons = { rocket: "🚀", shield: "◉", magnet: "◆", swap: "⇄", turbo: "2d6" };

  p.items.forEach((item) => {
    const meta = itemTypes[item];
    if (!meta) return;
    const isSelected = selectedItem === item;
    const b = addButton(
      inv,
      `${icons[item] || "✧"} ${meta.name}`,
      () => {
        audio.click();
        if (item === "shield" || item === "turbo") {
          mutate("item", { item });
        } else {
          selectedItem = isSelected ? null : item;
          render();
        }
      },
      `item-button${isSelected ? " selected" : ""}`
    );
    b.disabled = game.used_item || busy;
    b.title = meta.description;
  });
  buttons.append(inv);

  if (selectedItem && !game.used_item && itemTypes[selectedItem]) {
    const panel = el("div", "target-panel", `Pick a rival: ${itemTypes[selectedItem].description}`);
    const targets = el("div", "target-options");
    for (const t of game.players.filter((x) => x.id !== p.id)) {
      addButton(targets, t.name, () => {
        audio.click();
        mutate("item", { item: selectedItem, target: t.id });
      });
    }
    addButton(targets, "Cancel", () => {
      selectedItem = null;
      render();
    });
    panel.append(targets);
    buttons.append(panel);
  }
}

function render() {
  if (!game) return;
  const setup = game.phase === "setup";
  const p = game.players[game.current];

  $("#turn").textContent = `ROUND ${String(game.round).padStart(2, "0")} / ${String(game.max_rounds).padStart(2, "0")}`;
  $("#player-card").hidden = setup;

  renderScoreboard();

  if (p) {
    $("#active-name").textContent = p.name;
    $("#player-avatar").style.color = p.color;
    $("#player-dot").style.background = p.color;
    $("#player-status").textContent =
      game.phase === "finished"
        ? "What an island adventure!"
        : game.turbo
          ? "Turbo Dice primed · Rolling 2d6!"
          : p.shield
            ? "Bubble shield active · Protected"
            : "Ready for sunlit mischief";
    $("#keys-count").textContent = `${p.keys} keys`;
    updateDeltaBadge(p);
    $("#hp-count").textContent = `${p.hp} / 20`;
    $("#hp-count").classList.toggle("health-low", p.hp <= 7);
    $("#trophies-count").textContent = `★ ${p.trophies}`;
    $("#items-count").textContent = `${p.items.length} / 3`;
    $("#progress").style.width = `${(game.round / game.max_rounds) * 100}%`;
  }

  $("#event-title").textContent = game.event.title;
  $("#event-text").textContent = game.event.text;
  const eventIcons = {
    welcome: "☀",
    meadow: "✿",
    chance: "✧",
    chest: "★",
    campfire: "♥",
    trap: "!",
    payday: "◆",
  };
  $("#moment-icon").textContent = eventIcons[game.event.kind] || "✳";

  $("#action-content").replaceChildren();
  const buttons = $("#action-buttons");
  buttons.className = "";
  buttons.replaceChildren();
  $("#space-label").textContent = p ? `SPACE ${String(p.position).padStart(2, "0")} / 48` : "2–4 PLAYERS";

  if (setup) {
    $("#action-eyebrow").textContent = "GATHER YOUR PEOPLE";
    setHeading("Who’s in the party?", "One device. Two to four friends. Sunlit chaos across the island.");

    const form = el("div", "setup-form");
    const counts = el("div", "setup-players");
    for (let n = 2; n <= 4; n++) {
      addButton(
        counts,
        `${n} players`,
        () => {
          audio.click();
          saveSetupNames();
          selectedCount = n;
          render();
        },
        `count-button${n === selectedCount ? " selected" : ""}`
      );
    }

    const roundsBar = el("div", "setup-rounds");
    for (const r of [5, 8, 12]) {
      addButton(
        roundsBar,
        `${r} rounds`,
        () => {
          audio.click();
          saveSetupNames();
          selectedRounds = r;
          render();
        },
        `count-button${r === selectedRounds ? " selected" : ""}`
      );
    }

    form.append(counts, roundsBar);

    for (let i = 0; i < selectedCount; i++) {
      const row = el("label", "name-row");
      const dot = el("i");
      dot.style.background = PLAYER_COLORS[i];
      const input = el("input", "setup-name");
      input.value = DEFAULT_NAMES[i];
      input.maxLength = 18;
      input.setAttribute("aria-label", `Player ${i + 1} name`);
      input.dataset.index = String(i);
      row.append(dot, input);
      form.append(row);
    }

    addButton(form, "Start the party  →", () => {
      audio.click();
      saveSetupNames();
      prevKeys = null;
      mutate("start", { names: DEFAULT_NAMES.slice(0, selectedCount), rounds: selectedRounds });
    });
    buttons.append(form);
    $("#action-note").textContent = "Pass the device when prompted. Progress saves automatically.";
  } else if (game.phase === "finished") {
    $("#action-eyebrow").textContent = "THE BRAGGING RIGHTS";
    const ranked = [...game.players].sort((a, b) => b.trophies - a.trophies || b.keys - a.keys);
    const best = ranked[0];
    const winners = ranked.filter((x) => x.trophies === best.trophies && x.keys === best.keys);
    setHeading(
      `${winners.map((x) => x.name).join(" & ")} ${winners.length > 1 ? "win!" : "wins!"}`,
      `${game.max_rounds} rounds complete. Most trophies wins; keys break ties.`
    );
    $("#action-content h2").classList.add("winner-title");

    const list = el("div", "round-results");
    for (const x of ranked) {
      const row = el("div", "round-result");
      row.append(el("b", "", x.name), el("span", "", `${x.trophies} ★ · ${x.keys} ◆`));
      list.append(row);
    }
    buttons.append(list);

    if (game.awards?.length) {
      const awardsWrap = el("div", "awards-list");
      for (const a of game.awards) {
        const chip = el("div", "award-chip");
        chip.append(el("b", "", `★ ${a.title}`), el("span", "", `${a.winners.join(", ")} — ${a.subtitle}`));
        awardsWrap.append(chip);
      }
      buttons.append(awardsWrap);
    }

    addButton(buttons, "Play another party?  →", () => $("#reset-dialog").showModal());
    $("#action-note").textContent = "Same friends. Fresh rivalries.";
  } else if (game.phase === "round_results") {
    $("#action-eyebrow").textContent = "ROUND COMPLETE";
    setHeading("A little victory lap.", game.event.text);
    const list = el("div", "round-results");
    for (const s of [...game.mini.scores].sort((a, b) => b.score - a.score)) {
      const row = el("div", "round-result");
      row.append(el("b", "", game.players[s.player].name), el("span", "", `${s.score} pts`));
      list.append(row);
    }
    buttons.append(list);
    addButton(buttons, `On to round ${game.round + 1}  →`, () => {
      audio.click();
      mutate("next");
    });
    $("#action-note").textContent = "Top minigame score wins a ★ trophy. Everyone earns keys.";
  } else if (game.pending) {
    $("#action-eyebrow").textContent = "TROPHY SHRINE";
    setHeading(game.pending.title, game.pending.text);
    buttons.className = "route-options";
    for (const o of game.pending.options) {
      const b = addButton(
        buttons,
        "",
        () => {
          audio.click();
          mutate("choice", { option: o.id });
        },
        "route-button"
      );
      const span = el("span");
      span.append(el("b", "", o.label), el("small", "", o.detail));
      b.append(span, el("span", "", "→"));
      b.disabled = o.disabled || busy;
    }
    $("#action-note").textContent = "Trophies decide the champion.";
  } else if (game.phase === "playing") {
    $("#action-eyebrow").textContent = `${p.name.toUpperCase()}’S TURN`;
    if (game.rolled) {
      const diceText = game.roll_dice?.length === 2 ? `(${game.roll_dice.join(" + ")})` : "";
      setHeading(
        `Rolled a ${game.roll}! ${diceText}`,
        "Pass the spotlight to the next troublemaker."
      );
      addButton(
        buttons,
        game.current === game.players.length - 1 ? "Minigame time!  →" : "Finish turn & pass  →",
        () => {
          audio.click();
          mutate("endturn");
        }
      );
      $("#action-note").textContent = "Once everyone moves, all players face a skill minigame.";
    } else {
      setHeading("Make a little trouble.", "Optionally trigger one item, then roll onto the trail.");
      const diceWrap = el("div", "dice-wrap");
      diceWrap.append(
        el("div", "dice", game.turbo ? "2d6" : "✳"),
        el("span", "dice-caption", game.turbo ? "Turbo Dice primed! Rolling 2–12 spaces." : "Use an item before rolling, or throw the 3D die!")
      );
      $("#action-content").append(diceWrap);
      addButton(
        buttons,
        game.turbo ? "Roll Turbo Dice (2d6)  →" : "Roll the dice  →",
        spin,
        `primary-button${game.turbo ? " turbo-ready" : ""}`
      );
      renderInventory(p);
      $("#action-note").textContent = "Hover any board space on the island to inspect it.";
    }
  } else {
    $("#action-eyebrow").textContent = game.phase.startsWith("minigame") ? "MINIGAME TIME" : "PASS THE DEVICE";
    setHeading("Everybody gets a moment.", "Hand over the device to the next player.");
    $("#action-note").textContent = "Fair pass-and-play.";
  }

  if (busy) {
    document.querySelectorAll("#action-buttons button").forEach((b) => {
      b.disabled = true;
    });
  }
  syncHandoff();
}

function syncHandoff() {
  const phase = game.phase;
  const needed = phase === "handoff" || phase === "minigame_handoff";
  const dialog = $("#handoff-dialog");
  if (!needed) {
    if (dialog.open) dialog.close();
    return;
  }
  const isMini = phase === "minigame_handoff";
  const p = game.players[isMini ? game.mini.index : game.current];
  $("#handoff-label").textContent = isMini
    ? `ROUND ${game.round} · MINIGAME`
    : `ROUND ${game.round} · PASS THE DEVICE`;
  $("#handoff-name").textContent = `${p.name}, you’re up!`;
  $("#handoff-avatar").style.background = p.color;
  $("#handoff-text").textContent = isMini
    ? `${MINI_INFO[game.mini.kind][0]}: ${MINI_INFO[game.mini.kind][1]}`
    : "Your turn to use items, roll the 3D dice, and explore the island.";
  $("#ready-button").disabled = busy;
  if (!dialog.open) dialog.showModal();
}

async function mutate(action, body = {}) {
  if (busy) return;
  busy = true;
  selectedItem = null;
  render();
  try {
    const data = await api(action, body);
    const shouldAnimate = world && actionCamEnabled && !reduceMotion && (action === "item" || (action === "choice" && body.option === "buy"));
    if (shouldAnimate) {
      await world.playEvent(data.game, { action, body });
    }
    game = data.game;
    world?.setState(game);
    if (action !== "item" && action !== "choice") audio.chime();
  } catch (err) {
    toast(err.message);
  } finally {
    busy = false;
    render();
    if (game?.phase === "minigame") startMinigame();
  }
}

async function spin() {
  if (busy) return;
  busy = true;
  render();
  const dice = $(".dice");
  dice?.classList.add("rolling");
  const cycle = setInterval(() => {
    if (dice) dice.textContent = String(1 + Math.floor(Math.random() * 6));
  }, 85);

  try {
    const next = (await api("spin")).game;
    clearInterval(cycle);
    if (dice) {
      dice.textContent = String(next.roll);
      dice.classList.remove("rolling");
    }
    if (world && !reduceMotion) {
      await world.rollDice(next.roll_dice || [next.roll]);
      if (actionCamEnabled) {
        await world.moveTo(next);
      } else {
        world.setState(next);
      }
    }
    game = next;
    if (game.last_move?.knocked_out) audio.trap();
  } catch (err) {
    toast(err.message);
    try {
      game = (await api()).game;
      world?.setState(game);
    } catch {
      // Ignore secondary refresh error
    }
  } finally {
    clearInterval(cycle);
    busy = false;
    render();
  }
}

function startMinigame() {
  if (miniActive || !game?.mini) return;
  miniActive = true;
  miniCleanup();
  miniCleanup = launchMinigame({
    game,
    dialog: $("#minigame-dialog"),
    audio,
    onSubmit: submitMini,
  });
}

async function submitMini(body) {
  if (busy) return;
  busy = true;
  miniCleanup();
  $("#mini-controls").replaceChildren(el("p", "", "Tallying your score…"));
  try {
    const data = await api("minigame", body);
    game = data.game;
    miniActive = false;
    $("#minigame-dialog").close();
    if (game.phase === "finished") audio.trophy();
    else audio.chime();
    world?.setState(game);
  } catch (err) {
    toast(err.message);
    miniActive = false;
    $("#minigame-dialog").close();
  } finally {
    busy = false;
    render();
    if (game?.phase === "minigame") startMinigame();
  }
}

// Wire controls
$("#ready-button").onclick = () => {
  audio.click();
  mutate("ready");
};

for (const id of ["#handoff-dialog", "#minigame-dialog"]) {
  $(id).addEventListener("cancel", (e) => e.preventDefault());
}

$("#rules-button").onclick = () => {
  audio.click();
  $("#rules-dialog").showModal();
};

document.querySelectorAll("[data-close]").forEach((btn) => {
  btn.onclick = () => btn.closest("dialog").close();
});

for (const id of ["#rules-dialog", "#journal-dialog", "#reset-dialog"]) {
  $(id).addEventListener("click", (e) => {
    const d = $(id);
    if (e.target === d) {
      const r = d.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) {
        d.close();
      }
    }
  });
}

$("#journal-button").onclick = () => {
  audio.click();
  const list = $("#journal-list");
  list.replaceChildren();
  if (!game.history.length) {
    list.append(el("p", "", "The party hasn’t started yet. Gather your friends!"));
  }
  for (const e of game.history) {
    const row = el("div", "journal-entry");
    const body = el("div");
    body.append(el("b", "", e.title), el("p", "", e.text));
    row.append(el("span", "", `ROUND ${e.round}`), body);
    list.append(row);
  }
  $("#journal-dialog").showModal();
};

$("#new-game").onclick = () => {
  $("#journal-dialog").close();
  $("#reset-dialog").showModal();
};

$("#confirm-reset").onclick = async () => {
  $("#reset-dialog").close();
  miniCleanup();
  miniActive = false;
  prevKeys = null;
  await mutate("reset");
};

$("#sound-button").onclick = () => {
  const next = !audio.enabled;
  audio.setEnabled(next);
  $("#sound-button").classList.toggle("is-muted", !next);
  $("#sound-button").setAttribute("aria-label", next ? "Mute sound" : "Enable sound");
  toast(next ? "Party sound effects on." : "Sound switched off.");
};

$("#cinematic-button").onclick = () => {
  actionCamEnabled = !actionCamEnabled;
  $("#cinematic-dot").classList.toggle("on", actionCamEnabled);
  $("#cinematic-button").setAttribute("aria-pressed", String(actionCamEnabled));
  toast(actionCamEnabled ? "Third-person Action Cam enabled." : "Fast overview mode enabled.");
};

$("#rotate-left").onclick = () => world?.rotate(-1);
$("#rotate-right").onclick = () => world?.rotate(1);
$("#reset-view").onclick = () => {
  world?.reset();
  document.querySelectorAll(".preset-btn").forEach((b) => b.classList.toggle("active", b.dataset.preset === "diorama"));
};

document.querySelectorAll(".preset-btn").forEach((btn) => {
  btn.onclick = () => {
    audio.click();
    world?.setPreset(btn.dataset.preset);
    document.querySelectorAll(".preset-btn").forEach((b) => b.classList.toggle("active", b === btn));
  };
});

// Boot
const tooltip = $("#tile-tooltip");
try {
  const data = await api();
  game = data.game;
  itemTypes = data.items;
  try {
    world = new PartyWorld($("#scene"), data.tiles, {
      audio,
      onTileHover: (info) => {
        if (!info) {
          tooltip.hidden = true;
          return;
        }
        tooltip.textContent = `Space ${String(info.index).padStart(2, "0")} · ${info.label}`;
        tooltip.style.left = `${info.x}px`;
        tooltip.style.top = `${info.y}px`;
        tooltip.hidden = false;
      },
    });
    world.setState(game);
    $("#loading").remove();
  } catch (err) {
    $("#loading").textContent = "WebGL 3D is unavailable here, but all board & minigame controls work!";
    $("#loading").className = "error";
    console.error(err);
  }
  render();
  if (game.phase === "minigame") startMinigame();
} catch (err) {
  $("#loading").textContent = "Unable to reach the game server. Refresh to try again.";
  toast(err.message);
}
