# SEGEL — Sistem Edar Gelar Elektronik Lapis-ganda

**Platform Distribusi & Pengamanan Rilis Konfigurasi dengan Rantai Bukti Kriptografis untuk Lingkungan Terisolasi (Air-Gapped) dan Edge TNI AD**

*Purwarupa Kompetisi Resmi untuk **Kartika Cyber Hackathon 2026** — Diselenggarakan oleh Pusat Siber Angkatan Darat (PUSSIBERAD) bekerja sama dengan PT Codepolitan Integrasi Indonesia (CODEPOLITAN) dalam rangka memperingati Hari Juang Kartika 2026.*

---

## 1. Identitas Kompetisi & Kesesuaian Karya

Dokumen ini disusun untuk memenuhi seluruh ketentuan teknis dan kepatuhan administratif sebagaimana diatur dalam **Rulebook** dan **Syarat & Ketentuan (T&C) Kartika Cyber Hackathon 2026**.

| Parameter Kompetisi | Deklarasi & Kesesuaian Karya SEGEL |
|---------------------|-----------------------------------|
| **Penyelenggara Utama** | Pusat Siber Angkatan Darat (**PUSSIBERAD**) |
| **Mitra Pelaksana** | PT Codepolitan Integrasi Indonesia (**CODEPOLITAN**) |
| **Tema Hackathon** | *"Pemanfaatan Kecerdasan Buatan (AI) untuk Mendukung Pengamanan Information Technology (IT) / Operational Technology (OT) TNI AD"* |
| **Kategori Terdaftar** | **Dukungan Teknologi** (*Infrastruktur, platform, atau tooling yang mendukung operasi siber satuan*) |
| **Bentuk Solusi** | Platform perangkat lunak, kerangka kerja otomasi deployment keamanan, dan gerbang pengesahan rilis kriptografis terisolasi (*air-gapped release gateway*). |
| **Sasaran Pengamanan** | Pengamanan rantai pasok konfigurasi & pembaruan perangkat lunak pada infrastruktur IT pangkalan/markas komando serta perangkat Operational Technology (OT) lapangan TNI AD (sistem C4ISR, radar, tautan komunikasi taktis, dan perangkat edge perbatasan). |
| **Peran Kecerdasan Buatan (AI)** | Model AI Penasihat (*AI Advisory Classifier*) lokal berbasis LLM loopback (`qwen3:4b`) untuk menganalisis niat rilis (*purpose classification*), mendeteksi ketidaksesuaian antara deklarasi maksud dan perubahan kapabilitas teknis (firewall, akun, logging), serta memperingatkan komando sebelum persetujuan rilis. |
| **Doktrin Inti** | *"No Evidence, No Deployment"* — Menolak penggelaran pembaruan tanpa rantai bukti kriptografis 5 stempel yang lengkap dan utuh. |

---

## 2. Kategori dan Ruang Lingkup Karya (Kesesuaian T&C Pasal 5)

Sesuai dengan ketentuan **Pasal 5 Syarat dan Ketentuan Kartika Cyber Hackathon 2026**, rincian ruang lingkup dan kepatuhan karya SEGEL diuraikan sebagai berikut:

### 2.1 Relevansi Kategori: Dukungan Teknologi
SEGEL dirancang sebagai platform **Dukungan Teknologi** bagi satuan operasi siber TNI AD:
1. **Otomasi Gerbang Rilis Aman (*Automated Security Deployment Gate*)**: Mengotomatisasi validasi konfigurasi dan artefak rilis melalui 5 gerbang kriptografis bertingkat.
2. **Kemandirian Lingkungan Terputus (*Air-Gapped & Edge Operability*)**: Menjamin bahwa stasiun kerja pangkalan dan unit penerima lapangan (*receiver node*) dapat memverifikasi keabsahan rilis secara otonom tanpa bergantung pada konektivitas internet atau server pihak ketiga.
3. **Pencegahan Sabotase Rantai Pasok (*Supply-Chain Tamper Resistance*)**: Menghentikan ancaman penyusupan konfigurasi jahat, eskalasi hak akses gelap, dan modifikasi tidak sah pada perangkat IT/OT vital satuan.

