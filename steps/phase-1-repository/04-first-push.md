# Step 1.04 — First Push

| | |
|---|---|
| **Goal** | All design artefacts are on GitHub, committed as a readable history rather than one opaque blob |
| **Day / Time** | Day 6 (Wed 11 Nov) · ~45 min |
| **Prerequisites** | [Step 1.03](03-github-repo.md) — the remote exists |
| **Produces** | `origin/main` with the design phase committed |

---

## Do this

### 1. Confirm what is about to be committed (~5 min)

```powershell
git status --short
```

Read the list. You are looking for three things:

- `.env` is **absent** (Step 1.02 should have handled this)
- `.venv/`, `node_modules/`, `__pycache__/` are **absent** (they do not exist yet, but confirm)
- Every existing file **is** present: the 65 design and process files, plus
  `README.md`, `.gitignore`, `.env.example`, and the three `.gitkeep` placeholders

```powershell
# Belt and braces — confirm no secret is staged
git status --short | Select-String -Pattern '\.env$'
```

That must print nothing.

### 2. Commit in logical groups (~30 min)

**Do not make one giant "initial commit".** Seven focused commits take ten extra
minutes and give you a history that reads like a process — which is exactly the
evidence CCS670 wants. It also makes the repository browsable: someone can see the
design phase happen in order.

```powershell
# 1. Repository scaffolding
git add .gitignore .env.example
git commit -m "chore(repo): add gitignore, env template, and folder structure"

# 2. Project concept and stack
git add docs/proposal/
git commit -m "docs(design): add concept paper, proposal deck, and completed technology stack"

# 3. UML
git add docs/uml/
git commit -m "docs(uml): add use case, class, sequence, and activity diagrams"

# 4. Database design
git add database/
git commit -m "docs(db): add EER diagrams, 26-table schema listing, and consistency audit"

# 5. UI mockups
git add docs/mockups/
git commit -m "docs(design): add passenger and driver UI mockups"

# 6. Planning and review
git add docs/review/ docs/plan/ steps/
git commit -m "docs(plan): add folder audit, stack review, roadmap, and build steps"

# 7. Root README last — it describes everything above
git add README.md
git commit -m "docs: add root README describing the project and repository layout"
```

> **Why `README.md` goes last.** Each commit should be coherent on its own. A
> README that describes files which do not exist yet in the history is a small
> inconsistency — the kind of detail that is easy to get right and noticeable when
> it is wrong.

### 3. Confirm the history before pushing (~5 min)

```powershell
git log --oneline
```

Expect seven lines, newest first, each a clear statement of what that commit did.

```powershell
git status
```

Expect `working tree clean`.

### 4. Push (~5 min)

```powershell
git push -u origin main
```

`-u` sets the upstream, so every later `git push` needs no arguments. You only do
this once.

---

## Verify

```powershell
# Local and remote agree
git log --oneline
git ls-remote origin

# The remote has the branch
git branch -r
```

Then open the repository in a browser and confirm:

- [ ] The README renders on the repository home page
- [ ] `docs/`, `database/`, `steps/` all appear
- [ ] **`.env` does NOT appear anywhere**
- [ ] `.env.example` **does** appear
- [ ] The commit list shows seven focused commits, not one
- [ ] Clicking into `database/diagrams/` shows both the `.puml` and the `.png`
- [ ] The images actually render on GitHub (not broken-image icons)

That last check matters: if the `.png` files were committed via Git LFS or with a
corrupted encoding, GitHub shows a broken image and an assessor sees nothing.

---

## Log it

```markdown
**Step 1.04 — first push — DONE**

- Committed the design phase as 7 focused commits (repo, design, UML, db, mockups,
  plan, README)
- Pushed to origin/main; upstream set
- Verified: .env absent from the remote, README renders, all diagram PNGs display
- **First commit SHA:** <sha>
- **Head SHA:** <sha>
```

Then fill in the **commit column** of `docs/plan/design-freeze.md` — Step 0.03 left
it blank specifically for now.

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `.env` is in the staged list | Step 1.02's ignore did not apply | `git rm --cached .env`, fix `.gitignore`, re-commit. **Rotate the password** |
| `src refspec main does not match any` | No commits yet, or branch is named differently | `git log --oneline` to check commits exist; `git branch --show-current` to check the name |
| `failed to push some refs` / rejected | The remote has commits you don't | You initialised with a README. `git pull origin main --allow-unrelated-histories`, resolve, push |
| Authentication prompt loops | HTTPS credentials | `gh auth login`, or set up a Personal Access Token |
| Images show as broken on GitHub | Very large files, or LFS pointers | Confirm the `.png` files are under 100 MB (yours are — the largest is 932 KB) and were not added via LFS |
| Committed something you shouldn't have | — | `git rm --cached <file>`, add to `.gitignore`, commit. If it contained a secret, rotate it — history rewrites are not worth it in a graded project |

---

## After this step

The milestone M1 exit criterion is now testable: **can a stranger clone this and
understand it?** Do that literally — clone to a temp folder, open the README, and
follow it. If you get lost, the README needs a line, not the project.

```powershell
git clone https://github.com/<you>/sakay-ph.git "$env:TEMP\sakay-clone-check"
```

Then delete it. Five minutes, and it catches broken relative links in the README
before an assessor does.
