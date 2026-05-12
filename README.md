# 🤖 Chatbot Teknik Informatika UNRI

Chatbot rule-based dengan fuzzy search untuk menjawab pertanyaan seputar kurikulum, dosen, kalender akademik, pedoman skripsi, SOP, dan alur administrasi di Program Studi Teknik Informatika UNRI.

## 📦 Sumber Data

- `kurikulum.json` — Kurikulum 2018 & 2025
- `kalender_akademik.json` — Kalender TA 2025/2026
- `kalender_akademik_2627_intents.json` — Kalender TA 2026/2027
- `dosen.json` — Data dosen & pimpinan prodi
- `data_skripsi_advanced.json` — Pedoman penulisan skripsi
- `sop_skripsi.json` — SOP Skripsi (Bab 1–3)
- `sop_jte_fixed.json` — SOP Kerja Praktek
- `after_sidang_map_biru_merah_chatbot.json` — Alur after sidang (map biru & merah)
- `after_sidang_sitei_chatbot.json` — Alur after sidang SITEI
- `informasi_umum.json` — Informasi umum (beasiswa, UKT, dll) — _opsional_

## 🚀 Menjalankan Lokal

```bash
# 1. Install dependency
pip install -r requirements.txt

# 2. Jalankan Streamlit
streamlit run app.py
```

App akan terbuka di `http://localhost:8501`.

## ☁️ Deploy ke Streamlit Community Cloud

1. Push folder ini ke repo GitHub (pastikan semua file `.json` ikut ter-push).
2. Buka https://share.streamlit.io dan hubungkan ke repo tersebut.
3. Set:
   - **Main file path**: `app.py`
   - **Python version**: 3.10 atau 3.11
4. Deploy. Streamlit akan otomatis baca `requirements.txt`.

## 🗂️ Struktur Proyek

```
rule-based_chatbot/
├── app.py                                      # Streamlit UI + core chatbot
├── requirements.txt
├── README.md
├── RULE-BASED.ipynb                            # Versi notebook (opsional)
├── kurikulum.json
├── kalender_akademik.json
├── kalender_akademik_2627_intents.json
├── dosen.json
├── data_skripsi_advanced.json
├── sop_skripsi.json
├── sop_jte_fixed.json
├── after_sidang_map_biru_merah_chatbot.json
└── after_sidang_sitei_chatbot.json
```

## 💬 Contoh Pertanyaan

- "Siapa kaprodi TI?"
- "Kapan wisuda 128?"
- "Semester 3 ada matkul apa aja?"
- "Prosedur seminar proposal skripsi"
- "Syarat pengajuan KP"
- "Isi map biru apa saja?"
- "Aturan margin skripsi"
- "Ganti kurikulum 2018"

## 🛠️ Arsitektur Router

Chatbot memeriksa query user berurutan ke beberapa sumber data (fuzzy match + threshold):

1. Perintah sistem (`ganti`, `total sks`, `semester N`)
2. Informasi Umum
3. Dosen
4. Kalender Akademik (gabungan 2 TA)
5. After Sidang
6. Pedoman Penulisan Skripsi
7. SOP Skripsi & SOP JTE
8. Mata kuliah di kurikulum
9. Fallback message

Pencocokan menggunakan `thefuzz.token_set_ratio` dengan threshold 70–80.