### 2.2 Deklarasi Keaslian Karya (*Originality & Pre-existing Work Declaration*)
- **Pengerjaan Orisinal**: Seluruh kode sumber utama, arsitektur sistem, skema atestasi, logika penegakan kebijakan, antarmuka Meja Rilis, dan rangkaian pengujian dibangun secara orisinal oleh tim pengembang selama periode kompetisi Kartika Cyber Hackathon 2026.
- **Rujukan Standar Terbuka (*Open Standards*)**: SEGEL mengadopsi spesifikasi publik terbuka tingkat industri, meliputi:
  - **RFC 8032**: Tanda tangan digital Ed25519 dan verifikasi deterministik.
  - **RFC 6962 & RFC 9162**: Struktur pohon Merkle append-only untuk transparansi log dan bukti konsistensi (*consistency proof*).
  - **in-toto Attestation Framework v1.0**: Format predikat atestasi rantai pasok perangkat lunak.
  - **Dead Simple Signing Envelope (DSSE)**: Pembungkusan tanda tangan digital dengan pengkodean PAE (*Pre-Authentication Encoding*).
  - **RFC 8785**: Format kanonikal JSON (JCS) untuk konsistensi hash kriptografis.

### 2.3 Atribusi Pihak Ketiga & Model AI (Sesuai T&C Pasal 5.4 dan Berkas NOTICE)
Pengembangan SEGEL memanfaatkan pustaka sumber terbuka dan model kecerdasan buatan berlisensi legal dengan atribusi lengkap sebagai berikut:
- **Pustaka Kriptografi**: `cryptography` (versi 50.0.2, lisensi Apache-2.0 / BSD-3-Clause) oleh Python Cryptographic Authority (PyCA) untuk operasi tanda tangan RFC 8032 Ed25519 dan fungsi hash SHA-256.
- **Kerangka Kerja Backend**: `FastAPI` (MIT), `Uvicorn` (BSD-3-Clause), `Pydantic` (MIT), dan `Jinja2` (BSD-3-Clause) untuk layanan web Meja Rilis (*Release Desk*).
- **Serialisasi & Media Air-Gapped**: `cbor2` (MIT) dan `qrcode` (BSD-3-Clause) untuk pembentukan muatan data ringkas pada transfer fisik berpemisah udara.
- **Kerangka Pengujian Mutu**: `pytest` (MIT), `Hypothesis` (MPL-2.0), `Bandit` (Apache-2.0), `Mypy` (MIT), dan `Ruff` (MIT/Apache-2.0).
- **Aset Tampilan**: `htmx` (2-Clause BSD) dan `Lucide Icons` (ISC).
- **Mesin Inferensi AI**: `Ollama` (MIT), diakses secara eksklusif melalui antarmuka loopback lokal `http://127.0.0.1:11434`.
- **Model Bahasa AI**: `Qwen3-4B` (`qwen3:4b`, lisensi Apache-2.0 oleh Alibaba Cloud / Qwen Team).
  > **Deklarasi Bobot Model AI**: Bobot model (*weights*) **tidak disimpan atau di-commit** di dalam repositori kode git ini. Model dikelola secara terpisah pada mesin host lokal melalui instalasi Ollama.
- Rincian atribusi lisensi lengkap tercantum pada berkas [NOTICE](NOTICE) dan daftar pembekuan dependensi pada [docs/sbom_freeze.txt](docs/sbom_freeze.txt).

### 2.4 Kepatuhan Hukum, Keamanan, dan Hak Kekayaan Intelektual (T&C Pasal 5.5 & Pasal 14)
- **Bebas Malware & Konten Berbahaya**: SEGEL tidak mengandung kode berbahaya (*malware*), pintu belakang (*backdoor*), atau skrip destruktif.
- **Perlindungan Hak Cipta**: Seluruh kode tidak melanggar HKI pihak ketiga. Sesuai Pasal 14 T&C, hak kekayaan intelektual atas karya ini tetap milik pengembang, dengan lisensi non-eksklusif diberikan kepada PUSSIBERAD dan CODEPOLITAN untuk keperluan evaluasi, penjurian, dan publikasi.
- **Hak Adopsi Pertahanan Siber**: Pengembang menyetujui hak PUSSIBERAD untuk mengadopsi, mengembangkan, dan mengimplementasikan konsep teknis karya ini demi pengamanan Infrastruktur Informasi Vital (IIV) TNI AD melalui diskusi kerja sama resmi.

---

## 3. Arsitektur & Rantai Bukti 5 Stempel Kriptografis

SEGEL menerapkan prinsip bahwa tidak ada konfigurasi atau kode biner yang dapat digelar ke stasiun kerja operasional atau instalasi taktis tanpa mengantongi rantai bukti kriptografis 5 stempel bertingkat:

