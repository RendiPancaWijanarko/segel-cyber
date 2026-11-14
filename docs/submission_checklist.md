# PANDUAN SUBMISSION & CHECKLIST KELENGKAPAN
## Kartika Cyber Hackathon 2026 (PUSSIBERAD × CODEPOLITAN)

**Karya**: SEGEL (Sistem Edar Gelar Elektronik Lapis-ganda)  
**Kategori**: Dukungan Teknologi  
**Batas Akhir Submission**: **15 November 2026 pukul 23:59 WIB**  
**Portal Pengumpulan**: `https://codepolitan.com/dashboard/kartika-cyber-hackathon-2026`

---

## 1. Ringkasan Kebutuhan Formulir Submission

| Komponen Wajib | Spesifikasi Rulebook | Status / Lokasi Aset |
|:---|:---|:---|
| **1. Link Karya / Repository** | Link publik repositori yang dapat diakses Dewan Juri | `https://github.com/RendiPancaWijanarko/segel-cyber` |
| **2. Thumbnail Karya** | Ukuran 1200×630 px, format JPG/PNG/WebP, maks. 500 KB | Konsep di `docs/submission_checklist.md` (dapat diekspor dari Canva/Figma) |
| **3. Screenshot Karya** | Maksimal 5 gambar tampilan antarmuka sistem | 5 Titik Screenshot Terpilih di Bab 3 |
| **4. Video Karya** | Maksimal 10 menit, unggah ke YouTube (Public/Unlisted) | Skrip narasi dan panduan rekaman di `docs/video_script.md` |
| **5. Slide Penjelasan (Deck)**| Slide presentasi (latar belakang, solusi, AI, arsitektur, kelayakan) | Teks per slide dan panduan visual di `docs/pitch_deck.md` |
| **6. Dokumentasi Teknis** | Arsitektur, instalasi, dan panduan penggunaan | `README.md`, `docs/architecture.md`, `docs/DEMO_GUIDE.md` |

---

## 2. Metadata Pengisian Formulir Platform

- **Nama Tim**: *(Sesuai nama tim yang didaftarkan ketua tim)*
- **Nama Karya**: `SEGEL — Sistem Edar Gelar Elektronik Lapis-ganda`
- **Kategori**: `Dukungan Teknologi`
- **Deskripsi Singkat (Ringkasan Eksekutif)**:
  > Platform distribusi dan verifikasi rilis konfigurasi berpaspor kriptografis multi-pihak (5-stempel) untuk pengamanan operasional satuan TNI AD. Memastikan pembaruan perangkat taktis dan perimeter air-gapped terlindungi dari ancaman rantai pasok (supply-chain attack) tanpa bergantung pada internet atau koneksi ke server pusat, diperkuat pengawasan semantik AI lokal (Ollama loopback) untuk mendeteksi maksud samar/tersembunyi.
- **Link Repositori**: `https://github.com/RendiPancaWijanarko/segel-cyber`

---

## 3. Spesifikasi 5 Screenshot Karya Terbaik

Dewan Juri membatasi maksimal **5 gambar**. Pilihlah 5 tangkapan layar berikut untuk memaksimalkan skor fungsionalitas dan inovasi:

1. **Screenshot 1: Dashboard Utama Release Desk (Beranda)**
   - *Halaman*: `http://127.0.0.1:8000/`
   - *Fokus*: Menampilkan Command Header PUSSIBERAD TNI AD, rasio konsensus kuorum, metrik stempel kripto, 3 kanal distribusi gelar satuan, dan tabel rilis konfigurasi satuan.
   - *Caption*: `Dashboard Operasional SEGEL: Telemetri distribusi rilis dan verifikasi kriptografis 5-stempel terintegrasi.`

2. **Screenshot 2: Rincian Rilis & Rantai 5-Stempel Keamanan**
   - *Halaman*: `http://127.0.0.1:8000/release/0`
   - *Fokus*: Diagram pipeline 5-stempel valid (Origin, Inspect, Approve, Record, Test) dengan rincian amplop DSSE Ed25519 dan identitas penandatangan.
   - *Caption*: `Rantai Paspor 5-Stempel: Pembuktian multi-pihak independen sebelum rilis disahkan ke satuan.`

3. **Screenshot 3: Panel Pengawasan AI Konsultatif (Maksud Samar DEV-14)**
   - *Halaman*: `http://127.0.0.1:8000/release/1` (setelah rilis `DEV-14` dibuat)
   - *Fokus*: Panel kuning AI Advisory dengan klasifikasi `L6 (Vague/Unclassified)`, alasan inferensi model lokal `qwen3:4b`, dan kewajiban `acknowledgement_digest` bagi approver.
   - *Caption*: `Panel Konsultatif AI: Deteksi maksud samar pada teks purpose rilis secara lokal tanpa paparan data ke internet.`

4. **Screenshot 4: Penjelajah Buku Besar Transparansi (RFC 6962 Merkle Tree)**
   - *Halaman*: `http://127.0.0.1:8000/ledger`
   - *Fokus*: Pohon Merkle append-only, checkpoint tertanda tangan, pembuktian inklusi, dan cosignature saksi eksternal.
   - *Caption*: `Buku Besar Transparansi Merkle Log: Audit jejak rilis anti-tamper yang dapat diverifikasi secara luring.`

5. **Screenshot 5: Akar Kepercayaan & Kuorum Otoritas (Trust Root)**
   - *Halaman*: `http://127.0.0.1:8000/trust`
   - *Fokus*: Daftar 7 kunci otoritas militer, pembagian grup penandatanganan (group-0 dan group-1), serta ambang batas kuorum 2-dari-3.
   - *Caption*: `Akar Kepercayaan Otoritas: Manajemen kunci kriptografi kedaulatan dengan pemisahan peran dan batas kuorum.`

---

## 4. Panduan Desain Thumbnail (1200×630 px)

- **Dimensi**: 1200 x 630 piksel (Rasio 1.91:1, standar OpenGraph).
- **Format**: PNG atau JPG (maksimum 500 KB).
- **Tata Letak Visual**:
  - **Latar Belakang**: Dark cyber green / deep army navy (`#0F172A` atau gradien `#1A2F1E` ke `#0F172A`) dengan aksen grid topografi digital militer atau radar cyber halus.
  - **Sisi Kiri**:
    - Logo PUSSIBERAD TNI AD dan Badge SEGEL.
    - Judul Besar: **SEGEL** (Warna Emas Militer `#D1BD99` atau Hijau Siber `#3B7A32`).
    - Subjudul: **Sistem Edar Gelar Elektronik Lapis-ganda**.
    - Tagline: *Distribusi Rilis Konfigurasi Berpaspor Kriptografis 5-Stempel untuk Satuan TNI AD*.
  - **Sisi Kanan**:
    - Mockup perspektif 3D layar laptop/tablet yang menampilkan Dashboard Release Desk SEGEL dengan pipa 5-stempel menyala hijau.
    - Badges/Pills: `Zero-Trust Air-Gap` · `Ed25519 DSSE` · `Local AI Guard` · `RFC 6962 Merkle`.
