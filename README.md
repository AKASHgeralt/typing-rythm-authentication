# Typing Rhythm Authentication Using Lightweight Machine Learning

Local Flask web application that verifies a claimed participant ID from keystroke
timing, using K-Nearest Neighbors and Random Forest (scikit-learn).

## Setup (Windows)

Requires Python 3.12 from python.org (tick "Add python.exe to PATH" during install).

```
cd %USERPROFILE%\Documents\typing-auth
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in the browser. Stop the server with Ctrl+C.

## How it works

A login page with email and password. Login succeeds only if the password is
correct **and** it is typed with the account owner's rhythm. Each account has its
own models: a nearest-neighbour distance model and a Random Forest. See
`docs/COLLECTION_GUIDE.md` for the data collection plan.

## Commands

Run these from the project folder with `(.venv)` active.

| Command | What it does |
|---|---|
| `python app.py` | Start the web application at http://127.0.0.1:5000 |
| `python -m src.users list` | List registered accounts |
| `python -m src.users add --name NAME --email EMAIL` | Register an account (asks for the password) |
| `python -m src.features` | Build one feature file per account from the raw keystrokes |
| `python -m src.explore` | Count attempts; plot owner vs others per account |
| `python -m src.train` | Nested cross-validation on Session 1, thresholds, final models |
| `python -m src.train --shuffle-check` | Sanity check: with shuffled labels AUC should be about 0.5 |
| `python -m src.evaluate` | Final test on Session 2. Run once only |
| `pytest` | Run the automated tests |

## Practising with simulated data

`python -m src.simulate` creates SIMULATED accounts and data in a separate `sim/`
folder and prints the simulated logins. Add `--workspace sim` to any command above
(including `python app.py --workspace sim`). The real `data/` folder is never
touched, and simulated results must not be reported.

## Folders

| Folder | Contents |
|---|---|
| `templates/`, `static/` | Web pages, CSS and the password key-capture script |
| `src/` | Settings, storage, feature extraction, training, evaluation |
| `data/` | Accounts (hashed passwords), raw keystrokes, features, login log (not in git) |
| `models/` | One model per account and model type, and thresholds (not in git) |
| `reports/` | Metrics and figures |
| `tests/` | Unit tests |

## Machines

Development, data collection, training and the demo all happen on the same laptop,
using its built-in keyboard (no external keyboard).
