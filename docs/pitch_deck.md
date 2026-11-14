# NASKAH LENGKAP SLIDE PITCH DECK SEGEL
## Kartika Cyber Hackathon 2026 (PUSSIBERAD × CODEPOLITAN)

**Judul Karya**: SEGEL (Sistem Edar Gelar Elektronik Lapis-ganda)  
**Kategori**: Dukungan Teknologi  
**Format Rekomendasi**: 16:9 Landscape (PDF / PPTX)  
**Total Slide**: 10 Slide Ringkas & Terarah

---

### SLIDE 1: JUDUL & IDENTITAS KARYA

- **Judul Utama**: SEGEL: Sistem Edar Gelar Elektronik Lapis-ganda
- **Subjudul**: Platform Distribusi Rilis Konfigurasi Berpaspor Kriptografis Multi-Pihak dengan Pengawasan AI Semantik untuk Satuan Operasional TNI AD
- **Kategori**: Dukungan Teknologi
- **Disusun Oleh**: [Nama Tim Anda]
- **Kompetisi**: Kartika Cyber Hackathon 2026 — PUSSIBERAD TNI AD × CODEPOLITAN

> **Deskripsi Visual Slide**:
> Latar belakang bertema *military cyber* bernuansa hijau gelap (`#0F172A` berpadu hijau tentara `#1E3A1A`). Di sisi kanan terdapat lambang perisai elang PUSSIBERAD dan logo geometris SEGEL bercahaya. Di tengah bawah terdapat 4 badge fitur: `Kriptografi Ed25519 DSSE` · `Local AI Inspector` · `Merkle Tree RFC 6962` · `100% Offline Air-Gap`.

> **Catatan Pembicara (Speaker Notes)**:
> *"Selamat pagi/siang Dewan Juri yang terhormat. Kami mempersembahkan SEGEL, inovasi platform pengamanan rilis konfigurasi dan perangkat lunak militer yang menjawab tantangan serangan rantai pasok pada infrastruktur IT dan Operational Technology (OT) di lingkungan satuan jajaran TNI Angkatan Darat."*

---

### SLIDE 2: PERMASALAHAN: ANCAMAN SUPPLY CHAIN & SATUAN AIR-GAP

- **Judul Slide**: Titik Buta Keamanan: Dari Markas Komando hingga Pos Taktis Lapangan
- **Tiga Masalah Kritis**:
  1. **Serangan Rantai Pasok (Supply Chain Attacks)**: Kasus global seperti SolarWinds membuktikan bahwa konfigurasi legal dapat disusupi kode jahat sebelum sampai ke instalasi akhir.
  2. **Satuan Terisolasi & Air-Gapped**: Satuan tempur dan pos taktis TNI AD berada di wilayah blank-spot atau sengaja di-airgap tanpa koneksi internet langsung. Solusi cloud CI/CD modern tidak dapat digunakan.
  3. **Integritas Konfigurasi Statis**: Pemeriksaan tradisional (SHA-256 biasa) hanya membuktikan file tidak korup, tetapi **tidak dapat membuktikan siapa pembuatnya, apakah telah diuji di lab, dan apakah disetujui oleh otoritas berwenang**.

> **Deskripsi Visual Slide**:
> Diagram alur ancaman: Server Markas -> Jalur Pengiriman (rentan intersepsi/tampering) -> Pos Taktis Lapangan (menerima konfigurasi tanpa sarana verifikasi otoritas). Diberikan ikon bahaya berwarna merah pada titik pergantian personel dan media transfer USB/radio.

> **Catatan Pembicara**:
> *"Bagi TNI AD, sebuah perintah operasi atau file konfigurasi radio taktis tidak boleh hanya sekadar diunduh. Saat personel di perbatasan menerima update perangkat, bagaimana mereka yakin konfigurasi tersebut benar-benar berasal dari Komando Resmi dan bukan hasil sabotase di tengah jalan? Inilah masalah yang diselesaikan SEGEL."*

---

### SLIDE 3: SOLUSI SEGEL: ARSITEKTUR PASPOR KRIPTOGRAFIS 5-STEMPEL

- **Judul Slide**: Filosofi SEGEL: *"Tanpa Bukti, Tidak Ada Penerapan"*
- **Prinsip Dasar**:
  - Konfigurasi tidak pernah dikirim dalam bentuk file mentah, melainkan dibundel dalam **Paspor Rilis Kriptografis**.
  - Mengadopsi standar internasional **DSSE (Dead Simple Signing Envelope)** dan spesifikasi **SLSA (Supply-chain Levels for Software Artifacts)** tingkat lanjut.
