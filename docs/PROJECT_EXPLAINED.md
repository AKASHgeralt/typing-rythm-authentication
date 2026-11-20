# Typing Rhythm Authentication Using Lightweight Machine Learning
## Complete project description: password login version (for study and the viva)

---

## 0. Instructions for the AI tutor (read first)

You are helping a team of third-year BTech students understand their own
university project before their viva. The description below matches the code
they have written. Please:

1. Teach step by step, from the big picture down to the maths.
2. Use small numeric examples whenever you explain a formula.
3. After each section, ask 3 to 5 short questions to check understanding.
4. **Do not invent results.** Real data has **not** been collected yet. The pipeline
   has only been run on simulated data, and simulated numbers are not findings.
5. Do not suggest making the project more complex (no deep learning, no databases,
   no cloud). The scope is fixed at Easy to Medium difficulty.
6. If something here seems wrong or unclear, say so instead of guessing.

Team: Daksh Nandal (24/11/EC/002), Akashveer Singh (24/11/EC/031),
Parteek Singla (24/11/EE/030), Aditya Chauhan (24/11/EC/032),
Jawaharlal Nehru University, New Delhi.

---

## 1. The project in one paragraph

A login page asks for an **email** and a **password**. Login succeeds only if
**(1)** the email belongs to a registered account, **(2)** the password is correct,
**and (3)** the password was typed with the **typing rhythm of the account owner**.
The rhythm is measured from the time each key is pressed and released
(**keystroke dynamics**, a behavioural biometric). Each account has its own trained
models. If someone knows Akash's password but types it in their own way, the system
should answer **No**. This is an academic prototype on one laptop, not a production
security system.

How it differs from the original proposal: the proposal used one fixed public
sentence typed by everyone, with one model that decided *which of five people* typed
it. The final version uses each person's own password, with a separate model per
account that decides *owner or not owner*. This is closer to how keystroke dynamics
is used in practice: as an extra check on top of a password.

---

## 2. Environment

| Item | Detail |
|---|---|
| Computer | One Windows laptop. Development, data collection, training, evaluation and the demo all happen here. |
| Keyboard | The laptop's **built-in keyboard only**. Key travel and layout change timings, so one keyboard is used throughout. |
| Python | 3.12 in a virtual environment (`.venv`) |
| Packages (pinned) | Flask 3.1.2, NumPy 2.2.6, pandas 2.3.3, scikit-learn 1.7.2, Matplotlib 3.10.6, pytest 8.4.2. Joblib and SciPy come with scikit-learn; Werkzeug comes with Flask. |
| Front end | HTML, CSS, JavaScript (no framework), dark theme |
| Storage | JSON (accounts) and CSV files (no database) |
| Code hosting | GitHub (code only; accounts and data are excluded by `.gitignore`) |
| Network | Runs locally at http://127.0.0.1:5000. Nothing is sent to the internet. |
| GPU | Not needed. Training takes about a minute on a CPU. |

---

## 3. Accounts

| ID | Name | Email | Password length | Features per attempt |
|---|---|---|---|---|
| U01 | Akash | akash@gmail.com | 9 | 17 |
| U02 | Daksh | daksh@gmail.com | 9 | 17 |
| U03 | Parteek | parteek@gmail.com | 11 | 21 |
| U04 | Aditya | aditya@gmail.com | 10 | 19 |
| U05 | Alex | alex@gmail.com | 8 | 15 |

- Passwords are stored **only as hashes** in `data/users.json`, using Werkzeug's
  `generate_password_hash` (scrypt, with a random salt). At login,
  `check_password_hash` compares. The plain password is never written to disk.
- The typing data uses only the anonymous IDs U01 to U05.
- Every password contains `@`, typed with Shift. **Shift is not recorded as a key**;
  the `@` key (Shift + 2) is recorded as one key.

---

## 4. Project files

