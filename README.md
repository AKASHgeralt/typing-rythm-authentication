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

## Commands

Run these from the project folder with `(.venv)` active.

| Command | What it does |
|---|---|
| `python app.py` | Start the web application at http://127.0.0.1:5000 |
| `python -m src.features` | Build `data/features.csv` (nine features per attempt) from the raw keystrokes |
| `python -m src.features --set-b` | Also build the optional 85-feature Set B file |
| `python -m src.explore` | Count attempts and plot each feature per participant |
| `python -m src.train` | Nested cross-validation on Session 1, thresholds, final models |
| `python -m src.train --shuffle-check` | Sanity check: with shuffled labels accuracy should be about 20% |
| `python -m src.evaluate` | Final test on Session 2 and impostors. Run once only |
| `pytest` | Run the automated tests |

## Practising with simulated data

`python -m src.simulate` writes SIMULATED data to a separate `sim/` folder. Add
`--workspace sim` to any command above (including `python app.py --workspace sim`)
to use it. The real `data/`, `models/` and `reports/` folders are never touched,
and simulated results must not be reported.

## Folders

| Folder | Contents |
|---|---|
| `templates/`, `static/` | Web pages, CSS and the key-capture script |
| `src/` | Settings, storage, feature extraction, training, evaluation |
| `data/` | Raw keystrokes, features and the authentication log (not in git) |
| `models/` | Trained models and thresholds (not in git; retrain on each machine) |
| `reports/` | Metrics and figures |
| `tests/` | Unit tests |

## Machines

Development, data collection, training and the demo all happen on the same laptop,
using its built-in keyboard (no external keyboard).
