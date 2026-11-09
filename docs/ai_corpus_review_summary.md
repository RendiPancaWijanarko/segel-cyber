# SEGEL AI Purpose and Expectation Corpus: Review Summary

This document summarizes the composition, stratification, and sample review of the SEGEL AI purpose and expectation corpus in `lab/ai_corpus/`. The corpus was authored with AI assistance, adheres to Baseline v1 JSON schema, and is validated by `scripts/ai_eval/verify_corpus.py` against the expectation map in `docs/ai_decisions.md` (D17, D9b).

> [!NOTE]
> Per project rules, no model under test (such as Ollama or local LLMs) was used to author or assign ground-truth labels. Ground-truth labels and `mismatch_kind` are determined by structural diff evaluation of candidate configurations against the predecessor baseline. Keyword evasion is measured in AI-4 against the independently written docs/b1_keywords.md.

---

## 1. Corpus Summary Counts

### Overall Splits
| Split | Consistent | Inconsistent | Total |
|---|---|---|---|
| Exemplar (`exemplar`) | 5 | 1 | 6 |
| Development (`dev`) | 12 | 12 | 24 |
| Evaluation / Test (`test`) | 18 | 18 | 36 |
| **Total** | **35** | **31** | **66** |

### Mismatch Kind per Split (D9b Rebalancing)
| Split | `none` (Consistent) | `silent` (Pass-Severity Extra) | `deterministic` (Warn/Reject Extra) | Total |
|---|---|---|---|---|
| Exemplar (`exemplar`) | 5 | 1 | 0 | 6 |
| Development (`dev`) | 12 | 7 | 5 | 24 |
| Evaluation / Test (`test`) | 18 | 11 | 7 | 36 |
| **Total** | **35** | **19** | **12** | **66** |

### Language Distribution
| Language | Code | Exemplar | Dev | Test | Total |
|---|---|---|---|---|---|
| Indonesian | `id` | 2 | 10 | 16 | 28 |
| English | `en` | 2 | 11 | 13 | 26 |
| Mixed (ID/EN) | `mixed` | 2 | 3 | 7 | 12 |
| **Total** | | **6** | **24** | **36** | **66** |

### Expected Purpose Class Distribution
| Class | Description | Exemplar | Dev | Test | Total |
|---|---|---|---|---|---|
| L1 | DNS allowlist update | 1 | 5 | 6 | 12 |
| L2 | Account management (standard) | 1 | 5 | 8 | 14 |
| L3 | Syslog / telemetry redirection | 1 | 4 | 10 | 15 |
| L4 | Egress network rule update | 1 | 4 | 5 | 10 |
| L5 | System hardening (service disabled) | 1 | 4 | 6 | 11 |
| L6 | Vague or unclassified purpose | 1 | 2 | 1 | 4 |
| **Total** | | **6** | **24** | **36** | **66** |

### Consistent Evaluation Items by Purpose Class (Target: 6 each, Total: 30)
| Purpose Class | Description | Dev Count | Test Count | Total Eval Count |
|---|---|---|---|---|
| L1 | DNS allowlist update | 2 | 4 | 6 |
| L2 | Account management (standard) | 3 | 3 | 6 |
| L3 | Syslog / telemetry redirection | 2 | 4 | 6 |
| L4 | Egress network rule update | 3 | 3 | 6 |
| L5 | System hardening (service disabled) | 2 | 4 | 6 |
| **Total Consistent** | | **12** | **18** | **30** |

### Inconsistent Evaluation Items by Category (D9b Target: Dev 12, Test 18)
| Inconsistency Category | Category Key | Mismatch Kind | Dev Count | Test Count | Total Eval Count |
|---|---|---|---|---|---|
| (a) Hidden extra impact | `hidden_extra_impact` | `silent` | 4 | 8 | 12 |
| (b) Vague or misleading purpose | `vague_or_misleading_purpose` | `silent` | 3 | 3 | 6 |
| (c) Privilege escalation | `privilege_escalation` | `deterministic` | 2 | 2 | 4 |
| (d) Control weakening | `control_weakening` | `deterministic` | 1 | 3 | 4 |
| (e) Over-broad change (diff >= 8) | `over_broad_change` | `deterministic` | 2 | 2 | 4 |
| **Total Inconsistent** | | | **12** | **18** | **30** |