```
  Asal-Usul (1)      Inspeksi (2)      Persetujuan (3)    Pencatatan (4)      Pengujian (5)
  ┌───────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐
  │ 🏭 PABRIK │─────▶│ 🔍 ANALIS │─────▶│ ✅ KOMANDO│─────▶│ 📜 BUKU   │─────▶│ 🧪 KANARI │
  │ (Builder) │      │(Inspector)│      │(Approvers)│      │ (Ledger)  │      │ (Canary)  │
  └───────────┘      └───────────┘      └───────────┘      └───────────┘      └───────────┘
   Tanda tangan       Ekstraksi &        Persetujuan        Pencatatan         Uji coba
   integritas         Penasihat AI       M-dari-N           transparan         lapangan &
   artefak sumber     advisori           air-gapped         Merkle Tree        verifikasi
```

1. 🏭 **Asal-Usul (*Origin*)**: Atestasi asal-usul yang membuktikan siapa pembuat rilis, sumber kode, dan bagaimana paket dibungkus secara terverifikasi (Builder).
2. 🔍 **Inspeksi (*Inspect*)**: Ekstraksi kapabilitas teknis (firewall, akun, hak istimewa, log) dan audit kebijakan deterministik, diperkuat klasifikasi penasihat AI (*AI Advisory Classification*).
3. ✅ **Persetujuan (*Approve*)**: Mekanisme persetujuan multi-pihak M-dari-N (ambang batas default 2-dari-3, melarang pembuat menyetujui karyanya sendiri), dengan kewajiban kriptografis untuk mengikat pengakuan peringatan (*mandatory warning acknowledgement binding*).
4. 📜 **Pencatatan (*Record*)**: Pencatatan ke dalam log transparansi Merkle pohon terurut (*append-only transparency log*) RFC 6962 dengan tanda tangan checkpoint resmi dan tanda tangan bersama saksi independen (*witness cosignatures*).
5. 🧪 **Pengujian (*Test*)**: Evaluasi uji coba gelar prapenggelaran (*canary deployment health evaluation*) dan verifikasi paspor rilis di sisi penerima terisolasi (*offline receiver*).

---

## 4. Subsistem Penasihat Kecerdasan Buatan (AI Advisory Subsystem)

Subsistem AI bertindak sebagai analis penasihat untuk membantu personel siber mendeteksi anomali antara intensi yang diklaim dalam manifest dengan dampak perubahan teknis konfigurasi.

### Batasan Keamanan & Prinsip AI:
- **Terkungkung Lokal (*Loopback Only*)**: Seluruh komunikasi HTTP inferensi dibatasi ketat ke alamat loopback lokal `http://127.0.0.1:11434`. Tidak ada transmisi data ke internet atau server awan pihak ketiga.
- **Hanya Penasihat (*Strictly Advisory, Capped at Warn*)**: Temuan model AI dibatasi paling tinggi pada tingkat keparahan `warn` (peringatan). Model AI **tidak pernah dapat menolak rilis secara mandiri** dan **tidak pernah dapat menurunkan atau membatalkan** temuan penolakan deterministik (`REJECT`).
- **Tanpa Akses Kunci Kriptografis (*Zero Key Exposure*)**: Proses inferensi AI dijalankan pada subproses steril (*scrubbed environment*) yang telah dibersihkan dari seluruh variabel lingkungan kunci privat, token, dan kredensial. AI tidak pernah melihat, memegang, atau menandatangani atestasi.
- **Integritas Prompt Terverifikasi (*Runtime Prompt Integrity*)**: Templat prompt inferensi diverifikasi terhadap digest SHA-256 yang dibekukan (`docs/ai_prompt_freeze.txt`). Setiap indikasi modifikasi prompt akan memicu penghentian fail-closed seketika (`PROMPT_TAMPERED`).
- **Evaluasi Empiris Jujur**: Berdasarkan evaluasi pra-registrasi sistematis, aturan deterministik sederhana (B1b) mampu mendeteksi inkonsistensi maksud tanpa LLM. Model AI memberikan nilai tambah berupa reduksi alarm palsu (*fewer false alarms*); perbedaan hasil 1-2 item dari 36 sampel korpus dilaporkan secara terbuka sesuai standar kejujuran ilmiah.

---

## 5. Panduan Cepat 10 Menit (Instalasi & Pengoperasian Lokal)

