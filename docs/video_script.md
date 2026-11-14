# SKRIP REKAMAN VIDEO DEMO PURWARUPA SEGEL
## Kartika Cyber Hackathon 2026 (Maksimal Durasi: 10 Menit)

**Target Output**: Video demo berdurasi 7–9 menit diunggah ke YouTube (format Landscape 1080p, Public / Unlisted).  
**Kebutuhan Rekaman**: Software perekam layar (OBS Studio / Bandicam) + Mikrofon jelas + Browser (`http://127.0.0.1:8000`) + Terminal PowerShell.

---

### TABEL RUNDOWN & TIMECODE REKAMAN

| Segmen | Menit | Fokus Konten | Tampilan Layar (Visual) |
|:---|:---:|:---|:---|
| **Segmen 1** | 00:00 – 01:30 | Pembuka & Latar Belakang Masalah Pertahanan Siber | Slide Judul & Slide Masalah (Air-Gap & Supply Chain) |
| **Segmen 2** | 01:30 – 03:00 | Konsep Solusi: Arsitektur 5-Stempel & AI Lokal | Slide Arsitektur 5-Stempel & Diagram AI Sandbox |
| **Segmen 3** | 03:00 – 06:30 | **Demo Live 1: Alur Rilis Sah (Golden Path)** | Layar Browser Dashboard SEGEL (`/`, `/release/new`) |
| **Segmen 4** | 06:30 – 08:00 | **Demo Live 2: Panel AI Advisory (Item DEV-14)** | Layar Browser Release Detail dengan AI Advisory Panel |
| **Segmen 5** | 08:00 – 09:00 | **Demo Live 3: Verifikasi Luring & Uji Ketahanan** | Layar Terminal PowerShell: CLI Receiver & Pytest |
| **Segmen 6** | 09:00 – 10:00 | Nilai Strategis bagi TNI AD & Kalimat Penutup | Slide Kesimpulan & Komitmen Kedaulatan Siber |

---

### NASKAH AUDIO KATA-PER-KATA & PETUNJUK TINDAKAN LAYAR

#### SEGMEN 1: PEMBUKA & LATAR BELAKANG (00:00 – 01:30)
* **Aksi Layar**: Buka slide presentasi Slide 1 (Judul), kemudian beralih ke Slide 2 (Masalah).
* **Narasi Pembicara**:
  > *"Halo Dewan Juri Kartika Cyber Hackathon 2026 yang terhormat dari PUSSIBERAD TNI AD dan CODEPOLITAN. Perkenalkan, kami dari [Nama Tim Anda] mempersembahkan karya kami dalam kategori Dukungan Teknologi: **SEGEL — Sistem Edar Gelar Elektronik Lapis-ganda**.*
  >
  > *Sebagai tulang punggung pertahanan negara, TNI Angkatan Darat mengoperasikan ribuan aset Information Technology (IT) dan Operational Technology (OT) — mulai dari radar perbatasan, perangkat radio taktis C4ISR, hingga sistem kendali persenjataan. Sebagian besar satuan taktis ini berada di wilayah terluar dan beroperasi dalam postur terisolasi atau **air-gapped** tanpa koneksi internet langsung.*
  >
  > *Tantangan kritis yang dihadapi adalah: **bagaimana mendistribusikan pembaruan konfigurasi dan patch perangkat lunak secara aman tanpa risiko serangan rantai pasok (supply-chain attack)?** Pemeriksaan hash konvensional hanya membuktikan file tidak korup, tetapi tidak mampu membuktikan siapa yang menandatanganinya, apakah kebijakan keamanannya terpenuhi, dan apakah pimpinan komando telah menyetujuinya. SEGEL hadir untuk menjawab tantangan tersebut dengan filosofi: **Tanpa Bukti Kriptografis Sah, Tidak Ada Penerapan.**"*

---

