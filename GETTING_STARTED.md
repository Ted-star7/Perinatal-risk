# Getting started

Read this once before you touch anything. It covers setup, where the data
goes, and the git steps you repeat every day.

## 1. Clone the repo

```bash
git clone git@github.com:Ted-star7/Perinatal-risk.git
cd Perinatal-risk
```

(If `git@` gives an SSH error, use
`git clone https://github.com/Ted-star7/Perinatal-risk.git`.)

## 2. Put the data in (one time)

The DHS data is **not** in the repo — it's licensed, so git ignores it. Teddy
shares the `G13_Team_Data.zip` separately. Unzip it so the CSVs land here:

```
Perinatal-risk/data/processed/ke_perinatal.csv
Perinatal-risk/data/processed/ke_perinatal_anc.csv
Perinatal-risk/data/processed/ke_lbw.csv
Perinatal-risk/data/processed/tz_perinatal.csv
Perinatal-risk/data/processed/tz_perinatal_anc.csv
Perinatal-risk/data/processed/tz_lbw.csv
```

That `data/processed/` folder already exists in the repo — just drop the files
in. They stay on your computer only; git will never commit them, so you can't
leak them by accident.

## 3. Find your notebook

One notebook per person, so nobody edits the same file.

- Kenya squad → `ml/notebooks/kenya/` (perinatal, perinatal_anc, lbw)
- Tanzania squad → `ml/notebooks/tanzania/` (perinatal, perinatal_anc, lbw)

Take one cohort and work only in that file.

## 4. The git loop (every work session)

**Start — get up to date first:**
```bash
git checkout main
git pull origin main
git checkout -b yourname-cohort      # e.g. dennis-ke-anc   (first time only)
```
If your branch already exists, skip the `-b` line and instead catch it up:
```bash
git checkout yourname-cohort
git merge main                       # pull the team's merged work into your branch
```

**Work**, then **save and send:**
```bash
git add ml/notebooks/kenya/eda_perinatal_anc.ipynb
git commit -m "Kenya ANC cohort EDA"
git push -u origin yourname-cohort   # first push; after that just: git push
```

**Open a Pull Request** on GitHub (your branch → `main`). Teddy reviews and
merges. Then delete the branch and start fresh next time from `main`.

### merge vs push (they're opposite directions)
- `git merge main` — **receive**: pulls the team's finished work *into* your branch.
- `git push` — **send**: puts *your* work up on GitHub.
Do merge at the start (stay current), push at the end (share your work).

## 5. Rules

- Never push straight to `main`. Always branch → PR → Teddy merges.
- Clear notebook outputs before committing (Cell → All Output → Clear).
- Never commit data, `.zip`, or `.csv` files — git ignores them; don't force it.
- Stay in your own notebook. The only shared file is the README, which Teddy edits.

## 6. What happens after EDA

The 6 EDA notebooks stay as 6 files in `main` — we don't merge them into one.
Once all are in and the squads agree the data looks right, we move to
`ml/notebooks/modeling/`: build the checklist baseline, train the model, and
validate it on Tanzania. That produces one saved model + a metrics file, which
is the input to the next phase (the backend and the two portals).
