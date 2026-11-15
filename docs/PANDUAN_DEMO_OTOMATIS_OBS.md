# PANDUAN PEREKAMAN DEMO OTOMATIS TERSINKRONISASI OBS
## Platform SEGEL — Kartika Cyber Hackathon 2026 (PUSSIBERAD TNI AD)

Panduan ini dirancang khusus agar Anda dapat merekam video demonstrasi purwarupa **SEGEL (Sistem Edar Gelar Elektronik Lapis-ganda)** secara profesional, mulus, dan **sekali jadi (*one-take recording*)** tanpa perlu mengoperasikan kursor atau mengetik di laptop secara manual.

---

### I. Gambaran Umum Autopilot Demo Player

Sistem telah dilengkapi dengan modul **Autopilot Demo Engine** terintegrasi (`/autopilot`). Saat diluncurkan, sistem akan mengendalikan seluruh jalannya demonstrasi di layar secara otomatis:
1. **Kursor Virtual Cerdas (*Animated Mouse Cursor*)**: Kursor taktis bergerak mulus (*smooth Bezier glide*) melintasi layar, menyorot tombol, dan mengarahkan pandangan penonton ke titik krusial.
2. **Efek Klik Nyata (*Click Ripple Pulse*)**: Setiap klik tombol memancarkan animasi gelombang cincin emas-hijau (*ripple wave*) disertai sorotan aktif (*active focus pulse*) pada elemen target.
3. **Animasi Mengetik Alami (*Human-like Typewriter Animation*)**: Isian formulir (`BASELINE-UNIT-42`, deskripsi rilis, target canary, skenario `DEV-14-SYNC`, dan perintah `pytest`) terisi huruf demi huruf secara dinamis dengan ritme alami manusia.
4. **Pergantian Layar Terpadu**: Transisi otomatis antara **Slide Presentasi Eksekutif**, **Antarmuka Meja Rilis (Release Desk) Dinamis**, dan **Terminal Militer PowerShell**.
5. **Panduan Naskah Teleprompter (HUD)**: Menampilkan kalimat narasi kata-per-kata yang harus Anda baca tepat pada detik berjalan sesuai dokumen `docs/video_script.md`, lengkap dengan hitung mundur 5 detik untuk bersiap di depan kamera.

---

### II. Tabel Sinkronisasi Waktu & Aksi Layar (Durasi 10 Menit)

| Segmen | Menit | Fokus Pembicara & Aksi Otomatis Layar | Tampilan Layar |
|:---|:---:|:---|:---|
| **Segmen 1** | 00:00 – 01:30 | **Pembuka & Masalah Siber**: Salam pembuka, identitas tim, latar belakang ribuan aset IT/OT TNI AD di wilayah terluar/air-gap, serta bahaya serangan rantai pasok (*supply chain attack*). | Slide 1 (Judul Resmi) &rarr; Slide 2 (Masalah & Doktrin *"No Evidence, No Deployment"*). |
| **Segmen 2** | 01:30 – 03:00 | **Konsep Solusi 5-Stempel & AI**: Penjelasan rantai 5 stempel paspor (Origin, Inspect, Approve, Record, Test) dan inovasi AI Inspector terisolasi (Qwen3-4B loopback). | Slide 3 (Rantai 5 Stempel) &rarr; Slide 4 (Inovasi AI Penasihat Loopback). |
| **Segmen 3** | 03:00 – 06:30 | **Demo Live 1 (Alur Rilis Sah / Golden Path)**: Kursor menyorot metrik dashboard, mengklik "Rilis Baru", mengetik data `BASELINE-UNIT-42`, mengeksekusi pipa 5-stempel, menguji unit canary, menerbitkan Paspor Umum, dan kembali ke dashboard. | Antarmuka Meja Rilis (Release Desk) interaktif penuh dengan animasi kursor, klik, dan ketik. |
| **Segmen 4** | 06:30 – 08:00 | **Demo Live 2 (Panel AI Advisory & Penolakan Deterministik)**: Rilis kasus `DEV-14-SYNC`, AI mendeteksi maksud samar (Kelas L6) dan mengeluarkan status `WARN` & mandat pengakuan. Kontras dengan penolakan keras `privilege: root` &rarr; `REJECT`. | Meja Rilis: Form input, Panel AI Advisory berwarna amber, dan simulasi penolakan deterministik. |
| **Segmen 5** | 08:00 – 09:00 | **Demo Live 3 (Verifikasi Luring Satuan & Uji Ketahanan)**: Penjelasan modul CLI penerima offline, pengetikan otomatis perintah `pytest`, streaming 436 uji lolos (100% Green), dan bukti penolakan serangan adversarial (AT-001, AT-002, AT-012). | Jendela Terminal PowerShell bertema militer gelap dengan streaming log uji real-time. |
| **Segmen 6** | 09:00 – 10:00 | **Kesimpulan & Nilai Strategis bagi TNI AD**: Tiga nilai strategis (Kedaulatan Penuh, Kesiapan Air-Gap, Pertahanan Berlapis), komitmen adopsi laboratorium PUSSIBERAD, dan salam penutup komando *"Cakra Wahana Paksa"*. | Slide 5 (3 Nilai Strategis) & Slide 6 (Salam Komando Cakra Wahana Paksa). |

---

### III. Langkah Memulai Demonstrasi Otomatis (1 Perintah)

