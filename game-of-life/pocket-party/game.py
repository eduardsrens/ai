"""Pocket Party: a local, turn-based 3D party board game. Rules live in Python."""

from __future__ import annotations

import math
import random
import time

VERSION = 3

CHEST_SPACES = (7, 21, 35)
CHANCE_SPACES = (5, 14, 23, 32, 44)
CAMPFIRE_SPACES = (11, 26, 41)
BOARD_SIZE = 49
MAX_HP = 20
MAX_ITEMS = 3
CHEST_COST = 20
ALLOWED_ROUNDS = (5, 8, 12)


def _tile_type(index: int) -> str:
    if index == 0:
        return "start"
    if index in CHEST_SPACES:
        return "chest"
    if index in CHANCE_SPACES:
        return "chance"
    if index in CAMPFIRE_SPACES:
        return "campfire"
    if index % 6 == 0:
        return "trap"
    if index % 4 == 0:
        return "payday"
    return "meadow"


TYPES = [_tile_type(i) for i in range(BOARD_SIZE)]

ITEMS = {
    "rocket": {
        "name": "Pocket Rocket",
        "description": "Deal 7 damage to a rival (or pop their shield).",
    },
    "magnet": {
        "name": "Key Magnet",
        "description": "Steal up to 8 keys from a rival.",
    },
    "shield": {
        "name": "Bubble Shield",
        "description": "Block the next rival attack or board trap.",
    },
    "swap": {
        "name": "Switcheroo",
        "description": "Teleport-swap board positions with a rival.",
    },
    "turbo": {
        "name": "Turbo Dice",
        "description": "Roll two dice (2–12 spaces) on this turn.",
    },
}

COLORS = ["#e06d53", "#4c96a8", "#7da657", "#a47bb8"]
MINIS = ["reaction", "memory", "mash", "reflex"]


def new_game() -> dict:
    return {
        "version": VERSION,
        "phase": "setup",
        "players": [],
        "current": 0,
        "round": 1,
        "max_rounds": 8,
        "roll": None,
        "roll_dice": [],
        "rolled": False,
        "used_item": False,
        "turbo": False,
        "pending": None,
        "last_move": None,
        "last_action": None,
        "awards": [],
        "event": {
            "title": "Good friends. Questionable decisions.",
            "text": "Gather 2–4 players on one screen for sunlit mischief and friendly rivalry.",
            "kind": "welcome",
        },
        "history": [],
        "mini": None,
    }


def record(g: dict, title: str, text: str, kind: str = "meadow") -> None:
    g["event"] = {"title": title, "text": text, "kind": kind}
    g["history"].insert(
        0,
        {"title": title, "text": text, "kind": kind, "round": g["round"]},
    )
    g["history"] = g["history"][:100]


def require(g: dict, phase: str) -> None:
    if g["phase"] != phase:
        raise ValueError("That action is not available right now.")


def start(g: dict, names, rounds: int = 8) -> dict:
    require(g, "setup")
    if not isinstance(names, list) or not 2 <= len(names) <= 4:
        raise ValueError("Choose 2 to 4 players.")
    if not isinstance(rounds, int) or isinstance(rounds, bool) or rounds not in ALLOWED_ROUNDS:
        raise ValueError("Choose 5, 8, or 12 rounds.")
    clean = [str(n).strip()[:18] for n in names]
    if any(not n for n in clean) or len({n.lower() for n in clean}) != len(clean):
        raise ValueError("Each player needs a different non-empty name.")
    g["max_rounds"] = rounds
    g["players"] = [
        {
            "id": i,
            "name": name,
            "color": COLORS[i],
            "position": 0,
            "hp": MAX_HP,
            "keys": 10,
            "trophies": 0,
            "items": ["rocket", "shield"],
            "shield": False,
            "stats": {
                "damage_dealt": 0,
                "keys_stolen": 0,
                "chests_bought": 0,
                "minigames_won": 0,
                "traps_hit": 0,
                "spaces_moved": 0,
            },
        }
        for i, name in enumerate(clean)
    ]
    g["phase"] = "handoff"
    record(
        g,
        "Let the friendly chaos begin.",
        f"{len(clean)} friends. {rounds} rounds. Most trophies wins.",
        "welcome",
    )
    return g


