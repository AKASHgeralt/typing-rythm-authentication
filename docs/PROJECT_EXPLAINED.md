> **OUTDATED.** This file describes the earlier fixed-sentence version. The project now uses an email + password login page (see docs/COLLECTION_GUIDE.md). An updated explanation will replace this file.

# Typing Rhythm Authentication Using Lightweight Machine Learning
## Complete project description (for studying and teaching the team)

---

## 0. Instructions for the AI tutor (read first)

You are helping a team of four third-year BTech students understand their own
university project before their viva. The description below is accurate to the
code they have written. Please:

1. Teach it step by step, starting from the big picture and going down to the maths.
2. Use small numeric examples whenever you explain a formula.
3. After each section, ask 3 to 5 short questions to check understanding.
4. **Do not invent results.** Real data has **not** been collected yet. The pipeline
   has only been tested on simulated data, and simulated numbers must never be
   presented as findings.
5. Do not suggest making the project more complex (no deep learning, no databases,
   no cloud). The scope is fixed at Easy to Medium difficulty.
6. If something in this description seems wrong or unclear, say so instead of guessing.

Team: Daksh Nandal (24/11/EC/002), Akashveer Singh (24/11/EC/031),
Parteek Singla (24/11/EE/030), Aditya Chauhan (24/11/EC/032),
Jawaharlal Nehru University, New Delhi.

---

## 1. What the project is, in one paragraph

People type in slightly different ways: some hold keys longer, some move between
keys faster, some overlap keys (press the next key before releasing the previous one).
This is called **keystroke dynamics**, a kind of **behavioural biometric**. The project
is a small web application that runs on one laptop. Everyone types the same fixed
sentence, **"the quick brown fox jumps over the lazy dog"**. The browser records the
exact time of every key press and key release. Python turns those times into nine
numbers (features) per attempt. Two machine learning models, **K-Nearest Neighbors (KNN)**
and **Random Forest (RF)**, learn each participant's typing pattern. To log in, a person
says "I am P03" and types the sentence. If the model's score for P03 reaches a
threshold, the page shows **Access Granted**, otherwise **Access Denied**.

Important points to be able to say in the viva:
- Authentication is based on **how** the sentence is typed, not **what** is typed. The
  sentence is public and is not a password.
- It is an **academic prototype**, not a security product.
- It uses only a normal laptop keyboard. No extra hardware.
- Users do **not** choose their own password. A fixed sentence is needed because the
  five-person comparison only works if everyone types the same keys. Using each user's
  own password would need one separate anomaly-detection model per user, which is out of
  scope (possible future work).

---

## 2. Machines and environment

| Item | Detail |
|---|---|
| Computer | One Windows laptop. The code was written here, and **all real data collection, training, evaluation and the live demo happen here too, using its built-in keyboard.** |
| Why one keyboard | Key travel and layout change timings. A model trained on one keyboard may fail on another. |
| Python | 3.12 (in a virtual environment `.venv`) |
| Packages (pinned) | Flask 3.1.2, NumPy 2.2.6, pandas 2.3.3, scikit-learn 1.7.2, Matplotlib 3.10.6, pytest 8.4.2. Joblib comes with scikit-learn. |
| Front end | HTML, CSS, JavaScript (no framework), dark theme |
| Storage | CSV files (no database) |
| Code hosting | GitHub repository (code only; data is excluded by `.gitignore`) |
| Network | Runs locally at http://127.0.0.1:5000. Nothing is sent to the internet. |
| GPU | Not needed. Training takes about 20 to 60 seconds on a CPU. |

---

## 3. Project folder and what every file does

