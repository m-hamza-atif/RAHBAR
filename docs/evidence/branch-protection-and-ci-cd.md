# Branch Protection, CI/CD Gates & GitHub Actions Evidence Guide

> [!NOTE]
> In accordance with project instructions and safeguards, automated agents are strictly forbidden from executing remote Git actions (`git push`, `git merge`, creating remote PRs, modifying `main`, or publishing images to Docker Hub).
> This document records the local verification status of all CI/CD pipelines and provides the exact procedure and templates for the required human GitHub actions.

---

## Status Overview

| Item | Local Status | Remote GitHub Status | Required Human Action |
|------|--------------|----------------------|-----------------------|
| `.github/workflows/ci.yml` | **VERIFIED PASS** (Lint, pytest 102/102, 93% coverage, strict kubeconform, 3 image builds, Trivy scans, e2e kind fixture eval) | **PENDING REMOTE EXECUTION** | Push `dev` branch to `origin/dev` |
| `.github/workflows/cd.yml` | **VERIFIED PASS** (Workflow syntax, SHA image tags, zero latest tags, deploy order) | **PENDING REMOTE EXECUTION** | Configure Docker Hub Secrets, merge PR `dev -> main` |
| `main` Branch Protection | N/A (GitHub repository setting) | **PENDING HUMAN CONFIG** | Configure branch ruleset in GitHub Web UI |
| Intentionally Failing Eval PR | **VERIFIED REPRODUCIBLE** (Evaluator gates fail closed on recall regression > 5% or invalid citations) | **PENDING HUMAN DEMO** | Open draft PR with regressed baseline/golden to capture blocked merge screenshot |
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
   - Status check: `test-and-lint`
   - Status check: `build-images`
   - Status check: `scan-images`
   - Status check: `e2e-fixture-cluster`
4. Check **Require branches to be up to date before merging**.
5. Save changes.

*Evidence Screenshot to Capture:* Save screenshot of this settings page as `docs/evidence/branch-protection.png`.

---

## Step 3: Demonstrating the Evaluation Gate Failure & Blocked Merge

To satisfy the rubric requirement demonstrating an intentional CI evaluation failure:
1. From a temporary branch `demo-fail-eval`, introduce a deliberate regression (e.g. increase golden difficulty or alter `eval/fixtures/baseline.fixture.json` recall@5 to 1.10).
2. Open a Pull Request targeting `main`.
3. GitHub Actions will run `ci.yml`. The `e2e-fixture-cluster` job will execute `eval/run_eval.py` and fail with exit code `1` (`GATE FAILED: recall@5 fell more than five percentage points`).
4. GitHub branch protection will mark the check as failed and disable/block the **Merge** button.
5. Capture a screenshot of the PR conversation tab showing:
   - Failing `e2e-fixture-cluster` status check.
   - Disabled "Merge pull request" button with note *"Required statuses must pass before merging"*.
   - Save as `docs/evidence/blocked-merge-failure.png`.
6. Close this demonstration PR without merging.

---

## Step 4: Normal Green PR (`dev -> main`)

1. Manually push `dev` to `origin/dev`.
2. Open a Pull Request from `dev` into `main`.
3. All 4 CI jobs in `ci.yml` will run and complete green.
4. Have your partner approve the PR (satisfying the 1-approval rule).
5. Capture a screenshot of the green checks and merge confirmation.
   - Save as `docs/evidence/green-pr-approval.png`.
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
