# xr3ed Cloudstream Extension

<div align="center">

### Repositori Ekstensi CloudStream Gabungan
#### Sumber Utama: BetbetMiro (Miro) | Sumber Backup: Phisher

<img src="https://img.shields.io/github/stars/xr3ed/xr3ed-Repo?style=for-the-badge&color=yellow" />
<img src="https://img.shields.io/github/forks/xr3ed/xr3ed-Repo?style=for-the-badge&color=blue" />
<img src="https://img.shields.io/github/license/xr3ed/xr3ed-Repo?style=for-the-badge&color=green" />
<img src="https://img.shields.io/github/last-commit/xr3ed/xr3ed-Repo?style=for-the-badge&color=red" />

<p>
  <strong>Repository Shortcode:</strong>
  <code>xr3ed</code>
</p>

</div>

---

## Tentang Repository

Repositori ini menggabungkan ekstensi Cloudstream dari dua sumber berbeda:
1. **BetbetMiro-Extension** (sebagai sumber **Utama**)
2. **cloudstream-extensions-phisher** (sebagai sumber **Backup**)

### Kebijakan Penggabungan:
- Jika ada nama ekstensi yang sama di kedua repositori sumber, maka ekstensi dari **Phisher** akan berganti nama dengan akhiran **`[Backup]`** agar tidak bentrok dengan versi utama dari Miro.
- Repositori ini otomatis diperbarui setiap 30 menit melalui GitHub Actions apabila ada perubahan pada salah satu repositori sumber.

---

## Cara Instalasi

### 1. One-click Install (Instalasi Sekali Klik)

**⭐ Jalur jsDelivr CDN (Direkomendasikan — bebas rate limit)**
```text
cloudstreamrepo://raw.githubusercontent.com/xr3ed/xr3ed-Repo/builds/repo-jsdelivr.json
```

**Jalur GitHub Raw (Alternatif jika CDN bermasalah)**
```text
cloudstreamrepo://raw.githubusercontent.com/xr3ed/xr3ed-Repo/builds/repo.json
```

### 2. Instalasi Manual
1. Buka aplikasi **Cloudstream**.
2. Masuk ke **Pengaturan (Settings)** -> **Ekstensi (Extensions)**.
3. Pilih **Tambah Repositori (Add Repository)**.
4. Masukkan salah satu URL repositori berikut:

   **⭐ Jalur jsDelivr CDN (Direkomendasikan)**
   ```text
   https://raw.githubusercontent.com/xr3ed/xr3ed-Repo/builds/repo-jsdelivr.json
   ```

   **Jalur GitHub Raw (Alternatif)**
   ```text
   https://raw.githubusercontent.com/xr3ed/xr3ed-Repo/builds/repo.json
   ```

5. Beri nama repositori (misal: `xr3ed`) lalu simpan.
6. Sekarang Anda bisa menginstal berbagai provider/ekstensi dari repositori ini!

> **Catatan:** Jalur jsDelivr CDN direkomendasikan karena tidak terkena rate limit seperti GitHub Raw, dan lebih cepat karena menggunakan CDN global.

---

## Build Secara Lokal

Jika Anda ingin mengompilasi ekstensi secara manual:

1. Clone repositori ini:
   ```bash
   git clone https://github.com/xr3ed/xr3ed-Repo.git
   cd xr3ed-Repo
   ```
2. Jalankan skrip sinkronisasi untuk mengambil kode terbaru dari repositori Miro dan Phisher:
   ```bash
   python sync_extensions.py
   ```
3. Kompilasi semua plugin:
   ```bash
   ./gradlew make makePluginsJson
   ```