```
typing-auth/
├── app.py                    Flask web server: pages + API routes
├── requirements.txt          pinned package versions
├── pytest.ini                test settings
├── README.md                 setup and command list
├── docs/COLLECTION_GUIDE.md  step-by-step guide for the data sessions
├── templates/                HTML pages (Jinja templates)
│   ├── base.html             common layout, navigation, "SIMULATED" banner
│   ├── index.html            home page
│   ├── enroll.html           Data collection page
│   └── authenticate.html     Authenticate page
├── static/
│   ├── css/style.css         dark theme
│   └── js/
│       ├── capture.js        records key press/release times, rejects bad attempts
│       ├── enroll.js         data collection page logic (consent, practice/record, saving)
│       └── authenticate.js   authentication page logic (sends attempt, shows result)
├── src/
│   ├── config.py             sentence, participant IDs, targets, limits, folder paths
│   ├── storage.py            server-side validation and writing raw CSV
│   ├── features.py           raw timings -> 9 features (and optional 85 for Set B)
│   ├── explore.py            counts and box plots of features per participant
│   ├── decision.py           decision rule, FAR/FRR counting, threshold choice
│   ├── train.py              nested cross-validation, thresholds, final models
│   ├── evaluate.py           one-time final test on Session 2 and impostors
│   ├── authenticate.py       live authentication + decision log
│   └── simulate.py           creates SIMULATED data in a separate "sim" folder
├── tests/                    36 automated tests (pytest)
├── data/                     real data (not on GitHub)
├── models/                   trained models (not on GitHub)
├── reports/                  metrics and figures
└── sim/                      simulated workspace (not on GitHub, never for results)
```

---

## 4. End-to-end data flow

```
Participant types the sentence in the browser
   │  capture.js: keydown/keyup -> 43 rows of (key, code, press time, release time)
   ▼
Flask /api/attempts  ── storage.py validates again ──► data/raw_keystrokes.csv
   ▼
python -m src.features  ──► data/features.csv   (one row of 9 features per attempt)
   ▼
python -m src.train     ──► models/knn.joblib, models/rf.joblib, models/thresholds.json,
                            reports/cv_metrics.json, FAR/FRR figures
   ▼
python -m src.evaluate  ──► reports/test_metrics.json, confusion matrix figures (run ONCE)
   ▼
Authenticate page: claimed ID + new typing -> same 9 features -> saved model -> score
   -> score >= threshold ? Access Granted : Access Denied   (logged in data/auth_log.csv)
```

Key design rule: the **same function** (`features_from_keys`) computes features for
training data and for live authentication, so both are processed identically.

---

## 5. Data collection

### 5.1 Participants and attempts

| Group | People | Session | Attempts each | Total | Used for |
|---|---|---|---|---|---|
| Enrolled (P01 to P05) | 5 | Session 1 | 20 | 100 | Training, tuning, threshold selection |
| Enrolled (P01 to P05) | 5 | Session 2 (at least 1 day later) | 10 | 50 | Final test only |
| External impostors (X01, X02) | 2 | Session 1 only | 10 | 20 | Final test only, never in training |
| **Total** | 7 people | | | **170 attempts** | |

- Each attempt has **43 keystrokes** (the sentence has 35 letters + 8 spaces = 43 characters,
  all lowercase, no punctuation, no Shift needed).
- Total raw rows: 170 × 43 = **7,310 rows**.
- 3 to 5 **practice attempts** per person before recording. Practice is **not saved**.
- Consent is required before typing. A paper sheet (not on the computer) maps real names
  to codes so each person gets the same code in Session 2.
- Why two sessions: attempts typed in one sitting look similar. Testing on another day
  checks whether a person's rhythm is stable over time.

### 5.2 How the browser captures timing (capture.js)

- Listens to **keydown** (press) and **keyup** (release) events.
- Time source: **`KeyboardEvent.timeStamp`**, a high-resolution time in milliseconds.
- `event.key` = the character typed (used to check the sentence).
- `event.code` = the physical key (for example `KeyT`, `Space`). Each press is paired with
  its release using `code`, which is why overlapping keys are timed correctly.
- Times are stored relative to the first key press (the first press is time 0).

Rules (attempt is **discarded** and the person starts again):
- wrong character (including uppercase, because `T` ≠ `t`)
- Backspace
- Ctrl, Alt or Windows key (blocks shortcuts such as Ctrl+V)
- pasting or dropping text
- clicking away (the typing box loses focus)
- an extra key pressed after the last letter
- a missing release event