```
typing-auth/
├── app.py                    Flask server: pages and API routes
├── requirements.txt, pytest.ini, README.md, .gitignore
├── docs/COLLECTION_GUIDE.md  step-by-step plan for the typing sessions
├── templates/
│   ├── base.html             layout, navigation, "SIMULATED" banner
│   ├── index.html            home page (lists registered accounts)
│   ├── enroll.html           Data collection page
│   └── authenticate.html     Login page
├── static/js/
│   ├── capture.js            records press/release times in a password field
│   ├── enroll.js             collection page: typist, session, tasks, practice/record
│   └── authenticate.js       login page: sends email, password and timings
├── src/
│   ├── config.py             targets, collection plan, limits, folder paths
│   ├── users.py              accounts and password hashing (python -m src.users)
│   ├── storage.py            collection plan, validation, writing raw CSV
│   ├── features.py           timings -> feature vector (dwell and flight times)
│   ├── models.py             nearest-neighbour distance scorer (the KNN model)
│   ├── decision.py           FAR/FRR counting, threshold choice
│   ├── train.py              nested cross-validation, thresholds, final models
│   ├── evaluate.py           one-time final test on Session 2
│   ├── explore.py            counts and owner-vs-others plots
│   ├── authenticate.py       login check and login log
│   └── simulate.py           SIMULATED accounts and data in a separate "sim" folder
├── tests/                    35 automated tests
├── data/ models/ reports/    real data and results (data and models not on GitHub)
└── archive/                  old sentence-version data (not used)
```

---

## 5. Data flow

```
Person types a password in the browser (collection page or login page)
  │ capture.js: one row per key = (press time, release time)
  ▼
Server checks: account exists, password hash matches, timings are valid
  ├─ collection page ─► data/raw_keystrokes.csv   (timings + IDs only)
  └─ login page ─────► features ─► that account's model ─► score ≥ threshold ?
                                                         ─► "Success" or "No"
python -m src.features ─► data/features/U01.csv ... U05.csv
python -m src.train    ─► models/knn_U01.joblib ... rf_U05.joblib, thresholds.json
python -m src.evaluate ─► reports/test_metrics.json (run once)
```

The **same function** (`features_from_keys`) computes features for training data and
for login attempts, so both are processed identically.

---

## 6. Data collection

### 6.1 Roles

- **Genuine attempt:** a person types **their own** password.
- **Impostor attempt:** a person types **someone else's** password. They have been
  told the password, so this simulates a stolen password.

### 6.2 Plan per person

| | Session 1 (day 1) | Session 2 (at least 1 day later) | Total |
|---|---|---|---|
| Own password | 30 | 10 | 40 |
| Next person's password | 2 | 2 | 4 |
| Each of the other three passwords | 1 | 1 | 2 each |
| **Total typed per person** | **35** | **15** | **50** |

"Next person" follows the list order: U01 types U02's, U02 types U03's, ...,
U05 types U01's. So each password receives exactly **5 impostor attempts per
session** from all four other people (2 + 1 + 1 + 1).

### 6.3 Totals

| | Per account | All 5 accounts |
|---|---|---|
| Session 1 genuine (training) | 30 | 150 |
| Session 1 impostor (training) | 5 | 25 |
| Session 2 genuine (testing) | 10 | 50 |
| Session 2 impostor (testing) | 5 | 25 |
| **Total attempts** | **50** | **250** |

Raw rows = attempts × password length = 50 × (9 + 9 + 11 + 10 + 8) = **2,350 rows**.

- 3 to 5 **practice** attempts first (checked, not saved). Impostors also practise
  an unfamiliar password 2 or 3 times before recording.
- Consent is required. The page shows each person's task list with counters and
  stops each task at its target.
- **Why two sessions:** attempts typed in one sitting are very similar. Testing on a
  different day checks whether the rhythm is stable over time and avoids optimistic results.

### 6.4 Capture rules (capture.js)

- Listens to **keydown** and **keyup** in the password field.
- Time source: **`KeyboardEvent.timeStamp`** (milliseconds, high resolution).
- Each press is paired with its release by **`event.code`** (physical key), so
  overlapping keys are timed correctly.
- Times are relative to the first key press (first press = 0).
- Not recorded: **Shift**, **Caps Lock**, **auto-repeat** events (key held down).
- Clears the field (type again from the start): Backspace, arrow keys or any
  non-character key, Ctrl/Alt/Windows shortcuts, pasting, losing focus while a key is held.
- **Enter** submits once all keys are released.
- A field changed without key events (e.g. browser autofill) is rejected.

### 6.5 Server validation (storage.py)

