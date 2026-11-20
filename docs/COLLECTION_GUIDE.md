# Data Collection Guide (password login version)

Everything happens on this laptop, using its **built-in keyboard**, with one
browser at 100% zoom. Data, training, evaluation and the demo all use this machine.

## A. Accounts

Five accounts are registered (check with `python -m src.users list`):

| ID | Name | Email |
|---|---|---|
| U01 | Akash | akash@gmail.com |
| U02 | Daksh | daksh@gmail.com |
| U03 | Parteek | parteek@gmail.com |
| U04 | Aditya | aditya@gmail.com |
| U05 | Alex | alex@gmail.com |

Passwords are stored only as hashes. Keep the passwords on a **paper sheet**:
people need it to type each other's passwords during collection.

## B. What each person types per session

| | Session 1 (day 1) | Session 2 (another day, at least 1 day later) |
|---|---|---|
| Own password | 30 | 10 |
| Next person's password | 2 | 2 |
| The other three passwords | 1 each | 1 each |
| **Total per person** | **35** | **15** |

"Next person" follows the list: U01 types U02's twice, U02 types U03's, ...,
U05 types U01's. The Data collection page shows each person's task list and
stops each task at its target, so you do not need to count.

## C. Before every session

```
cd %USERPROFILE%\Documents\typing-auth
.venv\Scripts\activate
python app.py
```
Open http://127.0.0.1:5000. There must be **no yellow "SIMULATED" banner**.

## D. For each person

1. Open **Data collection**, select **Who is typing** and the **Session**.
2. They read **Information for participants** and tick consent.
3. Choose **Own password**, keep mode on **Practice**, type it 3 to 5 times
   (press Enter after each). Practice checks the password but saves nothing.
4. Switch to **Record**. Type the own password until the task shows 30/30
   (Session 2: 10/10). The page moves to the next task automatically.
5. For each other person's password: practise it 2 or 3 times first (it is
   unfamiliar), then record the required number.
6. Mistakes: Backspace or any wrong key clears the field; type it again.
   A wrong password is rejected and not saved.

Type at normal speed. Do not copy anyone's style.

## E. After every session

1. Stop the server (Ctrl+C) and copy the `data` folder to a USB drive or a
   private Google Drive. It contains `users.json` and the typing data, and is
   not uploaded to GitHub.
2. Check the counts: `python -m src.explore`.

## F. After Session 2

```
python -m src.features
python -m src.explore
python -m src.train
python -m src.train --shuffle-check
python -m src.evaluate > reports\evaluate_output.txt
type reports\evaluate_output.txt
```
Run `src.evaluate` **once only**. Then try the **Login** page.
