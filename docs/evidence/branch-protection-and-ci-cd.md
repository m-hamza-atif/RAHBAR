# Branch Protection, CI/CD Gates & GitHub Actions Evidence Guide

> [!NOTE]
> In accordance with project instructions and safeguards, automated agents are strictly forbidden from executing remote Git actions (`git push`, `git merge`, creating remote PRs, modifying `main`, or publishing images to Docker Hub).
> This document records the local verification status of all CI/CD pipelines and provides the exact procedure and templates for the required human GitHub actions.

---

## Status Overview

| Item | Local Status | Remote GitHub Status | Required Human Action |
|------|--------------|----------------------|-----------------------|
| `.github/workflows/ci.yml` | Tests, lint, image and fixture checks recorded separately | **SUCCESS at 2efaa98** (before final review fixes) | Push reviewed changes manually and wait for a fresh green run |
| `.github/workflows/cd.yml` | Reviewed syntax, SHA tags and deploy order; this does not prove publication/deployment | **NO SUCCESS VERIFIED** | Configure Docker Hub Secrets, merge approved PR `dev -> main`, verify the actual run |
| `main` Branch Protection | N/A (GitHub repository setting) | **PENDING HUMAN CONFIG** | Configure branch ruleset in GitHub Web UI |
| Intentionally Failing Eval PR | Evaluator gates fail closed on recall regression > 5% or invalid citations | **PENDING HUMAN DEMO** | Use an isolated retrieval regression; preserve frozen baselines/golden sets |
| Green PR & Approved Merge | N/A | **PENDING HUMAN REVIEW** | Partner A or B approves and merges PR `dev -> main` |
| Docker Hub Published SHA Tags | Images built locally as `linux/amd64` | **PENDING REMOTE PUBLISH** | Automatic on merge to `main` via `cd.yml` |

---

## Step 1: GitHub Secrets Configuration

Before merging to `main`, set the following repository secrets in **Settings > Secrets and variables > Actions**:
1. `DOCKERHUB_USERNAME`: Your Docker Hub username or organization.
2. `DOCKERHUB_TOKEN`: Personal Access Token from Docker Hub with Read & Write permissions.

*(In CI on `dev`, images are built and tested in an isolated ephemeral kind cluster without needing Docker Hub credentials).*

---

## Step 2: Branch Protection Rules for `main`

Navigate to **Settings > Branches** (or **Rulesets**) and add a branch protection rule for `main`:
1. Check **Require a pull request before merging**.
2. Check **Require approvals** (set minimum to `1`).
3. Check **Require status checks to pass before merging**:
   - Status checks: `lint`, `test`, `manifests`, `build`, `scan`, `e2e-eval`.
   - Select these actual CI check names after they appear on GitHub; do not create
     rules requiring the obsolete names from earlier drafts of this guide.
4. Check **Require branches to be up to date before merging**.
5. Save changes.

*Evidence Screenshot to Capture:* Save screenshot of this settings page as `docs/evidence/branch-protection.png`.

---

## Step 3: Demonstrating the Evaluation Gate Failure & Blocked Merge

To satisfy the rubric requirement demonstrating an intentional CI evaluation failure:
1. From a temporary branch `demo-fail-eval`, introduce an isolated section-metadata
   regression: in `eval/fixtures/fees-2026.md`, rename the heading `## 1. Tuition`
   to `## Demonstration regression`. Keep the frozen golden set and baseline
   unchanged. The expected source/section can no longer be retrieved. Confirm the
   actual evaluator output before claiming the demonstration.
2. Open a Pull Request targeting `main`.
3. GitHub Actions will run `ci.yml`. The `e2e-eval` job executes `eval/run_eval.py`;
   confirm its recall regression gate fails rather than an unrelated build step.
4. GitHub branch protection will mark the check as failed and disable/block the **Merge** button.
5. Capture a screenshot of the PR conversation tab showing:
   - Failing `e2e-eval` status check.
   - Disabled "Merge pull request" button with note *"Required statuses must pass before merging"*.
   - Save as `docs/evidence/blocked-merge.png`.
6. Restore the original heading on the same demonstration branch, then manually
   commit/push the correction. Wait for green checks on that same PR and capture
   `docs/evidence/green-checks.png`. Close the demonstration PR without merging.
   The normal release PR below remains a separate reviewed `dev -> main` change.

---

## Step 4: Normal Green PR (`dev -> main`)

1. Manually push `dev` to `origin/dev`.
2. Open a Pull Request from `dev` into `main`.
3. All six CI jobs in `ci.yml` must complete green.
4. Have your partner approve the PR (satisfying the 1-approval rule).
5. Capture a screenshot of the green checks and merge confirmation.
   - Save as `docs/evidence/green-checks.png`.
6. Merge the PR.

---

## Step 5: Remote CD Deployment & Docker Hub Published Images

Upon merge to `main`:
1. `.github/workflows/cd.yml` triggers automatically on `push: branches: [main]`.
2. It builds all three containers tagged with the exact Git commit SHA:
   - `<DOCKERHUB_USERNAME>/rahbar-api:<SHA>`
   - `<DOCKERHUB_USERNAME>/rahbar-indexer:<SHA>`
   - `<DOCKERHUB_USERNAME>/rahbar-ui:<SHA>`
3. Pushes the SHA-tagged images to Docker Hub.
4. Deploys to an ephemeral test cluster using those published images, runs the bootstrap indexer job, and verifies HTTP 200 on Ingress `/` and `/readyz`.
5. Record the link to the successful CD workflow run and the Docker Hub image repository URLs in the final submission notes.

## Verified public state during final review

On 2026-11-08 the public [CI page](https://github.com/m-hamza-atif/RAHBAR/actions/workflows/ci.yml)
showed a successful run at commit `2efaa98`. The public
[pull request page](https://github.com/m-hamza-atif/RAHBAR/pulls) showed zero open
and zero closed PRs. No successful CD run was verified. The three screenshot PNGs
listed above were absent from this checkout. These are pending real release and
evidence steps, not reasons to fabricate screenshots or alter evaluation results.