| Check | Rule |
|---|---|
| Consent | must be true |
| Typist and target | registered accounts; the typist must have a task for that target |
| Session | 1 or 2 |
| Password | must match the target account's hash; otherwise "wrong password", not saved |
| Number of keys | must equal the password length |
| Key order | key_index 0, 1, 2 ... in order |
| First press | exactly 0 ms |
| Press order | each press at or after the previous press |
| Hold time | greater than 0 and at most 2,000 ms |
| Attempt length | last release at most 30,000 ms |
| Task target | refuses attempts once a task is complete |

### 6.6 Raw file: `data/raw_keystrokes.csv` (one row per key)

| Column | Meaning |
|---|---|
| typist_id | who typed (U01 to U05) |
| target_id | whose password was typed |
| role | genuine (typist = target) or impostor |
| session | 1 or 2 |
| attempt_id | unique attempt number |
| key_index | position in the password (0, 1, 2 ...) |
| press_ms | press time in ms from the first press |
| release_ms | release time in ms from the first press |
| recorded_at | date and time saved (shows Session 2 was on another day) |

**No password, no characters and no key names are stored.** The data cannot reveal
anyone's password.

---

## 7. Features (the maths)

For key *i* of a password with *n* characters, press time *pᵢ* and release time *rᵢ*:

- **Dwell (hold) time**: Dᵢ = rᵢ − pᵢ → *n* values (columns d00, d01, ...)
- **Flight time**: Fᵢ = pᵢ₊₁ − rᵢ → *n* − 1 values (columns f00, f01, ...)

**Feature vector** of one attempt: [D₀, ..., Dₙ₋₁, F₀, ..., Fₙ₋₂], i.e. **2n − 1 numbers**.
For `akash@123` (n = 9): 9 + 8 = **17 features**.

- Flight time is **negative** when the next key is pressed before the previous one is
  released (overlap). The sign is kept: overlapping is a personal habit.
- Each feature belongs to a fixed key position of that account's password, so the
  model compares like with like (e.g. "how long is the `@` key held").
- Because every password has a different length, every account has its **own
  feature table** (`data/features/U01.csv` ...).

**Worked example (3 keys, from the unit test):**

| key | press | release | dwell |
|---|---|---|---|
| 0 | 0 | 80 | 80 |
| 1 | 100 | 200 | 100 |
| 2 | 150 | 260 | 110 |

Flight: 100 − 80 = 20; 150 − 200 = −50 (overlap).
Feature vector = [80, 100, 110, 20, −50].

---

## 8. Machine learning

### 8.1 One problem per account

For account *u*, Session 1 gives a small table:

- **X**: 35 rows (attempts) × (2n − 1) feature columns
- **y**: 1 = genuine (30 rows), 0 = impostor (5 rows)

The classes are **unbalanced** (6 : 1). There are **5 accounts × 2 model types = 10 models**.
Session 2 is never used for training or tuning. Random seed 42 everywhere.

### 8.2 Model 1: nearest-neighbour distance ("KNN")

Why not a normal KNN classifier? With only 4 or 5 impostor examples, almost all
neighbours of any attempt are the owner's, so a normal KNN gives impostors a
genuine score near 1 as well. On simulated data it could not separate them.
So the KNN model measures **distance to the owner's own attempts** and is
trained **only on the owner's attempts** (impostor rows are ignored when fitting).

Steps (pipeline: StandardScaler → NearestNeighbourScorer):
1. **Standardise** every feature: z = (x − μ) / σ, with μ and σ from the training
   fold only (the scaler is inside the pipeline, so no data leakage).
2. **Distance** of a new attempt: d = mean Euclidean distance to its **k nearest
   owner attempts**, where Euclidean distance = √Σ(zₐ − z_b)².
3. **Normalise**: d_norm = d / s, where s = the median, over the owner's attempts,
   of the same k-neighbour distance (each attempt compared with the *other* owner
   attempts). So d_norm ≈ 1 means "as close as the owner's attempts usually are".
4. **Genuine score** = 1 / (1 + d_norm). About 0.5 for a typical owner attempt,
   smaller the further away the typing is.

Example: if s = 2.0 and a login is at distance d = 2.0 → d_norm = 1 → score 0.50.
If d = 6.0 → d_norm = 3 → score 0.25.

