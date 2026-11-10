# SEGEL Capability Taxonomy

This specification defines the complete capability taxonomy for SEGEL configuration release inspection, aligned with PRD v2.0 §7.5, TAS §8.4, and architectural decisions D2, D3, and D17 in `docs/ai_decisions.md`.

---

## 1. Overview & Instance Identification

Capabilities represent observable configuration declarations and actions extracted from release payloads. Extraction operates via:
1. **Structured Baseline v1 Extractor**: Used when payload files parse as Baseline v1 JSON configurations (`extract_capabilities_structured`).
2. **Deterministic Pattern Matcher (Regex)**: Fallback scanner for non-JSON or legacy configurations (`extract_capabilities`).

### Instance ID Format
Every capability instance is assigned a globally deterministic, unique instance ID within an inspection:
```
<kind>#<n>
```
where:
- `<kind>` is the canonical capability kind name from Section 2.
- `<n>` is a 1-based sequential counter per kind (`1, 2, 3, ...`).

### Ordering Properties
Instance numbering strictly adheres to stable sort order:
1. **File Path**: Files are processed in lexicographical order (`sorted(files.keys())`).
2. **File Position**:
   - In structured Baseline v1 JSON: Document order of top-level sections (`firewall.outbound_allowed`, `dns_allowlist`, `services.enabled`, `services.disabled`, `accounts`, `logging`, `scheduled_tasks`, `trust_anchors`) and item index within each array.
   - In regex fallback: Line number and character start offset (`match.start()`).

---

## 2. Capability Taxonomy Table

| Kind | Description | Parameters | Default Severity | Expected by Class (D17) |
|---|---|---|---|---|
| `network_listen` | Opens a network listener / bind address | `port`, `proto`, `setting`, `value` | `pass` | None |
| `file_write` | Declares filesystem write path or log output | `destination`, `setting`, `value` | `pass` | None |
| `external_connect` | Outbound network connection / upstream endpoint | `destination`, `port`, `setting`, `value` | `warn` | None |
| `credential_reference` | References credentials, passwords, tokens, API keys | `setting`, `value` | `warn` | None |
| `privilege_escalation` | Requests root, sudo, or elevated container privileges | `account`, `setting`, `value` | `reject` | None (Forbidden) |
| `dns_allowlist_change` | Addition or update of an allowed DNS resolver / domain | `destination`, `setting`, `value` | `pass` | L1 (DNS Allowlist Update) |
| `outbound_rule_added` | Addition of allowed outbound firewall rule | `destination`, `port`, `proto`, `setting`, `value` | `pass` | L4 (Network Rule Addition) |
| `account_added` | Declaration of standard or operator account | `account`, `setting`, `value` | `pass` | L2 (Operator Account Change) |
| `privilege_granted` | Elevated privileges (admin/root) granted to an account | `account`, `setting`, `value` | `reject` | None (Never Expected) |
| `logging_changed` | Non-weakening logging destination or parameter adjustment | `destination`, `setting`, `value` | `pass` | L3 (Logging Adjustment) |
| `logging_disabled` | Logging disabled (`logging.enabled = false`) | `setting`, `value` | `warn` | None (Never Expected) |
| `service_enabled` | Background service enabled | `setting`, `value` | `warn` | None (Never Expected) |
| `service_disabled` | Hardening action disabling an unneeded service | `setting`, `value` | `pass` | L5 (Hardening Disabling Services) |
| `scheduled_task_added` | Periodic task, cron job, or automation rule added | `setting`, `value` | `warn` | None (Never Expected) |
| `trust_anchor_added` | CA certificate, public key, or trust anchor added | `setting`, `value` | `warn` | None (Never Expected) |
| `broad_change` | Sweeping delta (8 or more entries differ from predecessor) | `setting`, `value` | `warn` | None (Never Expected) |

---

## 3. Parameter Specifications

Every capability dictionary emits standard parameters:
- `capability_id` (`str`): The canonical kind name matching the table above.
- `instance_id` (`str`): The assigned `<kind>#<n>` identifier.
- `file` (`str`): Relative file path within the release package.
- `line` (`int`): Line number where the element appears (or top of section).
- `destination` (`str | None`): Target host, IP address, CIDR, domain, or filesystem path.
- `port` (`int | str | None`): Network port number or service port name.
- `proto` (`str | None`): Protocol identifier (e.g. `tcp`, `udp`).
- `account` (`str | None`): Username or identity associated with the capability.
- `setting` (`str | None`): Specific configuration attribute or section name.
- `value` (`str | None`): Stringified value or representation of the configuration setting.
- `description` (`str`): Human-readable explanatory description.

---

## 4. Policy and Purpose Class Alignment (D17)

Per Decision D17:
- **Class L1 (DNS allowlist update)**: Expects `dns_allowlist_change`.
- **Class L2 (Operator account change)**: Expects `account_added`.
- **Class L3 (Non-weakening logging adjustment)**: Expects `logging_changed`.
- **Class L4 (Network rule addition)**: Expects `outbound_rule_added`.
- **Class L5 (Hardening by disabling services)**: Expects `service_disabled`.
- **Class L6 (Vague or other)**: Expects no capabilities. Any capability under L6 raises a deterministic WARN ("purpose too vague to verify").

### High-Risk Unclassified Capabilities
The following capabilities are **never expected by any purpose class** and trigger findings when present:
- `privilege_granted` (Default: `reject`)
- `logging_disabled` (Default: `warn`)
- `trust_anchor_added` (Default: `warn`)
- `service_enabled` (Default: `warn`)
- `scheduled_task_added` (Default: `warn`)
- `broad_change` (Default: `warn`)