---

## 2. 16 Items Sampled with Fixed Seed (Seed = 42)

The following 16 items were sampled randomly using Python standard library `random.seed(42)` and sorted by item ID:

| Item ID | Split | Lang | Purpose Text | Candidate - Previous Capabilities | Expected Class | Label | Inconsistency Class | Mismatch Kind |
|---|---|---|---|---|---|---|---|---|
| `DEV-02` | dev | en | Register additional DNS forwarder for branch office network | `dns_allowlist_change` | L1 | consistent | - | `none` |
| `DEV-03` | dev | id | Penambahan akun operator perangkat telekomunikasi router regional | `account_added` | L2 | consistent | - | `none` |
| `DEV-04` | dev | en | Create operator account for remote maintenance access to branch node | `account_added` | L2 | consistent | - | `none` |
| `DEV-06` | dev | en | Update centralized syslog forwarder destination for gateway node | `logging_changed` | L3 | consistent | - | `none` |
| `DEV-07` | dev | id | Penambahan aturan firewall keluar untuk transmisi data telemetri | `outbound_rule_added` | L4 | consistent | - | `none` |
| `DEV-09` | dev | id | Penonaktifan layanan protokol legacy telnet dan rsh pada node | `service_disabled` | L5 | consistent | - | `none` |
| `DEV-15` | dev | mixed | Adjustment of audit log destination untuk branch office node | `logging_changed, outbound_rule_added` | L3 | inconsistent | hidden_extra_impact | `silent` |
| `DEV-16` | dev | en | Reduce attack surface by decommissioning unneeded system services | `account_added, service_disabled` | L5 | inconsistent | hidden_extra_impact | `silent` |
| `EX-04` | exemplar | mixed | Provisioning akun operator baru untuk technical support jaringan intranet | `account_added` | L2 | consistent | - | `none` |
| `TEST-05` | test | id | Pembuatan akun personel piket jaga komunikasi shift malam | `account_added` | L2 | consistent | - | `none` |
| `TEST-06` | test | en | Provision standard operator account for telemetry inspection team | `account_added` | L2 | consistent | - | `none` |
| `TEST-08` | test | id | Pengalihan rekaman audit sistem kendali ke repositori terpusat | `logging_changed` | L3 | consistent | - | `none` |
| `TEST-14` | test | mixed | Add outbound rule untuk upstream metrics aggregation server | `outbound_rule_added` | L4 | consistent | - | `none` |
| `TEST-18` | test | mixed | Disabling legacy print service lpd untuk hardening branch node | `service_disabled` | L5 | consistent | - | `none` |
| `TEST-30` | test | id | Reorganisasi direktori akses identitas pengguna sistem monitoring | `account_added, privilege_granted` | L2 | inconsistent | privilege_escalation | `deterministic` |
| `TEST-36` | test | en | Minor refresh of field gateway connection parameters for branch nodes | `broad_change, outbound_rule_added` | L4 | inconsistent | over_broad_change | `deterministic` |

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
Languages:             28 id, 26 en, 12 mixed
Consistent by Class:   {'L1': 6, 'L2': 6, 'L3': 6, 'L4': 6, 'L5': 6}
Inconsistent by Cat:   {'hidden_extra_impact': 12, 'vague_or_misleading_purpose': 6, 'privilege_escalation': 4, 'control_weakening': 4, 'over_broad_change': 4}

Counts per split x mismatch_kind:
  split               none     silent    deterministic
  exemplar               5          1                0
  dev                   12          7                5
  test                  18         11                7
============================================================
```

- Ground truth evaluation mismatches: 0
- Schema validation failures: 0
- Stratification requirement errors: 0
- Mismatch kind calculation errors: 0
- Keyword evasion is measured in AI-4 against the independently written docs/b1_keywords.md.