Hyperparameter: **k ∈ {1, 3, 5}**. The model stores the owner's scaled training
vectors plus the scaler's means and standard deviations; it has no trained weights
(a "lazy" learner).

### 8.3 Model 2: Random Forest

- An owner-vs-others classifier: many decision trees, each trained on a bootstrap
  sample (random sample with replacement), each split using a random subset of
  features (default √(number of features)) and Gini impurity.
- **class_weight = "balanced"**: impostor examples get about 6× more weight, so the
  few impostor attempts are not ignored.
- **Genuine score** = average over trees of the fraction of genuine training examples
  in the leaf the attempt reaches.
- No scaling needed: trees split one feature at a time.
- Hyperparameters: **n_estimators ∈ {100, 300}**, **max_depth ∈ {None, 5}**.

### 8.4 Scores are not probabilities

Both models give scores between 0 and 1 (via `predict_proba`). They are used as
**scores**, not as calibrated probabilities.

### 8.5 Nested cross-validation (Session 1, per account)

Purpose: if the same cross-validation is used to choose hyperparameters and to
measure error, the estimate is optimistic (Varma and Simon, 2006). Nested CV separates them.

- **Outer loop**: stratified 5-fold on the 35 attempts. Each fold trains on 28
  (24 genuine + 4 impostor) and scores the held-out 7 (6 genuine + 1 impostor).
- **Inner loop**: on the 28, a stratified 4-fold grid search (21 train / 7 validate)
  chooses the hyperparameters. Scoring = **ROC AUC**, because accuracy is
  misleading with unbalanced classes (always saying "genuine" would already give 86%).
- Result: every Session 1 attempt gets a genuine score from a model that never saw it
  (**out-of-fold scores**).

Model fits per account: KNN 3 settings × 4 inner × 5 outer = 60 (+5 refits);
RF 4 × 4 × 5 = 80 (+5 refits). Final models: a 5-fold grid search on all 35
attempts (KNN 15 fits, RF 20 fits) and one refit, saved as `models/knn_U01.joblib` etc.

### 8.6 Threshold selection

- Out-of-fold scores of all five accounts are **pooled**: **150 genuine** and
  **25 impostor** scores per model type.
- Candidate thresholds: 0.00, 0.01, ..., 1.00 (101 values).
- FRR(t) = genuine scores below t / 150; FAR(t) = impostor scores at or above t / 25.
- Chosen t = the value where |FAR − FRR| is smallest (approximate **Equal Error Rate**).
  Ties: lower FAR + FRR, then higher t.
- **One threshold per model type** (2 in total). A separate threshold per account
  would rest on only 5 impostor scores, which is too unreliable.

### 8.7 Demo model and sanity check

- The login page uses the model type with the lower average of FAR and FRR in nested
  cross-validation (tie: higher mean AUC). Test data plays no part in the choice.
- `python -m src.train --shuffle-check` repeats nested CV with **shuffled labels**.
  Mean AUC should fall to about **0.5** (chance). If not, something is leaking.

---

## 9. Final evaluation (run once)

Test data: **Session 2**, per account 10 genuine + 5 impostor attempts;
in total **50 genuine** and **25 impostor** attempts.

| Measure | Definition | Out of |
|---|---|---|
| FRR | owners rejected (score < t) | 50 |
| FAR | impostors accepted (score ≥ t) | 25 |
| Accuracy | correct accept/reject decisions | 75 |
| Precision (genuine) | of accepted attempts, how many were the owner | |
| Recall (genuine) | of owner attempts, how many were accepted (= 1 − FRR) | |
| F1 | 2 × precision × recall / (precision + recall) | |
| Confusion matrix | 2 × 2: actual (genuine, impostor) × decision (accepted, rejected) | |

Also reported per account (e.g. U01: FRR 1/10, FAR 0/5).

Rules:
- Always give **raw counts** with percentages (e.g. 3/50 = 6%).
- One error = **2%** of FRR (out of 50) and **4%** of FAR (out of 25).
- The impostors in Session 2 are the **same people** who gave impostor examples in
  Session 1 (insiders who know the password). There is no test against complete strangers.
- `src.evaluate` refuses to run twice unless `--force` is used: test data is used once.

---

## 10. Login (the demo)

