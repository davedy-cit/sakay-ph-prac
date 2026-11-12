# Step 1.03 — Create the GitHub Repository

| | |
|---|---|
| **Goal** | An empty remote repository exists on GitHub, ready to receive the first push |
| **Day / Time** | Day 6 (Wed 11 Nov) · ~30 min |
| **Prerequisites** | [Step 1.02](02-gitignore-and-env-example.md) |
| **Produces** | A GitHub remote at `origin` |

---

## Before you start

**Check your instructor's requirements first.** Many CCS670 sections require a
specific repository name, a specific visibility, or an invitation to a course
organisation. If there is a rule, follow it — the convention below is only a
default for when there is not.

---

## Decisions to make

| Decision | Recommendation | Why |
|---|---|---|
| **Name** | `sakay-ph` | Matches the project. `ccs670-sakay-ph` also works if you want the subject visible. The local folder stays `ride-hailingSystem` — the repo name is independent |
| **Visibility** | **Public** | Simplest to submit — one link, no invitation step. If your instructor requires private, choose private and invite them as a collaborator |
| **Initialise with a README?** | **No** | You already have one. Initialising creates a commit that conflicts with your local history and forces a merge on the very first push |
| **Add `.gitignore` / licence from GitHub?** | **No** | You wrote your own in Step 1.02. GitHub's would conflict |
| **Licence** | Optional | Academic work usually needs none. Add MIT if you want to signal reuse; skip it if unsure |

---

## Do this

### Option A — GitHub CLI (recommended)

Fewer steps and no copy-pasting URLs.

```powershell
# 1. Check whether gh is installed
gh --version
```

If it is not installed:

```powershell
winget install --id GitHub.cli
```

Then **close and reopen the terminal** — `gh` needs a fresh PATH.

```powershell
# 2. Authenticate (opens a browser)
gh auth login
```

Choose: **GitHub.com** → **HTTPS** → **Login with a web browser**. Follow the
prompt and paste the one-time code.

```powershell
# 3. Confirm who you are
gh auth status

# 4. Create the repository from the project root
Set-Location "C:\Users\MCC IT Admin\Downloads\MIT\CCS670-Object-Orented Software Development\Project\ride-hailingSystem"
gh repo create sakay-ph --public --source=. --remote=origin --description "Sakay.ph — Isang App, Lahat ng Sakyan. A multi-mode ride-hailing platform for every Filipino transport mode. CCS670 capstone."
```

The flags mean:

| Flag | Effect |
|---|---|
| `--source=.` | Use the current directory as the source |
| `--remote=origin` | Add it as the remote named `origin` |
| `--public` | Public visibility |
| *no* `--push` | Create the remote but **do not push yet** — Step 1.04 does that, after you have staged commits |

```powershell
# 5. Confirm the remote
git remote -v
```

### Option B — the web UI

1. Go to **github.com/new**
2. **Repository name:** `sakay-ph`
3. **Description:** the one-liner above
4. **Public** (or Private, per your instructor)
5. **Do NOT** tick "Add a README file"
6. **Do NOT** choose a `.gitignore` or licence template
7. Click **Create repository**
8. On the empty-repo page, copy the HTTPS URL
9. Back in PowerShell:

```powershell
Set-Location "C:\Users\MCC IT Admin\Downloads\MIT\CCS670-Object-Orented Software Development\Project\ride-hailingSystem"
git remote add origin https://github.com/<your-username>/sakay-ph.git
git remote -v
```

---

## Verify

```powershell
# The remote exists and is named origin
git remote -v

# Expected — both lines, fetch and push:
# origin  https://github.com/<you>/sakay-ph.git (fetch)
# origin  https://github.com/<you>/sakay-ph.git (push)

# The remote is reachable and empty
git ls-remote origin
```

`git ls-remote origin` on a brand-new empty repository prints nothing and exits 0.
That is success — an empty repository has no refs. If it prompts for a password,
your authentication is not set up; see "If it goes wrong".

- [ ] `git remote -v` shows `origin` for both fetch and push
- [ ] `git ls-remote origin` succeeds without an auth prompt
- [ ] The repository page on GitHub shows the empty-repo instructions
- [ ] The repository is **not** initialised with a README

---

## Log it

```markdown
**Step 1.03 — GitHub repository — DONE**

- Created public repo `sakay-ph` via gh CLI
- Remote `origin` added; `git ls-remote origin` confirms reachable and empty
- Deliberately did not initialise with README/gitignore — local files already exist
- **Commit:** (no commit — remote setup only)
```

Add a row to the decision log: repo name, visibility, and why.

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `gh` not recognised after install | PATH not refreshed | Close and reopen the terminal entirely |
| Push prompts for a username/password | HTTPS auth not configured | Use `gh auth login`, or a Personal Access Token as the password (your GitHub account password will not work) |
| `remote origin already exists` | Ran `git remote add` twice | `git remote set-url origin <url>` instead |
| Repository was created with a README | You ticked the box | `git pull origin main --allow-unrelated-histories`, then resolve the conflict. Easier to delete the repo and recreate it correctly |
| `gh repo create` fails: name taken | Someone else has `sakay-ph` | Use `sakay-ph-ccs670` or `sakay-ph-<your-initials>` |
| Want to rename later | — | Rename on GitHub, then `git remote set-url origin <new-url>` |

---

## On visibility

If your instructor requires **private**, you must invite them:

```powershell
gh repo edit --visibility private
gh api repos/<you>/sakay-ph/collaborators/<instructor-username> -X PUT -f permission=push
```

Submitting a private repository without granting access is a common and entirely
avoidable way to lose marks — the assessor opens the link and sees a 404. If in
doubt, make it public, or confirm the invitation was accepted before submitting.