def _build_reflex_events(rng: random.Random) -> list[dict]:
    slots = [rng.randrange(9) for _ in range(14)]
    # Ensure consecutive targets land on fresh slots when possible.
    for i in range(1, len(slots)):
        if slots[i] == slots[i - 1]:
            slots[i] = (slots[i] + rng.randint(1, 8)) % 9
    kinds = ["star"] * 10 + ["bomb"] * 4
    rng.shuffle(kinds)
    events = []
    for i in range(14):
        at = 240 + i * 380
        events.append(
            {
                "id": i,
                "slot": slots[i],
                "kind": kinds[i],
                "at": at,
                "ttl": 1050 if kinds[i] == "star" else 950,
            }
        )
    return events


def ready(g: dict) -> dict:
    if g["phase"] == "handoff":
        g["phase"] = "playing"
    elif g["phase"] == "minigame_handoff":
        g["phase"] = "minigame"
        g["mini"]["started"] = time.time()
        rng = random.SystemRandom()
        if g["mini"]["kind"] == "memory":
            gems = [rng.choice(["gold", "green", "blue", "coral"]) for _ in range(20)]
            if gems.count("gold") < 2:
                gems[0] = "gold"
                gems[7] = "gold"
            g["mini"]["gems"] = gems
        elif g["mini"]["kind"] == "reflex":
            g["mini"]["events"] = _build_reflex_events(rng)
    else:
        raise ValueError("No handoff is waiting.")
    return g


def player(g: dict) -> dict:
    return g["players"][g["current"]]


def _apply_damage(p: dict, amount: int, attacker: dict | None = None) -> tuple[str, bool, bool]:
    """Apply damage to p. Returns (message, knocked_out, shield_broken)."""
    if p["shield"]:
        p["shield"] = False
        return (f"{p['name']}’s bubble shield absorbed the hit!", False, True)
    p["hp"] = max(0, p["hp"] - amount)
    if attacker is not None:
        attacker["stats"]["damage_dealt"] += amount
    if p["hp"] == 0:
        lost = min(p["keys"], 8)
        p["keys"] -= lost
        p["position"] = 0
        p["hp"] = MAX_HP
        return (
            f"{p['name']} got knocked out! Lost {lost} keys and respawned at the portal with full health.",
            True,
            False,
        )
    return (f"{p['name']} took {amount} damage. {p['hp']} HP left.", False, False)


def spin(g: dict, rng=None) -> dict:
    require(g, "playing")
    if g["rolled"] or g["pending"]:
        raise ValueError("Finish this turn before rolling again.")
    rng = rng or random.SystemRandom()
    p = player(g)
    if g.get("turbo"):
        d1 = rng.randint(1, 6)
        d2 = rng.randint(1, 6)
        roll_dice = [d1, d2]
        roll = d1 + d2
    else:
        d1 = rng.randint(1, 6)
        roll_dice = [d1]
        roll = d1

    old = p["position"]
    wrapped = (old + roll) >= BOARD_SIZE
    new_pos = (old + roll) % BOARD_SIZE
    p["position"] = new_pos
    p["stats"]["spaces_moved"] += roll
    g.update(roll=roll, roll_dice=roll_dice, rolled=True, turbo=False)

    kind = TYPES[new_pos]
    knocked_out = False
    shield_broken = False
    reward_item = None

    if kind == "trap":
        p["stats"]["traps_hit"] += 1
        msg, knocked_out, shield_broken = _apply_damage(p, 4)
        record(g, "A very unfriendly shortcut.", msg, "trap")
    elif kind == "campfire":
        healed = min(6, MAX_HP - p["hp"])
        p["hp"] += healed
        if healed > 0:
            record(
                g,
                "A cozy campfire rest.",
                f"{p['name']} recovered {healed} HP by the campfire.",
                "campfire",
            )
        else:
            p["keys"] += 2
            record(
                g,
                "Already feeling great.",
                f"{p['name']} was at full health and picked up 2 spare keys by the campfire.",
                "campfire",
            )
    elif kind == "chance":
        item = rng.choice(list(ITEMS))
        if len(p["items"]) < MAX_ITEMS:
            p["items"].append(item)
            reward_item = item
            record(
                g,
                "Something up your sleeve.",
                f"{p['name']} found a {ITEMS[item]['name'].lower()}!",
                "chance",
            )
        else:
            p["keys"] += 5
            record(
                g,
                "Pockets full. Lucky you.",
                f"{p['name']} found 5 keys instead of an extra item.",
                "chance",
            )
    else:
        keys = 8 if kind == "payday" else 3
        p["keys"] += keys
        title = "A hidden key stash!" if kind == "payday" else "A little pocket money."
        record(g, title, f"{p['name']} collected {keys} keys.", "payday" if kind == "payday" else "meadow")

    passed_chest = any((old + step) % BOARD_SIZE in CHEST_SPACES for step in range(1, roll + 1))
    if passed_chest and not knocked_out:
        g["pending"] = {
            "kind": "chest",
            "title": "A trophy with your name on it.",
            "text": f"You passed a trophy shrine. Trade {CHEST_COST} keys for a shiny trophy?",
            "options": [
                {
                    "id": "buy",
                    "label": "Claim a trophy",
                    "detail": f"{CHEST_COST} keys → 1 trophy",
                    "disabled": p["keys"] < CHEST_COST,
                },
                {
                    "id": "skip",
                    "label": "Keep your keys",
                    "detail": "Save them for the next shrine",
                },
            ],
        }

    g["last_move"] = {
        "player": g["current"],
        "from": old,
        "to": new_pos,
        "roll": roll,
        "dice": roll_dice,
        "wrapped": wrapped,
        "landed_kind": kind,
        "knocked_out": knocked_out,
        "shield_broken": shield_broken,
        "reward_item": reward_item,
    }
    return g


