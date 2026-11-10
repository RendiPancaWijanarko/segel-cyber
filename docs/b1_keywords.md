# B1 Baseline Keyword Taxonomy (Deterministic Expectation Check)

This document defines the generic keyword taxonomy for the deterministic B1 keyword classifier used in SEGEL release inspection. Per Decisions D6 and D17 in `docs/ai_decisions.md`, B1 classifies declared release purposes into canonical classes L1 through L5 based on keyword matching, or abstains when no match or an ambiguous multi-class match is found.

> [!WARNING]
> **Methodological Limitation**: The corpus author and the keyword author are the same assistant. To preserve conservative evaluation rigor, these lists were written generically from the class definitions in `docs/ai_purpose_classes.md` and the 6 exemplars (`EX-01` through `EX-06`) only. No tuning was performed against development or test corpus items.

---

## 1. Classification and Matching Logic

The B1 classifier evaluates purpose text against word-bounded patterns (`\b...\b`) in a case-insensitive manner:
1. **Single-Class Match**: If purpose text matches keywords belonging strictly to one class $L \in \{L1, L2, L3, L4, L5\}$, B1 assigns class $L$.
2. **Ambiguous Match**: If keywords from more than one class match the text, B1 **abstains** (`None`), deferring to downstream inspection logic.
3. **No Match**: If no keywords match from any class, B1 **abstains** (`None`).
4. **Class L6**: B1 never returns `L6` (vague or unclassified purpose is evaluated via model inference or fallback).

---

## 2. Keyword Lists per Purpose Class

### Class L1: DNS Allowlist Update
*Expected capability*: `dns_allowlist_change`
*Domain*: Domain name resolution, DNS resolvers, name servers, forwarders, allowlist configuration.

#### English
- `dns`, `nameserver`, `nameservers`, `name server`, `name servers`
- `resolver`, `resolvers`, `forwarder`, `forwarders`
- `domain resolution`, `name resolution`, `dns allowlist`, `dns whitelist`
- `dns lookup`, `domain lookup`, `recursive dns`, `caching dns`
- `coredns`, `bind`, `unbound`, `dns record`, `dns records`

#### Indonesian
- `dns`, `server dns`, `server nama`, `resolusi nama`, `resolusi domain`
- `penerjemah nama`, `pengurai nama`, `resolver dns`, `forwarder dns`
- `pengarah dns`, `allowlist dns`, `whitelist dns`, `daftar izin dns`
- `kueri domain`, `pencarian domain`, `alamat dns`, `domain resolusi`

---

### Class L2: Operator Account Change
*Expected capability*: `account_added`
*Domain*: Standard operator, technician, or maintenance user provisioning, account management, identity directory.

#### English
- `account`, `accounts`, `user`, `users`, `username`, `usernames`
- `operator`, `operators`, `technician`, `technicians`, `personnel`
- `profile`, `profiles`, `roster`, `identity`, `identities`, `credentials`
- `provisioning`, `provision`, `onboarding`, `onboard`, `user account`
- `operator account`, `maintenance account`, `service account`, `login profile`

#### Indonesian
- `akun`, `akun-akun`, `pengguna`, `user`, `operator`, `teknisi`
- `personel`, `profil`, `identitas`, `kredensial`, `petugas`, `staf`
- `pembuatan akun`, `penambahan akun`, `registrasi akun`, `pendaftaran user`
- `akun operator`, `akun pengguna`, `identitas personel`, `daftar pengguna`

---

### Class L3: Non-Weakening Logging Adjustment
*Expected capability*: `logging_changed`
*Domain*: Syslog redirection, audit log streaming, event journal forwarding, SIEM collector configuration.

#### English
- `log`, `logs`, `logging`, `syslog`, `syslogs`, `audit`, `audit log`, `audit logs`
- `audit trail`, `audit stream`, `journal`, `event log`, `event logs`
- `telemetry`, `siem`, `collector`, `log collector`, `log forwarder`
- `logging destination`, `log target`, `event forwarding`, `event transmission`
- `audit repository`, `event aggregation`

#### Indonesian
- `log`, `logging`, `log audit`, `catatan audit`, `jejak audit`, `rekam jejak`
- `rekaman audit`, `berkas log`, `pengiriman log`, `tujuan log`, `server log`
- `repositori log`, `syslog`, `pencatatan log`, `peristiwa sistem`, `jurnal sistem`
- `agregasi log`, `kolektor log`, `siem`, `penanganan data log`

---

### Class L4: Network Rule Addition
*Expected capability*: `outbound_rule_added`
*Domain*: Firewall egress rules, outbound network rules, routing permits, port allowances.

#### English
- `firewall`, `firewalls`, `outbound`, `egress`, `network rule`, `firewall rule`
- `firewall rules`, `port`, `ports`, `traffic`, `permit traffic`, `egress traffic`
- `route`, `routing`, `uplink`, `connection`, `egress rule`, `outbound rule`
- `network allowlist`, `egress allowlist`, `packet filter`, `upstream connection`

#### Indonesian
- `firewall`, `dinding api`, `outbound`, `egress`, `aturan firewall`, `filter paket`
- `aturan jaringan`, `jalur koneksi`, `pembukaan port`, `port`, `lalu lintas`
- `transmisi data`, `uplink`, `koneksi keluar`, `rute keluar`, `izin keluar`
- `allowlist jaringan`, `firewall keluar`, `aturan keluar`

---

### Class L5: Hardening by Disabling Services
*Expected capability*: `service_disabled`
*Domain*: System hardening, disabling unused background daemons, attack surface reduction.

#### English
- `harden`, `hardening`, `disable`, `disabling`, `disabled`, `service`, `services`
- `daemon`, `daemons`, `attack surface`, `decommission`, `decommissioning`
- `legacy service`, `unused service`, `shutdown service`, `turn off service`
- `exposure reduction`, `system posture`

#### Indonesian
- `hardening`, `pengerasan`, `mematikan`, `menonaktifkan`, `nonaktifkan`
- `penonaktifan`, `disable`, `matikan`, `layanan`, `service`, `daemon`
- `protokol legacy`, `protokol tidak aman`, `bidang serang`, `pengurangan bidang serang`
- `dekomisi`, `penghentian layanan`, `keamanan baseline`