Ignored (not recorded, not an error):
- **auto-repeat** keydown events (`event.repeat` is true when a key is held down)
- Shift and Caps Lock on their own

### 5.3 Server-side validation (storage.py)

The server checks every attempt again, so a modified request cannot add bad data:

| Check | Limit |
|---|---|
| Consent flag | must be `true` |
| Participant ID | P01 to P05 or X01, X02 |
| Session | enrolled: 1 or 2; impostors: 1 only |
| Number of keys | exactly 43 |
| key_index | 0, 1, 2 ... 42 in order |
| key | must equal the sentence character at that position |
| code | non-empty text, at most 30 characters |
| First press | exactly 0 ms |
| Press order | each press at or after the previous press |
| Dwell (hold) time | greater than 0 and at most 2,000 ms |
| Attempt length | last release at most 60,000 ms |
| Session target | refuses extra attempts once 20 / 10 / 10 are saved |

### 5.4 Raw data file: `data/raw_keystrokes.csv` (one row per keystroke)

| Column | Meaning |
|---|---|
| participant_id | P01 ... P05, X01, X02 |
| role | enrolled or impostor |
| session | 1 or 2 |
| attempt_id | unique attempt number (1, 2, 3 ...) |
| key_index | 0 to 42 |
| key | character typed (space stored as " ") |
| code | physical key, e.g. KeyT, Space |
| press_ms | press time in ms from first press (2 decimals) |
| release_ms | release time in ms from first press (2 decimals) |
| recorded_at | date and time the attempt was saved (proves Session 2 was on another day) |

10 columns. No names, no passwords, no free text.

---

## 6. Feature engineering (the maths)

### 6.1 Basic timings

For key *i* with press time *pᵢ* and release time *rᵢ*:

- **Dwell time**: Dᵢ = rᵢ − pᵢ  (how long the key is held) → 43 values per attempt
- **Flight time**: Fᵢ = pᵢ₊₁ − rᵢ  (gap from releasing a key to pressing the next) → 42 values
- **Press-to-press interval**: Iᵢ = pᵢ₊₁ − pᵢ → 42 values

Flight time is **negative** when the next key is pressed before the previous key is
released (overlap). Negative values are **kept**, because overlapping is a typing habit.

### 6.2 The nine features (Set A, primary)

| # | Feature | Formula |
|---|---|---|
| 1 | dwell_mean | mean of the 43 dwell times |
| 2 | dwell_median | median of the 43 dwell times |
| 3 | dwell_std | population standard deviation (ddof = 0) of dwell times |
| 4 | flight_mean | mean of the 42 flight times |
| 5 | flight_median | median of the 42 flight times |
| 6 | flight_std | population standard deviation of flight times |
| 7 | p2p_std | population standard deviation of the 42 press-to-press intervals |
| 8 | overlap_ratio | (number of negative flight times) / 42 |
| 9 | chars_per_sec | 43 / (total duration in seconds) |

- **Total duration** = (latest release time − first press time). Stored as
  `total_duration_ms` for description only. It is **not** a model feature, because
  chars_per_sec = 43 / duration, so the two carry the same information.
- Population standard deviation: σ = √( Σ(xᵢ − x̄)² / n ).

### 6.3 Worked example (3 keys, used in the unit test)

| key | press | release | dwell |
|---|---|---|---|
| 0 | 0 | 80 | 80 |
| 1 | 100 | 200 | 100 |
| 2 | 150 | 260 | 110 |

- Flight: 100 − 80 = 20; 150 − 200 = **−50** (overlap)
- Press-to-press: 100, 50
- dwell mean = 96.67, median = 100, std = √(466.67/3) = 12.47
- flight mean = −15, median = −15, std = 35
- p2p std = 25
- overlap ratio = 1/2 = 0.5
- duration = 260 ms → 3 / 0.26 = 11.54 characters per second

### 6.4 Feature file: `data/features.csv` (one row per attempt)

