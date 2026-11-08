# Submission links and release status

Checked after the human pushed `8827fb6` and opened
[PR #1: dev into main](https://github.com/m-hamza-atif/RAHBAR/pull/1).
The local installer follow-up still needs a manual commit/push.

| Item | Link | Status |
| --- | --- | --- |
| GitHub repository | https://github.com/m-hamza-atif/RAHBAR | Public; PR open |
| Successful CD run | Pending: copy its actual successful run URL after merging main | Not verified yet |
| API image SHA tag | https://hub.docker.com/r/mhamzaatif/rahbar-api/tags | Public; no tags yet |
| Indexer image SHA tag | https://hub.docker.com/r/mhamzaatif/rahbar-indexer/tags | Public; no tags yet |
| UI image SHA tag | https://hub.docker.com/r/mhamzaatif/rahbar-ui/tags | Public; no tags yet |
| Results | https://github.com/m-hamza-atif/RAHBAR/blob/dev/eval/results.json | Committed on dev |
| Baseline | https://github.com/m-hamza-atif/RAHBAR/blob/dev/eval/baseline.json | Committed and unchanged |

After release, use main-branch file links and verify every image tag matches the
main commit SHA shown by the successful CD run. Empty repositories are not yet
submission evidence. CI success does not replace CD success.

## Verified findings

- The active main ruleset requires one approval and all six checks: lint, test,
  manifests, build, scan, e2e-eval; up-to-date checks are enabled.
- PR [run 42473746954](https://github.com/m-hamza-atif/RAHBAR/actions/runs/42473746954):
  lint, test, build and scan passed. Manifests failed during tool installation;
  e2e-eval was skipped.
- Push [run 42472472309](https://github.com/m-hamza-atif/RAHBAR/actions/runs/42472472309):
  manifests and scan failed at tool installation, not their validation/scan commands.
- The user supplied the curl HTTP 504. Local fixes add bounded retries, a pinned
  GitHub release-asset API fallback and per-job tool selection. Complete downloads
  and extraction precede replacing a tool; failed acquisition still fails the job.
  Three Linux regression cases, bash syntax, Ruff and actionlint passed. A real
  pinned actionlint 1.7.7 download/install succeeded.
- All three Docker Hub repositories were verified public with empty tag lists.
  No Hub mutation is needed before CD publishes. Secret values cannot be read
  back; the real CD login/push will validate the credentials the user added.

## Screenshots and next steps

`blocked-merge.png` is genuine, but shows download failures/missing approval.
It does not yet show an evaluation regression: that job was skipped.
`branch-protection.png` shows the ruleset listing; open the rule to capture its
main target, approval count and six checks for stronger evidence. The API confirms
those settings. `green-checks.png` is still missing.

1. Commit/push the installer fix, test, documentation and supplied PNGs manually;
   private CODEX_REQUESTS.md has the exact commands. Wait for fresh CI.
2. Before merging, follow the reversible fixture-heading demonstration in
   `evidence/branch-protection-and-ci-cd.md` for the failed eval and green screenshots.
   Commit the final screenshots to dev. Preserve the frozen baseline.
3. Partner B approves PR #1; merge it manually after checks pass.
4. CD automatically tests, scans, publishes and deploys SHA-tagged images. Copy
   the successful run URL and verify that SHA on all three Hub tag pages.
5. Request a final link/status check before submitting. No manual image upload
   or additional local model download is required.
