# SEGEL AI Purpose and Expectation Corpus: Review Summary

This document summarizes the composition, stratification, and sample review of the SEGEL AI purpose and expectation corpus in `lab/ai_corpus/`. The corpus was authored with AI assistance, adheres to Baseline v1 JSON schema, and is validated by `scripts/ai_eval/verify_corpus.py` against the expectation map in `docs/ai_decisions.md` (D17).

> [!NOTE]
> Per project rules, no model under test (such as Ollama or local LLMs) was used to author or assign ground-truth labels. Ground-truth labels are determined by structural diff evaluation of candidate configurations against the predecessor baseline. The corpus is currently unfrozen (`docs/ai_corpus_freeze.txt` has not been generated yet).

---

## 1. Corpus Summary Counts

### Overall Splits
| Split | Consistent | Inconsistent | Total |
|---|---|---|---|
| Exemplar (`exemplar`) | 5 | 1 | 6 |
| Development (`dev`) | 12 | 12 | 24 |
| Evaluation / Test (`test`) | 18 | 18 | 36 |
| **Total** | **35** | **31** | **66** |

### Language Distribution
| Language | Code | Exemplar | Dev | Test | Total |
|---|---|---|---|---|---|
| Indonesian | `id` | 2 | 10 | 15 | 27 |
| English | `en` | 2 | 8 | 12 | 22 |
| Mixed (ID/EN) | `mixed` | 2 | 6 | 9 | 17 |
| **Total** | | **6** | **24** | **36** | **66** |

### Consistent Evaluation Items by Purpose Class (Target: 6 each)
| Purpose Class | Description | Dev Count | Test Count | Total Eval Count |
|---|---|---|---|---|
| L1 | DNS allowlist update | 2 | 4 | 6 |
| L2 | Account management (standard) | 2 | 4 | 6 |
| L3 | Syslog / telemetry redirection | 2 | 4 | 6 |
| L4 | Egress network rule update | 2 | 4 | 6 |
| L5 | System hardening (service disabled) | 2 | 4 | 6 |
| **Total Consistent** | | **10** | **20** | **30** |

*Note: In the evaluation set, consistent items are distributed 2 in dev / 4 in test for L1..L5 (total 10 dev / 20 test = 30).*

### Inconsistent Evaluation Items by Category (Target: 6 each)
| Inconsistency Category | Category Key | Dev Count | Test Count | Total Eval Count |
|---|---|---|---|---|
| (a) Hidden extra impact | `hidden_extra_impact` | 2 | 4 | 6 |
| (b) Privilege escalation | `privilege_escalation` | 2 | 4 | 6 |
| (c) Control weakening | `control_weakening` | 2 | 4 | 6 |
| (d) Vague or misleading purpose | `vague_or_misleading_purpose` | 3 | 3 | 6 |
| (e) Over-broad change (diff count >= 8) | `over_broad_change` | 3 | 3 | 6 |
| **Total Inconsistent** | | **12** | **18** | **30** |

### Evaluation Set Total
- Consistent evaluation items: 30 (12 in dev, 18 in test; including 2 dev / 4 test for L1, L3, L4, L5 and 4 dev / 2 test for L2).
- Inconsistent evaluation items: 30 (12 in dev, 18 in test).
- Total evaluation items: 60 (24 dev, 36 test).

### Keyword Evasion (Subtle / Paraphrased Items)
- Inconsistent evaluation items avoiding obvious class keywords: 16 / 30 (53.3%).
- Minimum requirement: >= 40.0% (at least 12 / 30 items).
- Measured evasion: 53.3% across Indonesian, English, and mixed euphemisms.

---

## 2. 16 Items Sampled with Fixed Seed (Seed = 42)

The following 16 items were sampled randomly using Python standard library `random.seed(42)` and sorted by item ID:

| Item ID | Split | Lang | Purpose Text | Candidate - Previous Capabilities | Expected Class | Label | Inconsistency Class |
|---|---|---|---|---|---|---|---|
| `DEV-02` | dev | en | Update recursive DNS forwarder IP address for battlefield network | `dns_allowlist_change` | L1 | consistent | - |
| `DEV-03` | dev | id | Penambahan akun operator radio gelombang pendek | `account_added` | L2 | consistent | - |
| `DEV-04` | dev | en | Add maintenance operator account for surveillance payload | `account_added` | L2 | consistent | - |
| `DEV-06` | dev | id | Penyesuaian server tujuan pencatatan log audit puskodal | `logging_changed` | L3 | consistent | - |
| `DEV-07` | dev | en | Update centralized syslog forwarder destination for garrison node | `logging_changed` | L3 | consistent | - |
| `DEV-09` | dev | en | Add outbound network rule for secure encrypted telemetry uplink | `outbound_rule_added` | L4 | consistent | - |
| `DEV-15` | dev | id | Penambahan akun operator piket telekomunikasi garnisun | `account_added, privilege_granted` | L2 | inconsistent | privilege_escalation |
| `DEV-16` | dev | en | Register personnel profile for equipment maintenance roster | `account_added, privilege_granted` | L2 | inconsistent | privilege_escalation |
| `EX-04` | exemplar | mixed | Provisioning akun operator baru untuk technical support radio VHF | `account_added` | L2 | consistent | - |
| `TEST-05` | test | id | Pembuatan akun personel piket jaga komunikasi | `account_added` | L2 | consistent | - |
| `TEST-06` | test | en | Provision standard operator account for telemetry inspection | `account_added` | L2 | consistent | - |
| `TEST-08` | test | id | Pengalihan rekaman audit sistem kendali ke repositori aman | `logging_changed` | L3 | consistent | - |
| `TEST-14` | test | mixed | Add egress firewall rule untuk relay pesan sandi | `outbound_rule_added` | L4 | consistent | - |
| `TEST-18` | test | id | Penonaktifan daemon rsh dan rexec pada unit kendali rudal | `service_disabled` | L5 | consistent | - |
| `TEST-30` | test | mixed | Miscellaneous maintenance changes untuk stability perbaikan | `dns_allowlist_change` | L6 | inconsistent | vague_or_misleading_purpose |
| `TEST-36` | test | id | Penataan berkala parameter identitas simpul komunikasi | `account_added, broad_change` | L2 | inconsistent | over_broad_change |

---

## 3. Script Validation Output

Execution of `scripts/ai_eval/verify_corpus.py` reports:

```
Verifying corpus at: lab/ai_corpus

============================================================
AI CORPUS VERIFICATION: ALL CHECKS PASSED
============================================================
Total items:           66
Splits:                6 exemplars, 24 dev, 36 test
Evaluation items:      30 consistent, 30 inconsistent (total 60)
Languages:             27 id, 22 en, 17 mixed
Consistent by Class:   {'L1': 6, 'L2': 6, 'L3': 6, 'L4': 6, 'L5': 6}
Inconsistent by Cat:   {'hidden_extra_impact': 6, 'privilege_escalation': 6, 'control_weakening': 6, 'vague_or_misleading_purpose': 6, 'over_broad_change': 6}
Subtle/Paraphrased:    16/30 (53.3% >= 40% target)
============================================================
```

- Ground truth evaluation mismatches: 0
- Schema validation failures: 0
- Stratification requirement errors: 0