- **Rantai 5-Stempel Keamanan**:
  1. 🏭 **Stempel Asal (Origin)**: Identitas pembuat & lingkungan build tertanda tangan Ed25519.
  2. 🔍 **Stempel Periksa (Inspect)**: Evaluasi kepatuhan kebijakan otomatis & ekstraksi kapabilitas.
  3. 🛡️ **Stempel Setuju (Approve)**: Persetujuan kuorum multi-pihak 2-dari-3 dengan pemisahan grup komando.
  4. 📜 **Stempel Catat (Record)**: Pencatatan ke Buku Besar Transparansi Pohon Merkle (RFC 6962).
  5. 🧪 **Stempel Uji (Test)**: Validasi kesehatan pada unit canary sebelum promosi ke seluruh satuan.

> **Deskripsi Visual Slide**:
> Ilustrasi infografis horizontal menyerupai alur stempel paspor dinas militer: 5 stempel tersusun berurutan dengan ikon industri modern, dihubungkan garis hijau bercahaya menuju dokumen berpaspor digital.

> **Catatan Pembicara**:
> *"SEGEL mengubah paradigma deployment menjadi sistem paspor multi-otoritas. Setiap rilis wajib mengantongi 5 stempel kriptografis independen. Jika ada satu stempel hilang, tidak sah, atau diubah 1 bit saja, sistem satuan otomatis menolak penerapan secara fail-closed."*

---

### SLIDE 4: INOVASI TEKNIS: PENGISOLASIAN AI INSPECTOR LOKAL

- **Judul Slide**: AI Sebagai Pengawas Semantik, Bukan Pemegang Kunci
- **Tantangan Semantik**:
  - Penyerang sering menyembunyikan perubahan berbahaya di balik deskripsi yang tampak biasa (*silent inconsistency*), seperti menyusupkan DNS aneh di balik tujuan "sinkronisasi rutin".
- **Inovasi AI SEGEL**:
  - **Model Lokal Bebas Internet**: Menjalankan LLM lokal (`qwen3:4b` via Ollama loopback 127.0.0.1) tanpa pernah mengirim sebutir byte pun data militer ke server cloud komersial.
  - **Prinsip Fail-Closed & Sandboxing**: AI berjalan di subproses terisolasi tanpa akses socket luar dan tanpa akses kunci privat.
  - **AI Bersifat Konsultatif**: AI tidak memiliki wewenang menandatangani atau menolak rilis secara mandiri; keputusannya dibatasi maksimal pada vonis `WARN` yang mewajibkan konfirmasi kriptografis (*acknowledgement digest*) dari perwira penyetuju.

> **Deskripsi Visual Slide**:
> Diagram arsitektur AI: Teks 'Purpose' rilis dianalisis oleh Model Lokal dalam kotak terisolasi (*sandbox*). Tampil perbandingan: Keyword Rule (Lolos/Abstain) vs AI Inspector (Mendeteksi Kelas L6 Vague -> Memunculkan Peringatan Konsultatif).

> **Catatan Pembicara**:
> *"Dalam keamanan militer, AI tidak boleh dipercaya memegang tombol rilis. Pada SEGEL, AI bertindak sebagai analis semantik cerdas untuk mendeteksi maksud samar yang luput dari aturan regex biasa, seperti pada kasus DEV-14. Namun keputusan akhir tetap berada di tangan rantai komando manusia."*

---

### SLIDE 5: VERIFIKASI MANDIRI LURING SATUAN (AIR-GAP READY)

- **Judul Slide**: Kedaulatan Verifikasi: Otonom Penuh di Satuan Garis Depan
- **Kapabilitas Utama**:
  - **Zero Network Reliance**: Perangkat penerima di pos satuan (`segel-receiver`) memverifikasi keabsahan paspor secara instan menggunakan *Akar Kepercayaan Lokal (Trust Root)* tanpa perlu menghubungi server pusat.
  - **Media Transfer Fleksibel**: Paspor rilis dapat disalurkan melalui jaringan taktis daring, media fisik (USB flashdisk terlindungi), maupun **QR Code Berdensitas Tinggi (High-Density 2D Barcode)** untuk perimeter air-gap ekstrem.
  - **Pertahanan Anti-Rollback**: Enkapsulasi nomor urut rilis yang meningkat monotonik mencegah serangan pemutaran ulang rilis konfigurasi usang (*replay attack*).
  - **Penerapan Atomik**: Jika verifikasi lolos, konfigurasi diterapkan secara instan; jika gagal, direktori staging otomatis dibersihkan tanpa meninggalkan jejak kerusakan sistem.