#### SEGMEN 2: ARSITEKTUR PASPOR 5-STEMPEL & AI LOKAL (01:30 – 03:00)
* **Aksi Layar**: Beralih ke Slide 3 (Rantai 5-Stempel) dan Slide 4 (Inovasi AI Inspector).
* **Narasi Pembicara**:
  > *"SEGEL mengemas setiap rilis ke dalam **Paspor Kriptografis** yang wajib mengantongi **5 Stempel Keamanan Independen** berbasis standar terbuka Ed25519 DSSE:*
  > *1. **Stempel Asal (Origin)** dari pembuat rilis.*
  > *2. **Stempel Periksa (Inspect)** dari mesin evaluasi kebijakan.*
  > *3. **Stempel Setuju (Approve)** berbasis kuorum 2-dari-3 dari perwira komando berwenang.*
  > *4. **Stempel Catat (Record)** yang tercatat abadi di Buku Besar Transparansi Pohon Merkle RFC 6962.*
  > *5. **Stempel Uji (Test)** berupa validasi kesehatan otomatis pada unit canary sebelum disebarkan.*
  >
  > *Tidak hanya itu, kami melengkapinya dengan **AI Inspector lokal** yang memanfaatkan model open-weight `qwen3:4b` di atas Ollama loopback. AI ini diisolasi secara ketat: tidak memiliki akses ke internet, tidak memegang kunci privat, dan keputusannya bersifat konsultatif. Tugasnya adalah mendeteksi maksud samar (vague intent) atau ketidaksesuaian semantik tersembunyi yang sering digunakan penyerang untuk mengelabui aturan firewall atau kebijakan statis."*

---

#### SEGMEN 3: DEMO LIVE 1 — ALUR RILIS SAH (03:00 – 06:30)
* **Aksi Layar**: Pindah ke browser menampilkan `http://127.0.0.1:8000/`. Arahkan kursor ke metrik dashboard.
* **Narasi Pembicara**:
  > *"Mari kita lihat langsung purwarupa operasional SEGEL Release Desk yang telah kami bangun.*
  >
  > *(Tunjukkan Dashboard)*: Ini adalah dashboard operasional SEGEL. Seluruh angka di sini adalah telemetri dinamis riil yang bersumber langsung dari Buku Besar Merkle dan Akar Kepercayaan, tanpa data mock atau dummy.*
  >
  > *(Klik Rilis Baru)*: Sekarang kita simulasikan pembuatan rilis pembaruan konfigurasi untuk pos satuan taktis Unit 42. Kita masukkan Release ID `BASELINE-UNIT-42`, sequence 1, tujuannya adalah pembaruan parameter jaringan, dengan target canary `canary-1,canary-2` dan cakupan umum `canary-1,canary-2,unit-3`.*
  >
  > *(Klik tombol Jalankan Alur Rilis)*: Dalam hitungan milidetik, pipa 5-stempel langsung memproses rilis:
  > - Stempel Origin dan Inspect langsung sah dan berstatus PASS.
  > - Stempel Approve mendapatkan konsensus kuorum 2-dari-2 dari kunci penandatangan terpisah.
  > - Stempel Record mencatat rilis sebagai entri daun baru pada Pohon Merkle.*
  >
  > *(Klik Gelar ke Unit Canary)*: Selanjutnya rilis diuji pada unit canary. Node canary secara mandiri memverifikasi tanda tangan dan menjalankan probe kesehatan perangkat. Ketika kedua unit sehat, stempel Test berubah menjadi VALID.*
  >
  > *(Klik Promosikan ke Seluruh Satuan)*: Kontroler Promosi menerbitkan Paspor Rilis Umum, saksi eksternal (Witness) membubuhkan cosignature, dan paspor kini siap didistribusikan ke satuan taktis secara luring.*
  >
  > *(Kembali ke Dashboard)*: Amati dashboard utama — angka Stempel Sah bertambah menjadi 9, Satuan Tergelar meningkat menjadi 3 Unit, dan Buku Besar Transparansi mencatat 2 entri Merkle sah."*

---

#### SEGMEN 4: DEMO LIVE 2 — PANEL AI ADVISORY & PENOLAKAN DETERMINISTIK (06:30 – 08:00)
* **Aksi Layar**: Klik **Rilis Baru**, isi form dengan kasus `DEV-14`:
  - Release ID: `DEV-14-SYNC`
  - Purpose: `Synchronize communication parameters for branch office gateway node`
  - Klik **Jalankan Alur Rilis**.