### Prasyarat Sistem
- **Sistem Operasi**: Windows 10/11 atau Linux (teruji penuh pada lingkungan Windows).
- **Runtime Python**: Python 3.14.6 terverifikasi (sintaks kompatibel dengan Python 3.12+).
- **Git**
- **Ollama** (opsional, hanya diperlukan jika mengaktifkan fitur inferensi langsung AI penasihat): terpasang pada `http://127.0.0.1:11434` dengan model `qwen3:4b`.

### Langkah 1: Klon Repositori & Penyiapan Virtual Environment
```powershell
git clone <repo-url> segel-cyber
cd segel-cyber

python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Langkah 2: Instalasi Dependensi Pengembang
```powershell
pip install -e ".[dev]"
```

### Langkah 3: Eksekusi Seluruh Rangkaian Pengujian (Zero Network Dependency)
Seluruh 436 pengujian unit, integrasi, berbasis properti (*hypothesis*), dan adversarial dapat dieksekusi secara instan tanpa membutuhkan layanan eksternal atau koneksi internet (menggunakan `FakeLLM` bawaan):
```powershell
pytest
```

### Langkah 4: Eksekusi Skenario Demonstrasi Otomatis (4 Babak)
Menjalankan pengujian 4 babak skenario demonstrasi rilis pada mode deterministik (`SEGEL_AI_ENABLED=0`) dan mode berpenasihat AI (`SEGEL_AI_ENABLED=1`):
```powershell
python scripts/run_demo_scenario.py
```

### Langkah 5: Peluncuran Antarmuka Meja Rilis (Release Desk Web UI)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1
```
Buka peramban web pada alamat: `http://127.0.0.1:8000`.

---

## 6. Tabel Status Kesiapan Implementasi Fitur

Laporan status implementasi fitur per batas komitmen arsitektural:

| Komponen / Fitur | Status | Deskripsi & Cakupan Uji Terverifikasi |
|------------------|:------:|---------------------------------------|
| **Tanda Tangan RFC 8032 Ed25519** | **Terimplementasi** | Lolos vektor uji RFC 8032 pada `tests/unit/crypto/test_ed25519.py`. Identitas kunci berbasis `SHA-256(raw_pubkey)`. |
| **Amplop DSSE & Kanonikal JSON** | **Terimplementasi** | Pengkodean PAE dan pengurutan kunci kanonikal diverifikasi pada `tests/unit/crypto/test_dsse.py`. |
| **Skema Predikat in-toto v1.0** | **Terimplementasi** | Predikat Origin, Inspect, Approve, Record, Test divalidasi via Pydantic pada `tests/unit/test_schemas.py`. |
| **Ekstraksi Kapabilitas Deterministik** | **Terimplementasi** | Parser aturan batas regex dan ekstraktor terstruktur diuji pada `tests/unit/test_inspector.py`. |
| **Mesin Kebijakan Keamanan (PRULE-001..004)** | **Terimplementasi** | Penolakan keras `REJECT` atas eskalasi hak istimewa root diuji pada `tests/adversarial/test_at004_prohibited_capabilities.py`. |
| **Persetujuan Multi-Pihak Air-Gapped** | **Terimplementasi** | Ambang batas 2-dari-3 dan pencegahan *self-approval* pembuat diuji pada `tests/adversarial/test_at005_self_approval.py`. |
| **Pengikatan Pengakuan Peringatan (WARN Ack)** | **Terimplementasi** | `acknowledgement_digest` terikat pada stempel komando; ditegakkan oleh Ledger dan Receiver (`tests/unit/test_ai_7_ack_and_manifest.py`). |
| **Log Transparansi Merkle RFC 6962** | **Terimplementasi** | Log append-only dengan checkpoint bertandatangan diuji pada `tests/unit/crypto/test_merkle.py` dan `test_ledger.py`. |
| **Tanda Tangan Bersama Saksi (Witness)** | **Terimplementasi** | Validasi bukti konsistensi RFC 9162 diuji pada `tests/unit/test_witness.py`. |
| **Paspor Rilis (Candidate & General)** | **Terimplementasi** | Pembungkusan berkas bukti dan promosi paspor diuji pada `tests/unit/test_passport_and_promotion.py`. |
| **Penerima Terisolasi & Adaptor Gelar** | **Terimplementasi** | Siklus hidup gelar 10-langkah, jurnal pemulihan rollback, dan pembatasan isolasi diuji pada `tests/unit/test_receiver.py`. |
| **Pencegahan Rollback (Monotonic Sequence)** | **Terimplementasi** | Pemeriksaan urutan nomor monotonic diuji pada `tests/adversarial/test_at002_rollback.py`. |
| **Subsistem Penasihat AI** | **Terimplementasi** | Batasan keparahan `warn`, pembekuan prompt, timeout fail-closed diuji pada `tests/unit/test_ai_inspector.py`. |
| **Antarmuka Web Meja Rilis (Release Desk)** | **Terimplementasi** | Dasbor FastAPI dinamis, rincian rilis, panel telemetri kriptografis, dan dukungan Bahasa Indonesia penuh. |
| **Diff Manifest Rilis Historis** | **Sebagian (Partial)** | Inspeksi muatan rilis mandiri berjalan penuh; perbandingan diff otomatis terhadap rilis pendahulu belum diintegrasikan (DEV-07). |
| **Rantai Transisi Trust Root Rollover** | **Sebagian (Partial)** | Validasi kenaikan versi `root_version` berjalan; rantai tanda tangan multi-root masa transisi ditangguhkan ke versi lanjutan (DEV-10). |
| **Pembangun Independen Ganda (Dual Builders)** | **Belum Diterapkan** | Menggunakan pembangun tunggal pada MVP; verifikasi biner identik bit-demi-bit dialokasikan untuk fase berikutnya (FR-011). |
| **Streaming QR Fountain Code Multi-Frame** | **Belum Diterapkan** | Muatan QR ringkas JSON/CBOR berjalan; streaming animasi fountain code multi-frame dialokasikan untuk fase berikutnya (AT-036). |
| **Distribusi Pencabutan Kunci Jaringan Darurat** | **Belum Diterapkan** | Penerima terisolasi memerlukan paket pembaruan kepercayaan fisik (TUP); distribusi via jaringan ditangguhkan (AT-011). |