1. Buka terminal PowerShell pada direktori proyek `segel-cyber`:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/run_automated_demo.ps1
   ```
2. Skrip akan:
   - Memeriksa ketersediaan backend Release Desk pada port 8000.
   - Meluncurkan Microsoft Edge dalam **App Mode** tanpa bilah tab atau URL bar (`--app=http://127.0.0.1:8000/autopilot --start-maximized`).
   - Membuka halaman demonstrasi otomatis beresolusi tinggi yang siap direkam.

---

### IV. Panduan Penyiapan OBS Studio (Tata Letak Talking Head)

Untuk menghasilkan video berkualitas tinggi (1080p) yang siap dinilai oleh Dewan Juri:

#### 1. Pengaturan Kanvas & Video
- Buka **OBS Studio** &rarr; Masuk ke **Settings** &rarr; **Video**:
  - Base (Canvas) Resolution: `1920x1080`
  - Output (Scaled) Resolution: `1920x1080`
  - Common FPS Values: `60` (atau `30`)

#### 2. Susunan Lapisan (*Sources*) pada Scene Rekaman:
Susun sumber media pada panel **Sources** OBS dari atas ke bawah:
1. **Lapisan 1 (Teratas): Webcam Talking Head Anda**
   - Tambahkan: `Video Capture Device` (Pilih kamera/webcam Anda).
   - Ukuran: Posisikan di **pojok kanan bawah** atau **pojok kanan atas** layar (lebar sekitar 380–420 piksel).
   - Tips: Berikan sedikit filter *Crop/Pad* atau border tipis jika diinginkan agar tampilan talking head terlihat rapi.
2. **Lapisan 2: Tangkapan Layar Demonstrasi Otomatis**
   - Tambahkan: `Window Capture` (Pilih jendela Microsoft Edge yang menjalankan demonstrasi `SEGEL — Demonstrasi Otomatis`).
   - Capture Method: `Windows 10 (1903 and up)` agar perekaman peramban sangat halus tanpa glitch.
3. **Lapisan 3: Audio Mikrofon**
   - Pastikan mikrofon Anda aktif pada panel **Audio Mixer** dan tidak mengalami *clipping* (warna bar hijau-kuning di level -12dB s.d. -6dB).

---

### V. Prosedur Perekaman Video (*Execution Flow*)

1. **Buka OBS Studio** dan pastikan preview rekaman menampilkan layar demonstrasi dan wajah Anda di pojok layar.
2. **Tekan tombol "Start Recording" di OBS Studio**.
3. **Pindah ke jendela Demonstrasi SEGEL** dan tekan tombol **`Spasi`** (atau klik tombol **Mulai Demo (Spasi)**).
4. **Hitung Mundur 5 Detik** akan muncul di layar (*5... 4... 3... 2... 1... MULAI!*).
   - Gunakan 5 detik ini untuk membetulkan posisi duduk, menatap kamera, dan menarik napas santai.
5. **Saat hitung mundur selesai**, mulailah membacakan kalimat pertama pada kotak panduan naskah di bagian atas layar:
   > *"Halo Dewan Juri Kartika Cyber Hackathon 2026 yang terhormat dari PUSSIBERAD TNI AD dan CODEPOLITAN..."*
6. **Seluruh animasi kursor, ketikan teks formulir, klik tombol, pengujian terminal, dan perpindahan slide akan berjalan secara otomatis**, sinkron dengan narasi yang sedang Anda baca!
7. **Jika rekaman selesai (Menit 10:00)**:
   - Tekan tombol **"Stop Recording" di OBS Studio**.
   - Video demonstrasi Anda selesai dan tersimpan dengan presisi tinggi!

---

### VI. Tombol Pintas (*Hotkeys*) untuk Kendali Penuh

Selama demonstrasi berjalan, Anda memegang kendali penuh melalui tombol keyboard:
- **`Spasi`** : Menjeda (*Pause*) atau Melanjutkan (*Resume*) demonstrasi (sangat berguna jika Anda ingin minum atau batuk tanpa harus mereset demo dari awal).
- **`T`** : Menyembunyikan atau Menampilkan panel panduan naskah (HUD Prompter).
- **`R`** : Mengulang demonstrasi dari detik 00:00.
- **`&rarr;` (Panah Kanan)** : Melompati ke segmen berikutnya secara instan.
- **`&larr;` (Panah Kiri)** : Kembali ke segmen sebelumnya.
- **Tombol Kecepatan (`1.0x` / `1.5x` / `2.0x`)** : Mempercepat jalannya demonstrasi untuk keperluan latihan pembacaan naskah.

---

### VII. Tips Rekaman Sekali Jadi (*One-Take Success*)

1. **Jaga Kontak Mata dengan Kamera**:
   Kotak panduan naskah diletakkan di bagian atas tengah layar, tepat di bawah lensa webcam laptop Anda, sehingga mata Anda akan tampak selalu menatap langsung ke arah Dewan Juri.
2. **Gunakan Nada Bicara Tegas & Percaya Diri**:
   Sebagai perwakilan yang membawakan solusi militer pertahanan siber TNI AD, gunakan intonasi yang lugas, terstruktur, dan berwibawa.
3. **Latihan Cepat dengan Mode 1.5x**:
   Sebelum menekan tombol rekam resmi, coba jalankan demonstrasi satu kali pada kecepatan `1.5x` untuk membiasakan diri dengan alur perpindahan visual.