14 columns: participant_id, role, session, attempt_id, total_duration_ms, and the 9 features.
170 rows when collection is complete.

### 6.5 Optional Set B (experiment only)

85 features: the 43 individual dwell times (dwell_00 ... dwell_42) and the 42 individual
flight times (flight_00 ... flight_41). Written to `data/features_set_b.csv` only with
`--set-b`. With only 100 training attempts, 85 features may **overfit**. The project
does not depend on Set B.

---

## 7. Machine learning

### 7.1 The learning problem

- Training input **X**: 100 rows (Session 1 attempts) × 9 features.
- Labels **y**: participant ID, 5 classes (P01 ... P05), 20 attempts each (balanced).
- Session 2 and impostor data are **never** used during training or tuning.
- Random seed 42 everywhere, so results are repeatable.

### 7.2 Model 1: K-Nearest Neighbors

- Pipeline: **StandardScaler → KNeighborsClassifier(weights="distance")**.
- StandardScaler: z = (x − μ) / σ for each feature, with μ and σ computed from the
  **training fold only**. Without scaling, features with big numbers (dwell in ms ≈ 100)
  would dominate features with small numbers (overlap ratio ≈ 0.1).
- Putting the scaler **inside the pipeline** prevents data leakage: during cross-validation
  it is refitted on each training fold, never on the held-out fold.
- Distance: Euclidean, d = √Σ(zₐ − z_b)².
- Distance weighting: each of the k nearest neighbours votes with weight 1/d.
- Score for each class = (sum of weights of neighbours from that class) / (sum of all weights).
  The five scores add up to 1.
- Hyperparameter grid: **k ∈ {3, 5, 7, 9}**. k = 1 is excluded because it gives only scores
  of 0 or 1, which cannot be thresholded.

### 7.3 Model 2: Random Forest

- Many decision trees, each trained on a **bootstrap sample** (random sample with
  replacement) of the training data, and at each split only a random subset of features is
  considered (default √9 = 3 features). Splits use **Gini impurity**.
- Score for each class = average over trees of the class probability in the leaf the
  attempt reaches. The five scores add up to 1.
- No scaling needed: a tree splits one feature at a time, so feature scale does not matter.
- Hyperparameter grid: **n_estimators ∈ {100, 300}**, **max_depth ∈ {None, 5, 10}** → 6 combinations.

### 7.4 Scores are not probabilities

Both models give scores from `predict_proba`. They are treated as **relative scores
between the five enrolled people**, not as calibrated real-world probabilities.

### 7.5 Nested cross-validation (on Session 1 only)

Why: if the same cross-validation is used both to pick hyperparameters and to measure
performance, the estimate is optimistic (Varma and Simon, 2006). Nested CV separates the two.

- **Outer loop**: stratified 5-fold. Each fold: 80 training attempts (16 per person) and
  20 held-out attempts (4 per person).
- **Inner loop**: on the 80 training attempts only, stratified 4-fold grid search
  (60 train / 20 validate in each inner fold), scoring = accuracy, chooses the hyperparameters.
- The tuned model then scores the 20 held-out attempts.
- After 5 outer folds, **every one of the 100 attempts has scores from a model that never saw it**
  (out-of-fold scores) → a 100 × 5 score matrix per model.

Number of model fits:
- KNN: 4 settings × 4 inner folds × 5 outer folds = 80 fits (+5 refits)
- RF: 6 settings × 4 × 5 = 120 fits (+5 refits)
- Final models: grid search with 5-fold CV on all 100 attempts (KNN 20 fits, RF 30 fits) + 1 refit each.

### 7.6 Genuine and false-claim scores

From the 100 × 5 out-of-fold score matrix:
- **100 genuine scores**: for each attempt, the score of its true ID.
- **400 false-claim scores**: for each attempt, the scores of the other 4 IDs.
  These 400 come from the **same 100 attempts**, so they are **not** 400 independent samples
  and **not** attempts by strangers.

### 7.7 Decision rule