1. Enter email and password; press Enter or click Login.
2. Unknown email → **No** ("Unknown email address").
3. Wrong password (hash check) → **No** ("Wrong password").
4. Correct password → timings validated → same feature extraction → that account's
   demo model → genuine score.
5. Score ≥ threshold → **Success**; otherwise **No** ("Password correct, but the typing
   rhythm does not match"). The page shows the score and threshold.
6. Logged in `data/login_log.csv`: timestamp, user_id, model, password_ok, score,
   threshold, result. **No password and no timings** are logged, and logins are
   **never added to the training data**.

---

## 11. Everything that will be saved

| File | Content |
|---|---|
| data/users.json | 5 accounts: ID, name, email, password length, password hash |
| data/raw_keystrokes.csv | 2,350 rows, 9 columns |
| data/features/U01.csv ... U05.csv | 50 rows each; 5 ID columns + 15 to 21 features |
| data/login_log.csv | one row per login on the demo page |
| models/knn_U01.joblib ... knn_U05.joblib | KNN distance model per account |
| models/rf_U01.joblib ... rf_U05.joblib | Random Forest per account |
| models/thresholds.json | threshold per model type, best hyperparameters per account, demo model |
| reports/cv_metrics.json | nested CV: pooled FRR x/150, FAR x/25, mean AUC, per-account results |
| reports/test_metrics.json | final test with counts, per-account results, confusion matrices |
| reports/evaluate_output.txt | printed output of the final test |
| reports/figures/owner_vs_others.png | mean dwell and mean flight, owner vs others, per account |
| reports/figures/cv_far_frr_knn.png, cv_far_frr_rf.png | FAR and FRR against threshold |
| reports/figures/test_confusion_knn.png, test_confusion_rf.png | 2 × 2 confusion matrices |

---

## 12. All the numbers in one place

| Quantity | Value |
|---|---|
| Accounts | 5 |
| Password lengths | 8 to 11 characters |
| Features per attempt | 2n − 1 = 15 to 21 |
| Per person, Session 1 | 30 own + 5 others' = 35 |
| Per person, Session 2 | 10 own + 5 others' = 15 |
| Per account, training | 30 genuine + 5 impostor = 35 |
| Per account, testing | 10 genuine + 5 impostor = 15 |
| Total attempts / raw rows | 250 / 2,350 |
| Models | 10 (KNN and RF for each account) |
| Outer / inner CV folds | 5 / 4 |
| Outer fold sizes | 28 train (24 + 4), 7 test (6 + 1) |
| KNN grid | k = 1, 3, 5 |
| RF grid | trees = 100, 300; depth = None, 5; class_weight = balanced |
| Inner CV scoring | ROC AUC |
| Pooled out-of-fold scores | 150 genuine, 25 impostor |
| Thresholds | 2 (one per model type), grid 0.00 to 1.00 step 0.01 |
| Test decisions | 50 genuine, 25 impostor |
| Validation limits | hold 0 to 2,000 ms; attempt ≤ 30,000 ms; password 4 to 64 characters |
| Random seed | 42 |
| Automated tests | 35 |

---

## 13. Status

Done:
- Password login web app (Flask), data collection page with task lists, hashed accounts
- Keystroke capture, validation, CSV storage without passwords
- Feature extraction, both models, nested CV, thresholds, one-time evaluation
- Simulated workspace for rehearsal; 35 tests passing; code on GitHub
- Five real accounts registered on the laptop

Still to do:
1. Session 1: every person types 35 attempts (30 own + 5 others').
2. Back up the `data` folder.
3. Session 2 at least one day later: 15 attempts each (10 own + 5 others').
4. Run features, explore, train, shuffle check, evaluate (once).
5. Update the report: the change from sentence to password login, the method,
   the real results and figures. The team then rewrites it in its own words.
6. Rehearse the login demo on the laptop.

---

## 14. Limitations to state honestly

- Five accounts, one keyboard, one laptop: results do not generalise.
- Only 5 impostor attempts per account for training and 5 for testing; one accepted
  impostor changes FAR by 4 percentage points.
- Test impostors are the same people as training impostors; complete strangers are not tested.
- Impostors knew the password but did not practise imitating the owner's rhythm.
- Thresholds are chosen on Session 1; typing can drift between days, which may raise FRR.
- Typing changes with tiredness, mood and practice.
- Scores are not calibrated probabilities.
- This is an extra factor on top of a password, not a replacement for it.

---

## 15. Likely viva questions

1. What is keystroke dynamics? Define dwell and flight time.
2. Why can flight time be negative, and why keep it?
3. Why does the login also check the rhythm if the password is already correct?
4. Why does each account need its own model?
5. Why did you change from a fixed sentence to passwords?
6. How do you handle the Shift key in `@`?
7. Why don't you store the password or the typed characters?
8. How are passwords stored? What is hashing, and why a salt?
9. What is a genuine attempt and what is an impostor attempt?
10. Why do people type each other's passwords during collection?
11. Why two sessions on different days?
12. How many features does Akash's password give, and why 2n − 1?
13. Why does the KNN model learn only from the owner's attempts?
14. How is the KNN genuine score calculated? Give an example.
15. Why is StandardScaler needed, and why inside a pipeline?
16. How does Random Forest produce a score? Why class_weight = "balanced"?
17. What is nested cross-validation and why use it?
18. Why ROC AUC and not accuracy for tuning?
19. How is the threshold chosen? What is the Equal Error Rate?
20. Why one threshold per model type instead of one per account?
21. Define FAR and FRR. What happens to each when the threshold goes up?
22. Why report raw counts with percentages?
23. What does the shuffled-label check prove?
24. Why is the test set used only once?
25. What are the main limitations?
26. Why not deep learning?
27. What would you change for a real system?

---

## 16. Suggested 3-day study plan

- **Day 1 (idea and data):** sections 1 to 7. Work through the 3-key example by hand.
  Run the simulated pipeline and open `sim/data/raw_keystrokes.csv` and one features file.
- **Day 2 (machine learning):** sections 8 and 9. Draw the nested CV diagram for one
  account (35 → 28/7 → 21/7). Compute a KNN score by hand. Sketch FAR/FRR curves.
- **Day 3 (system and viva):** sections 10 to 15. Try the simulated Login page.
  Answer the viva questions aloud. Split topics: capture and data; features and
  hashing; models and cross-validation; evaluation and limitations.

---

## 17. References (IEEE style)

[1] F. Monrose and A. D. Rubin, "Keystroke dynamics as a biometric for authentication," Future Generation Computer Systems, vol. 16, no. 4, pp. 351–359, 2000, doi: 10.1016/S0167-739X(99)00059-X.
[2] P. S. Teh, A. B. J. Teoh, and S. Yue, "A survey of keystroke dynamics biometrics," The Scientific World Journal, vol. 2013, Art. no. 408280, 2013, doi: 10.1155/2013/408280.
[3] R. Shadman, A. A. Wahab, M. Manno, M. Lukaszewski, D. Hou, and F. Hussain, "Keystroke dynamics: Concepts, techniques, and applications," ACM Computing Surveys, vol. 57, no. 11, Art. no. 283, 2025, doi: 10.1145/3733103.
[4] K. S. Killourhy and R. A. Maxion, "Comparing anomaly-detection algorithms for keystroke dynamics," in Proc. IEEE/IFIP Int. Conf. Dependable Systems and Networks, 2009, pp. 125–134, doi: 10.1109/DSN.2009.5270346.
[5] T. M. Cover and P. E. Hart, "Nearest neighbor pattern classification," IEEE Transactions on Information Theory, vol. 13, no. 1, pp. 21–27, Jan. 1967, doi: 10.1109/TIT.1967.1053964.
[6] L. Breiman, "Random forests," Machine Learning, vol. 45, no. 1, pp. 5–32, 2001, doi: 10.1023/A:1010933404324.
[7] F. Pedregosa et al., "Scikit-learn: Machine learning in Python," Journal of Machine Learning Research, vol. 12, no. 85, pp. 2825–2830, 2011.
[8] S. Varma and R. Simon, "Bias in error estimation when using cross-validation for model selection," BMC Bioinformatics, vol. 7, Art. no. 91, 2006, doi: 10.1186/1471-2105-7-91.

Reference [4] is especially relevant now: it evaluates detectors that learn only from
the genuine user's typing of a fixed password, as the KNN model here does.
(Check the article number and year of [3], and the DOIs of [1] and [4], on the publisher pages.)
