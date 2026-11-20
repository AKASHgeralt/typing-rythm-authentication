# Adding a new employee

Each account has its own models, so a new employee only needs **their own**
models. Existing accounts and the thresholds are not changed.

## 1. Register the account

```
python -m src.users add --name Rahul --email rahul@gmail.com
```
It asks for the password twice (not shown on screen) and prints the new ID,
for example `U06`. The password is stored only as a hash.

## 2. Enrollment typing

Start the app (`python app.py`), open **Data collection**, choose the new person
and **Session 1**, tick consent, practise 3 to 5 times, then **Record** their own
password until it shows **30 / 30**. The other tasks on their list are optional.

Optional but recommended: colleagues type the new person's password a few times
(their task lists now include it). With at least **5** such attempts, both models
can be trained and checked. With fewer, only the KNN distance model is trained.

## 3. Train only the new account

```
python -m src.features
python -m src.train --user U06
```

What it does:

| Impostor attempts for U06 | Result |
|---|---|
| 5 or more | KNN and Random Forest trained with nested cross-validation; FRR and FAR printed for a quick check |
| fewer than 5 | Only the KNN distance model, learned from the owner's attempts alone (k = 3) |

The existing thresholds in `models/thresholds.json` are kept and reused.
U06 is added to the list of accounts, and the login page can be used straight away.

## 4. When to retrain everything

`python -m src.train` (without `--user`) retrains all accounts and chooses new
thresholds from everyone's data. Do this when several new people have joined.
For the project's reported results, keep the original five accounts.