def choose(g: dict, option: str) -> dict:
    require(g, "playing")
    if not g["pending"] or option not in ("buy", "skip"):
        raise ValueError("No such choice is waiting.")
    p = player(g)
    if option == "buy":
        if p["keys"] < CHEST_COST:
            raise ValueError(f"You need {CHEST_COST} keys for a trophy.")
        p["keys"] -= CHEST_COST
        p["trophies"] += 1
        p["stats"]["chests_bought"] += 1
        record(
            g,
            "A shiny little victory.",
            f"{p['name']} traded {CHEST_COST} keys for a trophy!",
            "chest",
        )
    g["pending"] = None
    return g


def use_item(g: dict, item: str, target=None) -> dict:
    require(g, "playing")
    p = player(g)
    if g["used_item"] or g["rolled"]:
        raise ValueError("Use one item before you roll.")
    if item not in p["items"]:
        raise ValueError("That item is not in your pocket.")

    blocked = False
    knocked_out = False
    stolen = 0
    if item == "shield":
        if p["shield"]:
            raise ValueError("Your shield is already active.")
        p["shield"] = True
        text = f"{p['name']} is shielded against the next attack or trap."
    elif item == "turbo":
        if g.get("turbo"):
            raise ValueError("Turbo Dice are already primed for this roll.")
        g["turbo"] = True
        text = f"{p['name']} primed Turbo Dice — next roll throws two dice!"
    else:
        if (
            not isinstance(target, int)
            or isinstance(target, bool)
            or target == g["current"]
            or not 0 <= target < len(g["players"])
        ):
            raise ValueError("Choose another player as your target.")
        t = g["players"][target]
        if item == "rocket":
            text, knocked_out, blocked = _apply_damage(t, 7, attacker=p)
        elif item == "magnet":
            if t["shield"]:
                t["shield"] = False
                blocked = True
                text = f"{t['name']} blocked the magnet with a shield!"
            else:
                stolen = min(8, t["keys"])
                t["keys"] -= stolen
                p["keys"] += stolen
                p["stats"]["keys_stolen"] += stolen
                text = f"{p['name']} stole {stolen} keys from {t['name']}!"
        elif item == "swap":
            if t["shield"]:
                t["shield"] = False
                blocked = True
                text = f"{t['name']} blocked the switcheroo!"
            else:
                p["position"], t["position"] = t["position"], p["position"]
                text = f"{p['name']} swapped places with {t['name']}!"

    p["items"].remove(item)
    g["used_item"] = True
    g["last_action"] = {
        "player": g["current"],
        "item": item,
        "target": target,
        "blocked": blocked,
        "knocked_out": knocked_out,
        "stolen": stolen,
    }
    record(g, ITEMS[item]["name"] + "!", text, "chance")
    return g