---

## 7. Peta Panduan & Dokumentasi Lengkap

- 📄 **[Panduan Instalasi & Penggunaan Lokal (Format PDF)](docs/PANDUAN_INSTALASI_DAN_PENGGUNAAN_SEGEL.pdf)** — Dokumen panduan eksekutif resmi berbahasa Indonesia lengkap, siap cetak dan mudah dibaca oleh personel satuan TNI AD.
- 📘 **[Dokumentasi Instalasi](docs/install.md)** — Panduan instalasi mendalam, dependensi lingkungan, penyiapan model Ollama, dan pemecahan kendala teknis.
- 📗 **[Panduan Operasional & Penggunaan](docs/usage.md)** — Alur kerja komando, instruksi baris perintah (CLI), dan eksplorasi antarmuka web.
- 🏛️ **[Arsitektur Sistem & Deviasi](docs/architecture.md)** — Spesifikasi arsitektur komprehensif, zona pemisah kepercayaan, dan daftar deviasi tercatat (DEV-01 s.d. DEV-10).
- ⚠️ **[Batasan & Konstrain Sistem](docs/limitations.md)** — Batasan keamanan operasional, asumsi kriptografis, dan fitur masa depan.
- 🧠 **[Log Keputusan Rekayasa AI](docs/ai_decisions.md)** — Catatan keputusan desain arsitektural subsistem kecerdasan buatan (D1 s.d. D22).
- 📊 **[Laporan Evaluasi Model AI](docs/evaluation/ai_report.md)** — Laporan ilmiah perbandingan performa model AI terhadap baseline deterministik (B0, B1, B1b, B2).
- 📜 **[Atribusi Lisensi & Hak Cipta](NOTICE)** — Daftar atribusi lisensi pustaka pihak ketiga dan model kecerdasan buatan.
- 🤝 **[Deklarasi Keterlibatan AI](docs/ai_assistance_disclosure.md)** — Pengungkapan penggunaan asisten AI dalam penulisan kode di bawah kendali dan peninjauan manusia.

---

## 8. Pernyataan Penyangkalan (*Disclaimer*)

*Karya ini merupakan purwarupa kompetisi untuk Kartika Cyber Hackathon 2026 dan bukan merupakan produk komersial atau sistem dinas resmi.*
SEGEL tidak memberikan jaminan mutlak (*zero defect*) atas ketiadaan kerentanan pada perangkat lunak target. SEGEL menyediakan bukti kriptografis yang dapat diverifikasi secara independen mengenai asal-usul, inspeksi kebijakan, pengesahan multi-pihak, catatan publik append-only, dan uji kanari. Seluruh kunci kriptografis yang disertakan dalam repositori ini merupakan kunci sintetis untuk demonstrasi dan tidak boleh digunakan pada lingkungan produksi operasional.
