# SEGEL Hardening State Tracker

- **Branch**: `hardening/p2b-p5`
- **Active Phase**: Phase A — Suspect Every Test (Read-only Audit)
- **Last Updated**: 2026-11-05T21:16:00+07:00

---

## 1. Phase Progress
- [x] **Setup Baseline**: Git repository initialized, branch `hardening/p2b-p5` created, clean working tree.
- [x] **Phase A**: Full validity audit of all 43 tests in `tests/adversarial/test_at_NNN.py` -> `docs/test_validity.md`.
- [ ] **Phase B**: Mutation testing via throw-away worktrees -> Mutation score and table.
- [ ] **Phase C**: Red tests for untested gaps (C1–C5) in `tests/gaps/` (`gap` pytest marker).
- [ ] **Gate 1**: Stop and report to user. Awaiting explicit "GO-1".
- [ ] **Phase D**: Reconcile IDs and Error Codes (post-GO-1).
- [ ] **Phase E**: Security Review (read-only) -> `docs/security_review.md`.
- [ ] **Gate 2**: Stop and report to user. Awaiting explicit "GO-2".
- [ ] **Phase F**: Systematic implementation of fixes one at a time.

---

## 2. Default Decisions (User Specified)
- **D1 (SEC-004)**: Move only approver keys out of Release Desk process into a separate signer process. Remaining demo keys documented as a limitation in `docs/limitations.md`.
- **D2 (AI Pipeline)**: Stays deterministic-only. Tests AT-016..AT-019 relabelled "validator-level" and listed under limitations.
- **D3 (Crash-Safe Journal & Audit Log)**: Implement crash-safe journal (FR-083) and hash-chained audit log (SEC-017).

---

## 3. Current Working Item
- Executing Phase A audit of `tests/adversarial/test_at_NNN.py` against PRD v2.0 Section 27.2 Table 50 to generate `docs/test_validity.md`.
