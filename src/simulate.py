"""Create SIMULATED users and typing data for testing the pipeline.

Everything is written to the separate "sim" workspace (sim/data/...), never to
the real data folder. Simulated results must not be reported as findings.

Each simulated person has their own typing style. The owner of a password
types it faster and more consistently than other people, who are typing an
unfamiliar password.

Run:  python -m src.simulate
"""
import argparse
import csv
from datetime import datetime, timedelta

import numpy as np

from src import config, storage, users

SIM_USERS = [  # demo accounts for the simulated workspace only
    ("Sim One", "sim1@example.com", "river@123"),
    ("Sim Two", "sim2@example.com", "stone@1234"),
    ("Sim Three", "sim3@example.com", "cloud@12"),
    ("Sim Four", "sim4@example.com", "maple@1234"),
    ("Sim Five", "sim5@example.com", "ember@123"),
]


class Person:
    def __init__(self, rng):
        self.rng = rng
        self.dwell_base = rng.uniform(80, 130)
        self.gap_base = rng.uniform(150, 240)
        self.dwell_key, self.gap_pair = {}, {}

    def dwell(self, ch):
        return self.dwell_key.setdefault(ch, self.dwell_base + self.rng.normal(0, 15))

    def gap(self, a, b):
        return self.gap_pair.setdefault((a, b), self.gap_base + self.rng.normal(0, 45))

    def type(self, password, own, speed=1.0):
        rng = self.rng
        familiar = 0.92 if own else 1.05         # owners know their password well
        noise = 0.85 if own else 1.0
        keys, t = [], 0.0
        for i, ch in enumerate(password):
            if i > 0:
                t += max(25.0, self.gap(password[i - 1], ch) * familiar * speed
                         + rng.normal(0, 35 * noise))
            d = max(30.0, self.dwell(ch) + rng.normal(0, 14 * noise))
            keys.append({"key_index": i, "press_ms": round(t, 2), "release_ms": round(t + d, 2)})
        return keys


def main():
    parser = argparse.ArgumentParser(description="Write simulated data to the sim workspace.")
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    ws = config.Workspace("sim")
    ws.ensure_dirs()
    for f in (ws.users_file, ws.raw_file):
        if f.exists():
            f.write_text("")
    users.save_users(ws, [])
    for name, email, pw in SIM_USERS:
        users.add_user(ws, name, email, pw)
    passwords = {u["user_id"]: pw for u, (_, _, pw) in zip(users.load_users(ws), SIM_USERS)}
    people = {uid: Person(rng) for uid in passwords}

    attempt_id = 0
    with open(ws.raw_file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=storage.COLUMNS)
        w.writeheader()
        for session in config.SESSIONS:
            when = datetime(2026, 1, 1, 10) + timedelta(days=session - 1)
            for typist in passwords:
                for target, n in storage.plan(ws, typist, session):
                    tid = target["user_id"]
                    for _ in range(n):
                        attempt_id += 1
                        keys = people[typist].type(passwords[tid], own=(tid == typist),
                                                   speed=0.95 if session == 2 else 1.0)
                        for k in keys:
                            w.writerow({"typist_id": typist, "target_id": tid,
                                        "role": "genuine" if tid == typist else "impostor",
                                        "session": session, "attempt_id": attempt_id,
                                        "recorded_at": when.isoformat(timespec="seconds"), **k})
    print(f"Wrote {attempt_id} SIMULATED attempts to {ws.raw_file}")
    print("Simulated accounts (for trying the login page with --workspace sim):")
    for name, email, pw in SIM_USERS:
        print(f"  {email:<20} {pw}")


if __name__ == "__main__":
    main()
