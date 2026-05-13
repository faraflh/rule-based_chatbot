"""
Streamlit UI untuk Chatbot Rule-Based Teknik Informatika UNRI.
Jalankan dengan: streamlit run app.py
"""

import json
import os
import re
from pathlib import Path

import streamlit as st
from thefuzz import fuzz, process

# ==========================================
# KONFIGURASI
# ==========================================
BASE_PATH = Path(__file__).parent  # folder tempat app.py berada

st.set_page_config(
    page_title="Chatbot TI UNRI",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ==========================================
# CORE CHATBOT
# ==========================================
class MasterRuleBasedChatbot:
    def __init__(self, default_year: str = "2025"):
        # 1. Load semua data JSON
        self.skripsi_data = self.load_json(BASE_PATH / "data_skripsi_advanced.json", [])
        self.kurikulum_data = self.load_json(BASE_PATH / "kurikulum.json", {})

        # Kalender Akademik gabungan 2 tahun ajaran
        kalender_2526 = self.load_json(BASE_PATH / "kalender_akademik.json", [])
        kalender_2627 = self.load_json(BASE_PATH / "kalender_akademik_2627_intents.json", [])
        for it in kalender_2526:
            it.setdefault("tahun_ajaran", "2025/2026")
        for it in kalender_2627:
            it.setdefault("tahun_ajaran", "2026/2027")
        self.kalender_data = kalender_2526 + kalender_2627

        self.dosen_data = self.load_json(BASE_PATH / "dosen.json", [])

        # Informasi Umum (format: {"intents": [...]})
        informasi_umum_raw = self.load_json(BASE_PATH / "informasi_umum_chatbot.json", {})
        self.informasi_umum_data = self._extract_intents(informasi_umum_raw)

        # Setelah Sidang (format: {"intents": [...]})
        setelah_sidang_map_raw = self.load_json(BASE_PATH / "after_sidang_map_biru_merah_chatbot.json", {})
        setelah_sidang_sitei_raw = self.load_json(BASE_PATH / "after_sidang_sitei_chatbot.json", {})
        self.setelah_sidang_data = (
            self._extract_intents(setelah_sidang_map_raw)
            + self._extract_intents(setelah_sidang_sitei_raw)
        )

        # SOP Jurusan & SOP Skripsi
        self.sop_jte_data = self.load_json(BASE_PATH / "sop_jte_fixed.json", [])
        self.sop_skripsi_data = self.load_json(BASE_PATH / "sop_skripsi.json", [])

        # 2. Aturan Rule-Based untuk Skripsi (target Fuzzy Search)
        self.skripsi_rules = {
            "Kertas": ["kertas", "ukuran kertas", "hvs", "a4", "jenis kertas"],
            "Cetakan naskah": ["cetakan", "bolak-balik", "satu sisi", "single side", "muka"],
            "Jenis huruf": ["font", "jenis huruf", "times new roman", "tnr", "ukuran huruf"],
            "Jarak baris": ["spasi", "jarak baris", "jarak paragraf", "line spacing", "jarak judul"],
            "Batas tepi": ["margin", "batas tepi", "batas margin", "jarak tepi", "tepi atas", "tepi bawah", "tepi kiri", "tepi kanan", "kiri kanan"],
            "Sampul CD": ["sampul cd", "cover cd", "label cd"],
            "File CD": ["file cd", "nama file cd", "folder cd", "susunan file cd", "softcopy", "pdf"],
            "Halaman Sampul": ["sampul", "cover", "warna sampul", "karton", "halaman depan", "buffalo"],
            "Daftar Pustaka": ["daftar pustaka", "referensi", "apa style", "dafpus", "pustaka"],
            "Tabel": ["tabel", "format tabel", "judul tabel", "kolom tabel", "sumber tabel"],
            "Gambar": ["gambar", "ilustrasi", "grafik", "format gambar", "judul gambar"],
            "Abstrak": ["abstrak", "ringkasan", "kata kunci", "keyword"],
            "Penulisan": ["penulisan skripsi", "aturan penulisan", "format penulisan", "pedoman penulisan", "cara menulis skripsi"]
        }

        # 3. Variabel & Konfigurasi Kurikulum
        self.kurikulum_year = default_year
        self.sem_map_2018 = {
            "Keahlian I": "Semester 5",
            "Keahlian II": "Semester 6",
            "Keahlian III": "Semester 6",
            "Keahlian IV": "Semester 7",
            "Keahlian V": "Semester 7",
        }

        self.course_names = []
        self.course_details = {}
        self.group_names = []
        self.spec_map = {}

        if not self.load_curriculum(self.kurikulum_year):
            if self.kurikulum_data:
                first_key = list(self.kurikulum_data.keys())[0]
                self.load_curriculum(first_key)

    # ------------------------------------------
    # LOADERS
    # ------------------------------------------
    def load_json(self, filepath, default_value):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return default_value
        except json.JSONDecodeError as e:
            st.warning(f"⚠️ File {filepath.name} rusak formatnya: {e}")
            return default_value

    def _extract_intents(self, raw):
        if isinstance(raw, dict):
            return raw.get("intents", [])
        if isinstance(raw, list):
            return raw
        return []

    # ------------------------------------------
    # KURIKULUM
    # ------------------------------------------
    def load_curriculum(self, year):
        if year not in self.kurikulum_data:
            return False

        self.kurikulum_year = year
        data_active = self.kurikulum_data[year]

        self.course_names = []
        self.course_details = {}
        self.group_names = []
        self.spec_map = {}

        for group in data_active:
            g_name = group.get("group_name", "Unknown")
            self.group_names.append(g_name)
            is_semester = "SEMESTER" in g_name.upper()

            for course in group.get("courses", []):
                c_name = course.get("name", "")
                c_no = course.get("no", "")

                real_semester = g_name if is_semester else self.sem_map_2018.get(str(c_no), "Semester Tidak Diketahui")

                if c_name:
                    self.course_names.append(c_name)
                    self.course_details[c_name] = {
                        "sks": course.get("sks", "0"),
                        "group": g_name,
                        "semester_info": real_semester,
                        "code": course.get("code", "-"),
                        "no_label": c_no,
                    }

                if self.kurikulum_year == "2018" and not is_semester and "Keahlian" in str(c_no):
                    if c_no not in self.spec_map:
                        self.spec_map[c_no] = []
                    self.spec_map[c_no].append({
                        "course_name": c_name,
                        "concentration": g_name,
                        "semester": self.sem_map_2018.get(c_no, ""),
                    })
        return True

    def get_semester_info(self, semester_num):
        target = f"SEMESTER {semester_num}"
        for group in self.kurikulum_data.get(self.kurikulum_year, []):
            if group["group_name"].upper() == target:
                total_sks = group.get("total_sks", "0")
                response = f"📚 **{target} (Kurikulum {self.kurikulum_year})**\n\nTotal Beban: {total_sks} SKS\n\n"
                for c in group["courses"]:
                    if self.kurikulum_year == "2018" and c["name"] in self.spec_map:
                        response += f"🔻 **{c['name']} ({c['sks']} SKS) → Pilih Konsentrasi:**\n"
                        for opt in self.spec_map[c["name"]]:
                            response += f"   - {opt['course_name']} ({opt['concentration']})\n"
                    else:
                        response += f"- [{c.get('code', '-')}] {c['name']} ({c['sks']} SKS)\n"
                return response
        return f"Maaf, data semester {semester_num} tidak ditemukan di Kurikulum {self.kurikulum_year}."

    # ------------------------------------------
    # FUZZY SEARCH HELPERS
    # ------------------------------------------
    def fuzzy_search_intent(self, user_query, data_list, threshold=80):
        best_item = None
        highest_score = 0
        for item in data_list:
            keywords = item.get("keywords", []) or item.get("keyword", [])
            if not keywords:
                continue
            match = process.extractOne(user_query, keywords, scorer=fuzz.token_set_ratio)
            if match and match[1] > highest_score:
                highest_score = match[1]
                best_item = item
        return best_item if highest_score >= threshold else None

    def fuzzy_search_skripsi_category(self, user_query, threshold=80):
        best_category = None
        highest_score = 0
        for category, keywords in self.skripsi_rules.items():
            match = process.extractOne(user_query, keywords, scorer=fuzz.token_set_ratio)
            if match and match[1] > highest_score:
                highest_score = match[1]
                best_category = category
        return best_category if highest_score >= threshold else None

    def fuzzy_search_sop(self, user_query, data_list, threshold=70, limit=2):
        scored = []
        for item in data_list:
            targets = [
                str(item.get("topik_utama", "")),
                str(item.get("sub_topik", "")),
                str(item.get("full_context", "")),
            ]
            konten = str(item.get("konten", ""))
            if konten:
                targets.append(konten[:400])
            targets = [t for t in targets if t]
            if not targets:
                continue
            match = process.extractOne(user_query, targets, scorer=fuzz.token_set_ratio)
            if match and match[1] >= threshold:
                scored.append((match[1], item))
        if not scored:
            return []
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def fuzzy_search_curriculum(self, user_query):
        if not self.course_names:
            return None

        best_group, group_score = process.extractOne(user_query, self.group_names, scorer=fuzz.token_set_ratio)
        if group_score > 75 and "SEMESTER" not in best_group:
            for group in self.kurikulum_data.get(self.kurikulum_year, []):
                if group["group_name"] == best_group:
                    resp = f"📂 **Peminatan: {best_group} ({self.kurikulum_year})**\n\n"
                    for c in group["courses"]:
                        resp += f"- {c['name']} ({c['sks']} SKS)\n"
                    return resp

        matches = process.extract(user_query, self.course_names, limit=3, scorer=fuzz.token_set_ratio)
        valid_matches = [m for m in matches if m[1] > 65]
        if not valid_matches:
            return None

        response = f"🔍 **Hasil Pencarian Mata Kuliah ({self.kurikulum_year}):**\n"
        for name, _ in valid_matches:
            details = self.course_details[name]
            response += f"\n📖 **{name}**\n   • Kode : {details['code']}\n   • SKS  : {details['sks']}\n"
            if "Keahlian" in str(details["no_label"]) and self.kurikulum_year == "2018":
                response += f"   • Kategori : {details['no_label']} ({details['semester_info']})\n   • Grup     : {details['group']}\n"
            else:
                response += f"   • Semester : {details['group']}\n"
        return response

    # ------------------------------------------
    # PREPROCESSING SINGKATAN
    # ------------------------------------------
    def expand_abbreviations(self, text):
        """Ekspansi singkatan umum ke bentuk lengkap untuk matching lebih baik"""
        abbreviations = {
            r'\bsempro\b': 'seminar proposal',
            r'\bsemhas\b': 'seminar hasil sidang skripsi ujian skripsi',
            r'\bkp\b': 'kerja praktik kerja praktek',
            r'\bta\b': 'tugas akhir skripsi',
            r'\buts\b': 'ujian tengah semester',
            r'\buas\b': 'ujian akhir semester',
            r'\bkrs\b': 'kartu rencana studi',
            r'\bukt\b': 'uang kuliah tunggal',
            r'\bspp\b': 'sumbangan pembinaan pendidikan',
            r'\bmbkm\b': 'merdeka belajar kampus merdeka',
            r'\bpmb\b': 'penerimaan mahasiswa baru',
            r'\bsnbp\b': 'seleksi nasional berdasarkan prestasi',
            r'\bsnbt\b': 'seleksi nasional berdasarkan tes',
            r'\butbk\b': 'ujian tulis berbasis komputer',
            r'\bkkn\b': 'kuliah kerja nyata kukerta',
            r'\bsti\b': 'surat tugas ilmiah',
            r'\bkpti\b': 'kartu peserta tugas ilmiah',
        }
        
        expanded = text.lower()
        for pattern, replacement in abbreviations.items():
            expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
        
        return expanded

    # ------------------------------------------
    # ROUTER UTAMA
    # ------------------------------------------
    def get_response(self, user_input):
        cleaned_input = user_input.lower().strip()
        # Ekspansi singkatan untuk matching yang lebih baik
        expanded_input = self.expand_abbreviations(cleaned_input)

        # 1. Perintah Sistem
        if "ganti" in expanded_input:
            if "2018" in expanded_input:
                return "✅ Berhasil beralih ke Kurikulum 2018." if self.load_curriculum("2018") else "❌ Data Kurikulum 2018 tidak ada."
            elif "2025" in expanded_input:
                return "✅ Berhasil beralih ke Kurikulum 2025." if self.load_curriculum("2025") else "❌ Data Kurikulum 2025 tidak ada."

        if "total" in expanded_input and "sks" in expanded_input:
            return f"🤖 Total SKS yang harus ditempuh berdasarkan Kurikulum {self.kurikulum_year} adalah 144 SKS."

        sem_match = re.search(r"(?:sem|semester)\s*(\d+)", expanded_input)
        if sem_match:
            return self.get_semester_info(sem_match.group(1))

        # 2. Informasi Umum
        # Deteksi khusus untuk "visi misi" atau "visi dan misi"
        if any(keyword in expanded_input for keyword in ["visi misi", "visi dan misi", "visi & misi"]):
            visi_item = None
            misi_item = None
            for item in self.informasi_umum_data:
                if item.get("intent") == "info_visi_prodi":
                    visi_item = item
                elif item.get("intent") == "info_misi_prodi":
                    misi_item = item
            
            if visi_item and misi_item:
                return f"ℹ️ **Visi & Misi Program Studi:**\n\n{visi_item['response']}\n\n---\n\n{misi_item['response']}"
            elif visi_item:
                return f"ℹ️ **Informasi:**\n\n{visi_item['response']}"
            elif misi_item:
                return f"ℹ️ **Informasi:**\n\n{misi_item['response']}"
        
        best_info = self.fuzzy_search_intent(expanded_input, self.informasi_umum_data, threshold=80)
        if best_info:
            return f"ℹ️ **Informasi:**\n\n{best_info['response']}"

        # 3. Dosen
        best_dosen = self.fuzzy_search_intent(expanded_input, self.dosen_data, threshold=80)
        if best_dosen:
            return f"👨‍🏫 **Informasi Dosen:**\n\n{best_dosen['response']}"

        # 4. Kalender Akademik
        # Prioritaskan intent jadwal_wisuda_semua untuk query umum tentang wisuda
        if any(keyword in expanded_input for keyword in ["kapan wisuda", "jadwal wisuda", "wisuda kapan", "semua jadwal wisuda", "jadwal wisuda 2026", "jadwal wisuda 2027", "wisuda tahun ini"]) and not re.search(r"wisuda\s*(ke-?)?\s*\d+", expanded_input):
            for item in self.kalender_data:
                if item.get("intent") == "jadwal_wisuda_semua":
                    return f"📅 **Jadwal Wisuda:**\n\n{item['response']}"
        
        best_kalender = self.fuzzy_search_intent(expanded_input, self.kalender_data, threshold=80)
        if best_kalender:
            ta = best_kalender.get("tahun_ajaran", "")
            header = f"📅 **Informasi Akademik (TA {ta}):**" if ta else "📅 **Informasi Akademik:**"
            return f"{header}\n\n{best_kalender['response']}"

        # 5. Setelah Sidang
        best_setelah = self.fuzzy_search_intent(expanded_input, self.setelah_sidang_data, threshold=80)
        if best_setelah:
            return f"📂 **Setelah Sidang:**\n\n{best_setelah['response']}"

        # 6. Pedoman Penulisan Skripsi (dicek lebih dulu karena lebih spesifik untuk aturan penulisan)
        # Deteksi query umum tentang pedoman/aturan penulisan skripsi
        if any(keyword in expanded_input for keyword in ["aturan penulisan", "pedoman penulisan", "format penulisan", "cara menulis skripsi", "panduan penulisan"]):
            overview_chunks = []
            for chunk in self.skripsi_data:
                if chunk.get("sub_topik") == "Umum" and chunk.get("topik_utama") in ["Kertas", "Pengetikan", "Penomoran", "Bahasa"]:
                    konten = chunk.get('konten', '')
                    if isinstance(konten, list):
                        konten = '\n'.join(konten)
                    overview_chunks.append(f"📌 **{chunk.get('full_context', 'Info')}**\n\n{konten}")
            if overview_chunks:
                return "📖 **Pedoman Penulisan Skripsi:**\n\n" + "\n\n---\n\n".join(overview_chunks[:4]) + "\n\n💡 *Tanyakan lebih spesifik untuk detail (contoh: 'aturan margin', 'format tabel', 'daftar pustaka')*"
        
        matched_skripsi_cat = self.fuzzy_search_skripsi_category(expanded_input, threshold=75)
        if matched_skripsi_cat:
            responses = []
            for chunk in self.skripsi_data:
                if matched_skripsi_cat.lower() in chunk.get("sub_topik", "").lower() or matched_skripsi_cat.lower() in chunk.get("topik_utama", "").lower():
                    konten = chunk.get('konten', '')
                    if isinstance(konten, list):
                        konten = '\n'.join(konten)
                    responses.append(f"📌 **{chunk.get('full_context', 'Info')}**\n\n{konten}")
            if responses:
                return "\n\n---\n\n".join(responses)

        # 7. SOP Skripsi & SOP JTE (dicek setelah Pedoman Skripsi)
        sop_results = []
        sop_skripsi_hits = self.fuzzy_search_sop(expanded_input, self.sop_skripsi_data, threshold=70, limit=2)
        sop_jte_hits = self.fuzzy_search_sop(expanded_input, self.sop_jte_data, threshold=70, limit=2)
        for chunk in sop_skripsi_hits:
            konten = chunk.get('konten', '')
            if isinstance(konten, list):
                konten = '\n'.join(konten)
            sop_results.append(f"📘 **SOP Skripsi — {chunk.get('full_context', 'Info')}**\n\n{konten}")
        for chunk in sop_jte_hits:
            konten = chunk.get('konten', '')
            if isinstance(konten, list):
                konten = '\n'.join(konten)
            sop_results.append(f"📗 **SOP JTE — {chunk.get('full_context', 'Info')}**\n\n{konten}")
        if sop_results:
            return "\n\n---\n\n".join(sop_results)

        # 8. Kurikulum Matkul
        fuzzy_kurikulum = self.fuzzy_search_curriculum(expanded_input)
        if fuzzy_kurikulum:
            return fuzzy_kurikulum

        # 9. Fallback
        return (
            "Maaf, saya tidak menemukan jawaban yang relevan. Coba contoh pertanyaan di sidebar, "
            "atau gunakan kategori berikut:\n\n"
            "- **Kurikulum** — `semester 5`, `matkul algoritma`\n"
            "- **Kalender** — `kapan wisuda 128`, `jadwal uts`\n"
            "- **Dosen** — `dosen pak irsan`, `kaprodi ti`\n"
            "- **Pedoman Skripsi** — `aturan margin skripsi`\n"
            "- **Setelah Sidang** — `map biru`, `alur bebas lab`\n"
            "- **SOP** — `prosedur seminar proposal`, `pendaftaran KP`\n"
            "- **Informasi Umum** — `alur pendaftaran`, `beasiswa`, `biaya ukt`, `form sti-1`, `kontak admin`\n"
            f"- `ganti 2018` (Ubah versi kurikulum, saat ini: {self.kurikulum_year})"
        )


# ==========================================
# CACHE BOT (biar gak reload file tiap rerun)
# ==========================================
@st.cache_resource
def load_bot(default_year: str = "2025"):
    return MasterRuleBasedChatbot(default_year=default_year)


# ==========================================
# UI
# ==========================================
bot = load_bot(default_year="2025")

# ---- Sidebar ----
with st.sidebar:
    st.markdown("## 🤖 Chatbot TI UNRI")
    st.caption("Rule-Based + Fuzzy Search")

    st.markdown("### ⚙️ Pengaturan")
    kur_options = list(bot.kurikulum_data.keys()) if bot.kurikulum_data else [bot.kurikulum_year]
    if kur_options:
        current_idx = kur_options.index(bot.kurikulum_year) if bot.kurikulum_year in kur_options else 0
        selected_year = st.selectbox("Versi Kurikulum Aktif", kur_options, index=current_idx)
        if selected_year != bot.kurikulum_year:
            bot.load_curriculum(selected_year)
            st.rerun()

    st.markdown("### 💡 Contoh Pertanyaan")
    examples = [
        "Siapa kaprodi TI?",
        "Visi dan Misi",
        "Kapan wisuda 128?",
        "Semester 3",
        "Isi map biru apa saja?",
        "Prosedur sempro",
        "Syarat semhas",
        "Syarat pengajuan KP",
        "Aturan margin skripsi",
        "Jumlah dosen TI",
        "Alur pendaftaran UNRI",
        "Biaya UKT Teknik Informatika",
        "Beasiswa Pemprov Riau",
        "Download form STI-1",
        "Kontak admin prodi",
        "Prosedur KP MBKM",
    ]
    for q in examples:
        if st.button(q, use_container_width=True, key=f"ex_{q}"):
            st.session_state["pending_input"] = q
            st.rerun()

    st.markdown("### 📂 Sumber Data")
    st.caption(
        "- Kurikulum (2018 & 2025)\n"
        "- Kalender Akademik TA 25/26 & 26/27\n"
        "- Data Dosen\n"
        "- Pedoman Penulisan Skripsi\n"
        "- SOP JTE & SOP Skripsi\n"
        "- Setelah Sidang (Map Biru/Merah & SITEI)\n"
        "- Informasi Umum (Pendaftaran, UKT, Beasiswa,\n"
        "  Form STI/KPTI, Publikasi, KP MBKM, dll.)"
    )

    if st.button("🗑️ Bersihkan Chat", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# ---- Main Area ----
st.title("🤖 Chatbot Teknik Informatika UNRI")
st.caption(
    f"Kurikulum aktif: **{bot.kurikulum_year}** · "
    f"Gunakan chatbot ini untuk bertanya seputar kurikulum, dosen, kalender akademik, skripsi, KP, informasi umum, dan administrasi."
)

# Init chat state
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": (
                "Halo! 👋 Saya asisten virtual Teknik Informatika UNRI.\n\n"
                "Silakan tanyakan apa saja seputar:\n"
                "- Kurikulum & mata kuliah\n"
                "- Jadwal akademik (UTS/UAS/wisuda)\n"
                "- Info dosen\n"
                "- Prosedur skripsi & KP\n"
                "- Alur setelah sidang\n"
                "- Informasi umum (pendaftaran, UKT, beasiswa, form STI/KPTI, publikasi)\n\n"
                "💡 **Tips:** Kamu bisa pakai singkatan seperti:\n"
                "• **sempro** = seminar proposal\n"
                "• **semhas** = seminar hasil / sidang skripsi\n"
                "• **KP** = kerja praktik\n"
                "• **TA** = tugas akhir / skripsi\n"
                "• **UTS/UAS** = ujian tengah/akhir semester\n"
                "• **KRS** = kartu rencana studi\n\n"
                "Kamu juga bisa klik contoh pertanyaan di sidebar."
            ),
        }
    ]

# Tampilkan riwayat chat
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Ambil input user (dari chat_input atau tombol contoh)
user_input = st.chat_input("Ketik pertanyaanmu di sini...")
if not user_input and "pending_input" in st.session_state:
    user_input = st.session_state.pop("pending_input")

if user_input:
    # Simpan pesan user
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban..."):
            response = bot.get_response(user_input)
        st.markdown(response)

    st.session_state["messages"].append({"role": "assistant", "content": response})