* **Narasi Pembicara**:
  > *"Sekarang mari kita uji kemampuan inovasi **AI Inspector**. Di sini kami menggunakan item uji coba `DEV-14` dari dataset evaluasi. Di balik tujuannya yang tampak sangat umum yaitu 'sinkronisasi parameter komunikasi', pembuat rilis sebenarnya menyusupkan perubahan DNS allowlist dan aturan firewall keluar.*
  >
  > *Aturan kata kunci deterministik biasa akan abstain karena kalimatnya terlalu umum. Namun perhatikan layar: model AI lokal kami mendeteksi bahwa tujuan ini tergolong **Kelas L6 (Vague / Unclassified)**. Vonis inspeksi dinaikkan menjadi **WARN**.*
  >
  > *Sistem memunculkan panel khusus bertajuk **AI Advisory**. Di sini dijelaskan alasan inferensi model, dan sistem mengaktifkan proteksi wajib: perwira penyetuju diwajibkan menyertakan *acknowledgement digest* tertanda tangan sebelum rilis ini diizinkan untuk dipromosikan.*
  >
  > *Sebaliknya, jika ada rilis yang secara terang-terangan melanggar kebijakan — misalnya menyusupkan hak akses root (`privilege: root`) — mesin deterministik SEGEL langsung menjatuhkan vonis **REJECT**. Gerbang buku besar menolak pencatatan secara fail-closed, membuktikan bahwa AI tidak pernah bisa menurunkan vonis REJECT menjadi PASS."*

---

#### SEGMEN 5: DEMO LIVE 3 — VERIFIKASI LURING SATUAN & UJI KETAHANAN (08:00 – 09:00)
* **Aksi Layar**: Pindah ke terminal PowerShell. Tunjukkan eksekusi pengujian otomatis `pytest`.
* **Narasi Pembicara**:
  > *"Bagaimana di sisi satuan penerima lapangan? Satuan menggunakan modul CLI `segel-receiver`. Penerima memverifikasi paspor rilis secara mandiri tanpa memerlukan koneksi ke Markas Besar.
  >
  > *(Tunjukkan hasil pytest di terminal)*:
  > Purwarupa SEGEL telah melalui pengujian perangkat lunak yang sangat ketat:
  > - **436 pengujian otomatis berstatus lulus 100% (Green)** mencakup pengujian kriptografi Ed25519, envelope DSSE, konsistensi pohon Merkle, dan uji sifat matematis (property-based testing).*
  > - Termasuk skenario serangan adversarial:
  >   - `AT-001`: Percobaan menggunakan kunci palsu langsung ditolak.
  >   - `AT-002`: Pengubahan 1 byte saja pada payload konfigurasi langsung digagalkan oleh verifikasi tanda tangan digital.
  >   - `AT-012`: Percobaan memutar ulang sequence lama (replay attack) otomatis diblokir oleh verifikasi anti-rollback."*

---

#### SEGMEN 6: KESIMPULAN & PENUTUP (09:00 – 10:00)
* **Aksi Layar**: Kembali ke Slide 9 (Roadmap) dan Slide 10 (Penutup).
* **Narasi Pembicara**:
  > *"Sebagai penutup, platform SEGEL memberikan tiga nilai strategis utama bagi Pusat Siber Angkatan Darat:
  > 1. **Kedaulatan Penuh**: Dibangun di atas standar terbuka tanpa lisensi asing berbayar dan tanpa ketergantungan cloud publik.
  > 2. **Kesiapan Air-Gap**: Dirancang sejak awal untuk medan operasi nyata TNI AD yang terisolasi dari internet.
  > 3. **Pertahanan Berlapis**: Menggabungkan ketegasan matematika kriptografi multi-pihak dengan kecerdasan analisa semantik AI lokal.
  >
  > Platform ini siap untuk diuji coba di laboratorium PUSSIBERAD dan diintegrasikan pada ekosistem pengamanan Information Technology dan Operational Technology satuan jajaran TNI Angkatan Darat.
  >
  > Sekian presentasi dan demonstrasi dari tim kami. Terima kasih atas perhatian Dewan Juri. Bersama PUSSIBERAD TNI AD, amankan ruang siber pertahanan bangsa! Cakra Wahana Paksa!"*
