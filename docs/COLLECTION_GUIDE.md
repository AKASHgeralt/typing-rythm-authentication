# Data Collection Guide

Everything happens on the **presentation laptop** (the same laptop the project was
built on), using its **built-in keyboard**. Data, training, evaluation and the demo
all use this one machine.

---

## A. The laptop

The project was built on this laptop and is already installed (`.venv`, packages,
36 passing tests). There is nothing to set up. Use the **built-in keyboard** for every
participant and for the demo; do not plug in an external keyboard.

If the project ever has to be installed on another computer, see the README.
Choose **one browser** (for example Edge) for every session and keep zoom at 100%.

## B. Keep a private ID sheet

Write each participant's name next to their code (P01 to P05, X01, X02) **on
paper**, not on the laptop and not in the repository. You need it to give each
person the same code in Session 2. Destroy it when the project is marked.

## C. Before every session

1. Plug the laptop into power and close other programs.
2. Open Command Prompt:
   ```
   cd %USERPROFILE%\Documents\typing-auth
   .venv\Scripts\activate
   python app.py
   ```
   Do **not** add `--workspace` here: real data goes to the normal `data` folder.
   There must be **no yellow "SIMULATED" banner** on the page.
3. Open http://127.0.0.1:5000 and go to **Data collection**.
4. Do not change or update the code between Session 1 and Session 2,
   unless something is broken.

## D. For each participant

1. Explain what is recorded. Let them open **Information for participants**,
   and tick the consent box only if they agree.
2. Select their ID and the session.
3. **Practice mode**: 3 to 5 attempts, not saved.
4. Switch to **Record**. They type at their normal speed, not as fast as
   possible. Short breaks are fine.
5. The page stops at the target by itself (Session 1: 20, Session 2: 10,
   impostors: 10).
6. Wrong keys and Backspace discard the attempt automatically; they simply
   start the sentence again. Do not coach their typing.

If an attempt is saved under the **wrong ID** by mistake, write down the time
and the ID and fix it before training. Do not edit the CSV casually.

## E. Order of sessions

| When | Who | Attempts |
|---|---|---|
| Day 1 | P01 to P05, Session 1 | 20 each |
| Any day | X01, X02 (people who are not enrolled), Session 1 | 10 each |
| At least one day after Day 1 | P01 to P05, Session 2 | 10 each |

Impostors must never be any of P01 to P05.

## F. After every session

1. **Back up** the `data` folder to a USB drive or a private Google Drive,
   for example as `data_backup_2026-11-25`. It is the only copy of the
   dataset, because data is not uploaded to GitHub.
2. Check the counts:
   ```
   python -m src.features
   python -m src.explore
   ```

## G. After all data is collected

Run these in order and keep every output:
```
python -m src.features
python -m src.explore
python -m src.train
python -m src.train --shuffle-check
python -m src.evaluate > reports\evaluate_output.txt
type reports\evaluate_output.txt
```
- `src.evaluate` is the final test. Run it **once only**.
- Results and figures are in `reports` and `reports\figures`.
- Back up `data`, `models` and `reports` together.