> **Deskripsi Visual Slide**:
> Ilustrasi tablet/laptop lapangan prajurit di pos terdepan sedang memindai QR code paspor dari kertas/layar offline. Layar menampilkan "5/5 STEMPEL SAH — KONFIGURASI DITERAPKAN".

> **Catatan Pembicara**:
> *"Prajurit di perbatasan tidak butuh akses internet ke Markas Besar untuk tahu apakah pembaruan radar atau sistem senjata mereka aman. Aplikasi penerima SEGEL memverifikasi matematika kriptografinya secara luring di perangkat lokal dalam waktu kurang dari 2 detik."*

---

### SLIDE 6: BUKU BESAR TRANSPARANSI & INTEGRITAS HISTORIS (RFC 6962)

- **Judul Slide**: Jejak Audit Anti-Penyangkalan: Pohon Merkle & Saksi Independen
- **Fondasi Kriptografis**:
  - Setiap rilis yang disetujui otomatis dicatat ke dalam **Pohon Merkle Append-Only** berbasis standar internasional RFC 6962 (teknologi yang sama di balik *Certificate Transparency* global).
  - Setiap penambahan entri menghasilkan *checkpoint* yang ditandatangani oleh Otoritas Pencatat (*Ledger Signer*).
- **Perlindungan Terhadap Serangan Internal (Split-View Defense)**:
  - Mengintegrasikan entitas **Saksi Independen (Witness)** yang melakukan verifikasi konsistensi matematis (*consistency proof*) dan membubuhkan tanda tangan silang (*cosignature*).
  - Administrator nakal tidak dapat menghapus riwayat rilis atau memberikan versi rilis yang berbeda kepada satuan yang berbeda tanpa terdeteksi.

> **Deskripsi Visual Slide**:
> Diagram Pohon Merkle kriptografis bercabang dua yang membentuk Root Hash. Di sampingnya terdapat entitas Saksi Eksternal (Witness) yang memvalidasi konsistensi log.

> **Catatan Pembicara**:
> *"Bagaimana jika server markas dikompromikan dari dalam? Dengan Buku Besar Transparansi Merkle, manipulasi atau penghapusan riwayat rilis mustahil dilakukan secara diam-diam. Struktur data append-only menjamin audit forensik yang tidak terbantahkan."*

---

### SLIDE 7: DEMONSTRASI PURWARUPA & KESIAPAN IMPLEMENTASI

- **Judul Slide**: Purwarupa Fungsional Berstandar Industri Militer
- **Antarmuka & Komponen Siap Uji**:
  - **Web Release Desk**: Dashboard berbasis FastAPI & Jinja2 dengan identitas visual PUSSIBERAD TNI AD, menyajikan telemetri riil (bukan data dummy).
  - **Suite CLI Militer**: `segel-receiver` (penerima luring), `segel-approver` (perangkat peninjau komando), dan `segel-witness` (layanan saksi).
- **Pengujian Ketat & Validasi Serangan**:
  - **436 Uji Otomatis Lulus (100% Green)** pada Python 3.14.6: unit test, integration test, dan fuzzing property-based test.
  - **Uji Ketahanan Serangan Siber Nyata**:
    - `AT-001`: Penolakan kunci palsu/rogue key.
    - `AT-002`: Penolakan perubahan muatan payload 1 byte.
    - `AT-008`: Penolakan persetujuan sepihak oleh pembuat (*author self-approval*).
    - `AT-012`: Penolakan replay sequence nomor rilis lama.

> **Deskripsi Visual Slide**:
> Screenshot antarmuka Dashboard SEGEL berdampingan dengan terminal pengujian `pytest` bertuliskan `436 passed in 42.13s` dan ringkasan audit data dinamis.

> **Catatan Pembicara**:
> *"SEGEL bukan sekadar konsep di atas kertas. Purwarupa kami telah selesai dibangun, lengkap dengan dashboard operasional, CLI taktis, dan telah teruji dengan 436 skenario pengujian otomatis, termasuk simulasi serangan injeksi dan pemalsuan kriptografis."*

---

### SLIDE 8: KESESUAIAN DENGAN KEBUTUHAN PUSSIBERAD & DOKTRIN TNI AD

