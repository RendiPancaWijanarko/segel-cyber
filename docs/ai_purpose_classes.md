# AI Purpose Classes and Expectation Map

This document defines the purpose classification schema (Classes L1 through L6) and the canonical expectation map for SEGEL release verification, strictly adhering to Decision D17 in `docs/ai_decisions.md`.

---

## 1. Purpose Classes (L1..L6)

| Class | Title | Canonical Description | Expected Capabilities |
|:---:|---|---|---|
| **L1** | DNS allowlist update | Updates, additions, or replacements of allowed DNS server addresses or domain resolution endpoints. | `dns_allowlist_change` |
| **L2** | Operator account change | Creation, update, or provisioning of standard operator or administrative maintenance user accounts. | `account_added` |
| **L3** | Non-weakening logging adjustment | Configuration changes to logging destinations, audit log targets, or logging parameters that do not disable logging. | `logging_changed` |
| **L4** | Network rule addition | Outbound network firewall rule additions, upstream host declarations, or network egress routing updates. | `outbound_rule_added` |
| **L5** | Hardening by disabling services | Hardening or attack-surface reduction actions by explicitly disabling unneeded services or background daemons. | `service_disabled` |
| **L6** | Vague or other | General, vague, ambiguous, or unclassified purposes that do not fall cleanly into L1 through L5. | *(None — empty set)* |

---

## 2. Canonical Expectation Map (D17)

The deterministic expectation check maps each purpose class to the exact set of allowable capability kinds:

```python
EXPECTATION_MAP = {
    "L1": {"dns_allowlist_change"},
    "L2": {"account_added"},
    "L3": {"logging_changed"},
    "L4": {"outbound_rule_added"},
    "L5": {"service_disabled"},
    "L6": set(),  # Empty set: nothing expected
}
```

---

## 3. High-Risk Capabilities (Never Expected by Any Class)

Per Decision D17, the following capabilities are **never expected by any class** (L1 through L6). Their presence in a release payload diff unconditionally marks the release as inconsistent with its declared purpose:

1. `privilege_granted`: Granting elevated administrative or root permissions to an account.
2. `logging_disabled`: Disabling system logging (`logging.enabled: false`), which weakens audit posture.
3. `trust_anchor_added`: Adding new public keys or root certificates, expanding the trust boundary.
4. `service_enabled`: Enabling new background services or daemons.
5. `scheduled_task_added`: Registering periodic jobs or cron tasks (potential persistence mechanism).
6. `broad_change`: Modifying 8 or more configuration entries for a nominally narrow release purpose.

---

## 4. Consistency Evaluation Logic

A release is evaluated for consistency between its stated purpose and its actual configuration delta:

1. The stated purpose is classified into one of the classes $L \in \{L1, L2, L3, L4, L5, L6\}$.
2. The candidate configuration delta relative to predecessor baseline is extracted into observed capability kinds: $C_{\text{diff}}$.
3. The release is marked:
   - **consistent** if and only if $C_{\text{diff}} \subseteq \text{EXPECTATION\_MAP}[L]$.
   - **inconsistent** if $\exists c \in C_{\text{diff}}$ such that $c \notin \text{EXPECTATION\_MAP}[L]$.

For Class **L6**, because $\text{EXPECTATION\_MAP}[L6] = \emptyset$, any configuration change producing at least one capability ($|C_{\text{diff}}| \ge 1$) results in an `inconsistent` verdict with a deterministic warning: *"purpose too vague to verify"* (Decision D15).