**Accept the claim "I am c" if score(c) ≥ t**, where t is the model's threshold.

- Above t = 0.5, an accepted ID is always the model's top prediction (scores add to 1).
- Below 0.5, one attempt could be accepted for two IDs (e.g. scores 0.60 and 0.36 with t = 0.34).
- Why not "predicted ID must match the claim AND score ≥ t": with that rule an enrolled
  person's false claim can only be accepted when the model misidentifies them, so FAR can
  never exceed FRR, and the "FAR = FRR" threshold always falls to 0 (no threshold). So
  the simple score rule is used. (The report's section IV-F must be updated to say this.)

### 7.8 Threshold selection

- Candidate thresholds: 0.00, 0.01, ... 1.00 (101 values).
- FRR(t) = (genuine scores < t) / 100
- FAR(t) = (false-claim scores ≥ t) / 400
- Chosen t = the value where |FAR − FRR| is smallest (approximate **Equal Error Rate**).
  Ties: lower FAR + FRR, then higher t.
- **Each model gets its own threshold**, because KNN and RF produce differently shaped scores.
- Saved in `models/thresholds.json`.

### 7.9 Choosing the demo model

The demo model is the one with the lower average of FAR and FRR at its threshold in nested
cross-validation (tie: higher accuracy). The test data plays **no** part in this choice.

### 7.10 Sanity check

`python -m src.train --shuffle-check` repeats nested CV with **randomly shuffled labels**.
Accuracy should drop to about 1/5 = 20%. If it stays high, something is leaking.

---

## 8. Final evaluation (run once)

Test data: **50 Session 2 attempts** + **20 impostor attempts**.

| Measure | Data | Number of decisions |
|---|---|---|
| Accuracy, macro precision, macro recall, macro F1, 5×5 confusion matrix | Session 2 (prediction = highest score) | 50 attempts |
| FRR | Session 2, true ID claimed | 50 |
| FAR, enrolled false claims | Session 2, each of the other 4 IDs claimed | 200 (from 50 attempts) |
| FAR, external impostors | each impostor attempt claimed as each of the 5 IDs | 100 (from 20 attempts) |
| Impostor attempts accepted for at least one ID | impostor attempts | out of 20 |

Formulas (per participant, then averaged over 5 = **macro average**):
- Accuracy = correct predictions / 50
- Precision = TP / (TP + FP): of the attempts predicted as this person, how many were theirs
- Recall = TP / (TP + FN): of this person's attempts, how many were recognised
- F1 = 2 × Precision × Recall / (Precision + Recall)

Rules:
- Always report **raw counts** with percentages (e.g. 4/50 = 8%).
- Size of one error: 1/50 = 2%, 1/200 = 0.5%, 1/100 = 1%, 1/20 = 5%.
- The external impostor test is the hardest and most realistic: the classifier only knows
  5 people and always spreads its scores across them, so a stranger may still look like
  someone. This is the **closed-set** limitation.
- `src.evaluate` refuses to run a second time unless `--force` is used, because test data
  must be used only once.

---

## 9. Live authentication (the demo)

1. Choose claimed ID (P01 to P05 only) and model (KNN or RF; the demo model is pre-selected).
2. Type the sentence. Same capture rules as data collection.
3. Server validates the 43 keys, computes the same 9 features, runs `predict_proba`.
4. Decision: score(claimed ID) ≥ model threshold → Access Granted, else Access Denied.
5. The page shows the claimed score, the threshold, the model's closest match, and a bar
   for each of the 5 scores.
6. Logged in `data/auth_log.csv`: timestamp, claimed_id, model, threshold, claimed_score,
   predicted_id, decision. Keystrokes are **not** saved, and authentication attempts are
   **never** added to training data.

---

## 10. Everything that will be saved (the complete output list)

| File | Rows / content |
|---|---|
| data/raw_keystrokes.csv | 7,310 rows (170 attempts × 43), 10 columns |
| data/features.csv | 170 rows, 14 columns |
| data/features_set_b.csv | optional, 170 rows, 5 + 85 columns |
| data/auth_log.csv | one row per demo authentication |
| models/knn.joblib | final KNN pipeline (scaler + KNN) |
| models/rf.joblib | final Random Forest |
| models/thresholds.json | threshold and best hyperparameters for each model, demo model, class list, feature list |
| reports/cv_metrics.json | nested CV results: accuracy, P/R/F1, threshold, FRR x/100, FAR x/400, parameters chosen in each fold |
| reports/test_metrics.json | final test results with counts and confusion matrices |
| reports/evaluate_output.txt | printed output of the final test |
| reports/figures/features_by_participant.png | 3×3 box plots of the 9 features per participant (Session 1) |
| reports/figures/cv_far_frr_knn.png, cv_far_frr_rf.png | FAR and FRR against threshold |
| reports/figures/test_confusion_knn.png, test_confusion_rf.png | confusion matrices on Session 2 |

---

## 11. All the numbers in one place ("maximum limits")

| Quantity | Value |
|---|---|
| Sentence length | 43 characters (35 letters + 8 spaces) |
| Enrolled participants / impostors | 5 / 2 |
| Attempts: Session 1 / Session 2 / impostors | 20 / 10 / 10 each |
| Total attempts | 100 + 50 + 20 = 170 |
| Practice attempts | 3 to 5 per person, not saved |
| Gap between sessions | at least 1 day |
| Values per attempt | 43 dwell, 42 flight, 42 press-to-press |
| Model features | 9 (Set A); optional 85 (Set B) |
| Classes | 5 |
| Training matrix | 100 × 9 |
| Outer / inner CV folds | 5 / 4 |
| KNN grid | k = 3, 5, 7, 9 |
| RF grid | trees = 100, 300; depth = None, 5, 10 |
| Out-of-fold scores | 100 genuine + 400 false-claim |
| Threshold grid | 0.00 to 1.00, step 0.01 |
| Test decisions | 50 genuine, 200 enrolled false claims, 100 impostor claims (from 20 attempts) |
| Validation limits | dwell 0 to 2,000 ms; attempt ≤ 60,000 ms; code ≤ 30 characters |
| Random seed | 42 |
| Automated tests | 36 |

---

## 12. Current status

Done:
- Stage 0: Flask project setup and dark theme
- Stage 1: keystroke capture in the browser
- Stage 2: consent, practice/record modes, validation, CSV storage
- Stage 3: feature extraction with unit tests
- Stage 5: nested CV training, thresholds, final evaluation script
- Stage 6: Authenticate page with Access Granted/Denied
- Simulated-data workspace for rehearsal; 36 tests passing; code on GitHub

Still to do:
1. (Laptop is already set up: the project was built on it.)
2. Session 1 (P01 to P05, 20 each).
3. Impostors (X01, X02, 10 each).
4. Session 2 at least one day later (P01 to P05, 10 each).
5. Back up the data folder after every session.
6. Run features, explore, train, shuffle check, evaluate (once).
7. Update the report with real results, the decision-rule sentence, the recorded_at column
   and real figures; then the team rewrites it in its own words.
8. Optional: an evaluation page in the app showing the final metrics.
9. Rehearse the demo on the laptop.

Note from the simulated rehearsal (NOT a result): a team member who was never enrolled was
accepted as simulated "P03" with score 0.48 against threshold 0.39. This is an example of
the closed-set problem that the external impostor test measures.

---

## 13. Limitations to state honestly

- Only 5 participants, one sentence, one keyboard: results do not generalise.
- External impostor test: 20 attempts from 2 people; the 100 decisions are not independent;
  one accepted attempt moves the per-attempt rate by 5 percentage points.
- Thresholds are chosen on Session 1; Session 2 may give a higher FRR because typing drifts.
- Typing changes with tiredness, mood and practice.
- Scores are not calibrated probabilities.
- No test against someone deliberately imitating another person's rhythm.
- Closed-set classifier: it always chooses among the five enrolled people.

---

## 14. Likely viva questions (practise answering these)

1. What is keystroke dynamics? What are dwell and flight time?
2. Why can flight time be negative, and why do you keep it?
3. Why does everyone type the same sentence? Why not their own password?
4. Why `event.code` as well as `event.key`?
5. How do you handle a key held down (auto-repeat)?
6. Why two sessions on different days?
7. Why is total duration not a feature?
8. Why population standard deviation? (Simple and consistent; it only needs to be the same for all attempts.)
9. Why does KNN need StandardScaler but Random Forest does not?
10. Why is the scaler inside a Pipeline?
11. How does distance-weighted KNN produce a score?
12. How does Random Forest produce a score?
13. What is nested cross-validation, and why not ordinary cross-validation?
14. How many training and test attempts are in each outer fold?
15. What are the 100 genuine and 400 false-claim scores? Are they independent?
16. How is the threshold chosen? What is EER?
17. Why does each model have its own threshold?
18. Why was the "prediction must match the claim" condition dropped?
19. Define FAR and FRR. What happens to each when the threshold goes up?
20. What is the difference between enrolled false claims and external impostors?
21. Why are external impostors the hardest test?
22. Why report raw counts with percentages?
23. What is macro averaging?
24. What does the shuffled-label check prove?
25. Why is the test set used only once?
26. Why not deep learning?
27. What would you change for a real system?

---

## 15. Suggested 3-day study plan

- **Day 1 (concepts and data):** sections 1 to 6. Hand-calculate the 3-key example. Open a
  simulated `raw_keystrokes.csv` and `features.csv` and match rows to formulas.
- **Day 2 (machine learning):** sections 7 and 8. Draw the nested CV diagram (5 outer folds,
  4 inner folds). Explain KNN and RF scoring with small numbers. Plot FAR/FRR on paper.
- **Day 3 (system and viva):** sections 9 to 14. Run the simulated pipeline and the app.
  Each team member answers the viva questions aloud; split the topics so each person
  owns one part (capture and data, features, models and CV, evaluation and limitations).

---

## 16. References (IEEE style)

[1] F. Monrose and A. D. Rubin, "Keystroke dynamics as a biometric for authentication," Future Generation Computer Systems, vol. 16, no. 4, pp. 351–359, 2000, doi: 10.1016/S0167-739X(99)00059-X.
[2] P. S. Teh, A. B. J. Teoh, and S. Yue, "A survey of keystroke dynamics biometrics," The Scientific World Journal, vol. 2013, Art. no. 408280, 2013, doi: 10.1155/2013/408280.
[3] R. Shadman, A. A. Wahab, M. Manno, M. Lukaszewski, D. Hou, and F. Hussain, "Keystroke dynamics: Concepts, techniques, and applications," ACM Computing Surveys, vol. 57, no. 11, Art. no. 283, 2025, doi: 10.1145/3733103.
[4] K. S. Killourhy and R. A. Maxion, "Comparing anomaly-detection algorithms for keystroke dynamics," in Proc. IEEE/IFIP Int. Conf. Dependable Systems and Networks, 2009, pp. 125–134, doi: 10.1109/DSN.2009.5270346.
[5] T. M. Cover and P. E. Hart, "Nearest neighbor pattern classification," IEEE Transactions on Information Theory, vol. 13, no. 1, pp. 21–27, Jan. 1967, doi: 10.1109/TIT.1967.1053964.
[6] L. Breiman, "Random forests," Machine Learning, vol. 45, no. 1, pp. 5–32, 2001, doi: 10.1023/A:1010933404324.
[7] F. Pedregosa et al., "Scikit-learn: Machine learning in Python," Journal of Machine Learning Research, vol. 12, no. 85, pp. 2825–2830, 2011.
[8] S. Varma and R. Simon, "Bias in error estimation when using cross-validation for model selection," BMC Bioinformatics, vol. 7, Art. no. 91, 2006, doi: 10.1186/1471-2105-7-91.

(Three of these were only partly verified: check the article number and year of [3], and the DOIs of [1] and [4], on the publisher pages.)