- **Judul Slide**: Selaras dengan Kebutuhan Pengamanan IT / OT TNI AD
- **Kesesuaian Doktrin Pertahanan Siber**:
  1. **Pengamanan Infrastruktur Informasi Vital (IIV) TNI AD**: Mencegah insersi malware pada firmware sistem kendali radar, komunikasi taktis C4ISR, dan server operasional militer.
  2. **Kemandirian & Kedaulatan Kriptografi**: Menggunakan primitif standar terbuka (Ed25519, SHA-256, DSSE) tanpa ketergantungan lisensi proprietary atau algoritma asing yang rentan backdoor.
  3. **Hierarki Komando Terintegrasi**: Mekanisme multi-approver 2-dari-3 merefleksikan otorisasi bertingkat militer (misal: Komandan Satuan Siber dan Pejabat Operasi).
  4. **Efisiensi Logistik**: Berjalan pada komputer komersial maupun laptop lapangan standar tanpa memerlukan perangkat keras HSM berbiaya miliaran rupiah pada fase adopsi awal.

> **Deskripsi Visual Slide**:
> Matriks pemetaan antara Doktrin Pertahanan Siber TNI AD dengan fitur keamanan SEGEL (IIV Protection, Air-Gap Support, Sovereign Crypto, Operational Efficiency).

> **Catatan Pembicara**:
> *"Solusi ini dirancang khusus untuk doktrin TNI AD. Tidak ada sistem pertahanan siber yang dapat bertahan jika rantai pasok perangkat lunaknya rapuh. SEGEL mengunci celah tersebut secara tuntas dan mandiri."*

---

### SLIDE 9: RENCANA PENGEMBANGAN LANJUTAN (ROADMAP IMPLEMENTASI)

- **Judul Slide**: Roadmap Implementasi: Dari Purwarupa ke Gelar Operasi Nyata
- **Fase 1: Uji Laboratorium PUSSIBERAD (Bulan 1–3)**
  - Pengujian terisolasi pada lab siber TNI AD, integrasi dengan perangkat radio taktis dan server komando percontohan.
- **Fase 2: Pilot Deployment Komando Wilayah (Bulan 4–6)**
  - Uji coba lapangan pada 2 Kotama/Korem terpilih untuk distribusi pembaruan konfigurasi perbatasan secara luring menggunakan QR densitas tinggi.
- **Fase 3: Integrasi Perangkat Keras Aman / Hardware Token (Bulan 7–12)**
  - Migrasi kunci penandatangan tingkat komando ke smartcard/HSM berstandar militer dan implementasi agen penerima ringan berbasis micro-controller untuk perangkat IoT/OT lapangan.

> **Deskripsi Visual Slide**:
> Diagram roadmap berbentuk timeline 3 tahap yang elegan dengan milestone terukur dan ikon kesiapan militer.

> **Catatan Pembicara**:
> *"Dengan arsitektur modular yang telah kami bangun, SEGEL siap memasuki tahap uji coba laboratorium PUSSIBERAD segera setelah kompetisi ini selesai, dengan target adopsi bertahap ke satuan kewilayahan."*

---

### SLIDE 10: KESIMPULAN & PENUTUP

- **Judul Slide**: Mengawal Kedaulatan Siber Nusantara Melalui Integritas Rantai Pasok
- **Tiga Pesan Penutup**:
  1. **Tangguh**: 5-stempel kriptografis memastikan tidak ada rilis tanpa bukti sah.
  2. **Cerdas**: Pengawasan AI semantik lokal menjaga kerahasiaan data militer tanpa kompromi.
  3. **Mandiri**: Otonom penuh secara luring untuk mendukung kesiapan operasi satuan TNI AD di seluruh pelosok negeri.
- **Ajakan**:
  - *"Bersama PUSSIBERAD TNI AD, Amankan Gelar Konfigurasi Menuju Kedaulatan Siber Indonesia yang Mandiri dan Berdaya Gentar Tinggi."*
- **Kontak Tim**: [Email Tim] | [Nomor WhatsApp] | Repositori: `github.com/RendiPancaWijanarko/segel-cyber`

> **Deskripsi Visual Slide**:
> Lambang garuda Kartika Yudha Waskita dan logo SEGEL berdampingan di tengah, dengan kalimat penutup yang tegas dan kredensial tim di bagian bawah.

> **Catatan Pembicara**:
> *"Terima kasih kepada Dewan Juri dari PUSSIBERAD dan CODEPOLITAN. Kami siap menjawab pertanyaan dan mendemonstrasikan purwarupa SEGEL secara langsung. Cakra Wahana Paksa!"*