def end_turn(g: dict) -> dict:
    require(g, "playing")
    if not g["rolled"] or g["pending"]:
        raise ValueError("Roll and finish your choices first.")
    g.update(rolled=False, used_item=False, roll=None, roll_dice=[], turbo=False)
    if g["current"] + 1 < len(g["players"]):
        g["current"] += 1
        g["phase"] = "handoff"
    else:
        g["phase"] = "minigame_handoff"
        g["mini"] = {
            "kind": MINIS[(g["round"] - 1) % len(MINIS)],
            "index": 0,
            "scores": [],
            "gems": None,
            "events": None,
            "started": None,
        }
    return g


def _compute_awards(players: list[dict]) -> list[dict]:
    awards = []
    specs = [
        ("Trophy Titan", "Most trophies claimed", lambda p: (p["trophies"], p["keys"])),
        ("Key Bandit", "Most keys stolen with magnets", lambda p: (p["stats"]["keys_stolen"], 0)),
        ("Minigame Ace", "Most minigame wins", lambda p: (p["stats"]["minigames_won"], 0)),
        ("Chaos Engineer", "Most rocket damage dealt", lambda p: (p["stats"]["damage_dealt"], 0)),
        ("Globe Trotter", "Most spaces traveled", lambda p: (p["stats"]["spaces_moved"], 0)),
    ]
    for title, subtitle, key_fn in specs:
        best_val = max(key_fn(p) for p in players)
        if best_val[0] <= 0:
            continue
        winners = [p["name"] for p in players if key_fn(p) == best_val]
        awards.append(
            {
                "title": title,
                "subtitle": subtitle,
                "winners": winners,
                "value": best_val[0],
            }
        )
    return awards[:4]


def minigame(g: dict, body: dict) -> dict:
    require(g, "minigame")
    m = g["mini"]
    idx = m["index"]
    if m["kind"] == "reaction":
        elapsed = float(body.get("elapsed", 0))
        if not 0 <= elapsed <= 10000:
            raise ValueError("Try again within ten seconds.")
        position = (math.sin(elapsed / 1000 * 3.4 - math.pi / 2) + 1) / 2
        score = round(100 * (1 - abs(position - 0.5) * 2))
    elif m["kind"] == "memory":
        answer = int(body.get("answer", -1))
        if not 0 <= answer <= 20:
            raise ValueError("Enter a number from 0 to 20.")
        count = m["gems"].count("gold")
        score = max(0, 100 - abs(answer - count) * 25)
    elif m["kind"] == "reflex":
        if time.time() - m["started"] < 5.2:
            raise ValueError("The six-second Star Snatch is still running.")
        hits = body.get("hits", [])
        if not isinstance(hits, list) or len(hits) > 20:
            raise ValueError("Invalid hit list.")
        event_map = {e["id"]: e for e in (m.get("events") or [])}
        seen = set()
        raw_score = 0
        for eid in hits:
            if not isinstance(eid, int) or isinstance(eid, bool) or eid not in event_map or eid in seen:
                raise ValueError("Invalid hit target.")
            seen.add(eid)
            raw_score += 10 if event_map[eid]["kind"] == "star" else -10
        score = max(0, min(100, raw_score))
    else:
        taps = int(body.get("taps", 0))
        if not 0 <= taps <= 100:
            raise ValueError("Invalid tap count.")
        if time.time() - m["started"] < 4.5:
            raise ValueError("The five-second sprint is still running.")
        score = min(100, taps * 2)

    m["scores"].append({"player": idx, "score": score})
    m["index"] += 1
    if m["index"] < len(g["players"]):
        g["phase"] = "minigame_handoff"
    else:
        scores = sorted(m["scores"], key=lambda x: (-x["score"], x["player"]))
        best = scores[0]["score"]
        winners = []
        rewards = [10, 7, 4, 2]
        for rank, result in enumerate(scores):
            p = g["players"][result["player"]]
            p["keys"] += rewards[rank]
            if result["score"] == best:
                p["trophies"] += 1
                p["stats"]["minigames_won"] += 1
                winners.append(p["name"])
        record(
            g,
            "A round of applause.",
            " & ".join(winners) + " won the minigame and earned a trophy! Everyone received keys.",
            "chest",
        )
        if g["round"] == g["max_rounds"]:
            g["phase"] = "finished"
            g["awards"] = _compute_awards(g["players"])
        else:
            g["phase"] = "round_results"
    return g


def next_round(g: dict) -> dict:
    require(g, "round_results")
    g["round"] += 1
    g["current"] = 0
    g["phase"] = "handoff"
    g["mini"] = None
    return g
