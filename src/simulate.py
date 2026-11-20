"""Create SIMULATED keystroke data for testing the pipeline before real data exists.

The data is written to the separate "sim" workspace (sim/data/...), never to the
real data folder. Results from simulated data must not be reported as findings.

Each simulated person has their own typical hold time and their own rhythm for
every key and key pair, plus random noise. Session 2 is made slightly faster to
imitate practice between sessions.

Run:  python -m src.simulate
"""
import argparse
import csv
from datetime import datetime, timedelta

import numpy as np

from src import config
from src.storage import COLUMNS

SENTENCE = config.SENTENCE


def make_person(rng):
    return {
        "dwell_base": rng.uniform(85, 125),
        "dwell_key": {ch: rng.normal(0, 10) for ch in set(SENTENCE)},
        "dwell_noise": rng.uniform(15, 30),
        "gap_base": rng.uniform(170, 230),
        "gap_pair": rng.normal(0, 30, len(SENTENCE) - 1),
        "gap_noise": rng.uniform(40, 80),
    }


def make_attempt(person, rng, speed=1.0):
    pace = speed * rng.normal(1.0, 0.05)        # whole attempt a bit faster or slower
    press, keys, t = [], [], 0.0
    for i, ch in enumerate(SENTENCE):
        if i > 0:
            gap = (person["gap_base"] + person["gap_pair"][i - 1]) * pace
            t += max(20.0, gap + rng.normal(0, person["gap_noise"]))
        dwell = person["dwell_base"] + person["dwell_key"][ch] + rng.normal(0, person["dwell_noise"])
        dwell = max(30.0, dwell)
        keys.append({"key_index": i, "key": ch,
                     "code": "Space" if ch == " " else "Key" + ch.upper(),
                     "press_ms": round(t, 2), "release_ms": round(t + dwell, 2)})
    return keys


def main():
    parser = argparse.ArgumentParser(description="Write simulated data to the sim workspace.")
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    ws = config.Workspace("sim")
    ws.ensure_dirs()

    day1 = datetime(2026, 1, 1, 10, 0)
    plan = [(pid, "enrolled", s, n) for pid in config.ENROLLED_IDS
            for s, n in config.SESSION_TARGETS["enrolled"].items()]
    plan += [(pid, "impostor", 1, config.SESSION_TARGETS["impostor"][1])
             for pid in config.IMPOSTOR_IDS]

    people = {pid: make_person(rng) for pid in config.ENROLLED_IDS + config.IMPOSTOR_IDS}
    attempt_id = 0
    with open(ws.raw_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        for pid, role, session, n in plan:
            speed = 0.95 if session == 2 else 1.0
            when = day1 + timedelta(days=session - 1)
            for _ in range(n):
                attempt_id += 1
                for k in make_attempt(people[pid], rng, speed):
                    writer.writerow({"participant_id": pid, "role": role, "session": session,
                                     "attempt_id": attempt_id,
                                     "recorded_at": when.isoformat(timespec="seconds"), **k})
    print(f"Wrote {attempt_id} SIMULATED attempts to {ws.raw_file}")


if __name__ == "__main__":
    main()
