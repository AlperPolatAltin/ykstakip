import streamlit as st
import psycopg2
from datetime import date

# --- SENİN GİZLİ KOÇLUK KODUN ---
ADMIN_KODU = "YKSKOCU2026" 

# --- BULUT VERİTABANI BAĞLANTISI (PostgreSQL) ---
@st.cache_resource
def init_connection():
    # Streamlit Secrets (Gizli Kasa) içinden veritabanı URL'sini çekiyoruz
    return psycopg2.connect(st.secrets["DB_URL"])

try:
    conn = init_connection()
    conn.autocommit = True # Her işlemi otomatik kaydet
    c = conn.cursor()

    # PostgreSQL'de id için AUTOINCREMENT yerine SERIAL kullanılır
    c.execute('''CREATE TABLE IF NOT EXISTS kullanicilar 
                 (email TEXT PRIMARY KEY, sifre TEXT, yetki TEXT, koc_email TEXT, isim_soyisim TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS konular 
                 (id SERIAL PRIMARY KEY, email TEXT, ders TEXT, konu TEXT, 
                 baslangic_tarihi TEXT, hedef_tarih TEXT, tamamlanma_tarihi TEXT, 
                 bitti_mi INTEGER, koc_email TEXT)''')
except Exception as e:
    st.error(f"Veritabanına bağlanılamadı: {e}")
    st.stop()

# --- YARDIMCI FONKSİYONLAR ---
def kayit_ol(email, sifre, yetki, koc_email="", isim_soyisim=""):
    try:
        # PostgreSQL'de ? yerine %s kullanılır
        c.execute("INSERT INTO kullanicilar (email, sifre, yetki, koc_email, isim_soyisim) VALUES (%s, %s, %s, %s, %s)", 
                  (email, sifre, yetki, koc_email, isim_soyisim))
        return True
    except psycopg2.IntegrityError:
        conn.rollback() # Hata alırsak işlemi geri al (Postgres kuralları)
        return False

def giris_yap(email, sifre):
    c.execute("SELECT yetki, koc_email, isim_soyisim FROM kullanicilar WHERE email=%s AND sifre=%s", (email, sifre))
    return c.fetchone()

def tarih_formatla(tarih_str):
    if not tarih_str: return ""
    try:
        y, m, d = str(tarih_str).split('-')
        return f"{d}.{m}.{y}"
    except:
        return str(tarih_str)

def ogrenci_sil(ogr_email):
    c.execute("DELETE FROM konular WHERE email=%s", (ogr_email,))
    c.execute("DELETE FROM kullanicilar WHERE email=%s", (ogr_email,))

# Sayfa ayarları
st.set_page_config(page_title="YKS Koçluk Sistemi", layout="wide")

if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False

# --- 1. GİRİŞ / KAYIT EKRANI ---
if not st.session_state.giris_yapildi:
    st.title("🔐 Sisteme Giriş")
    islem = st.radio("İşlem Seçin", ["Giriş Yap", "Koç Olarak Kayıt Ol"])
    
    with st.form("auth_form"):
        email = st.text_input("E-mail")
        sifre = st.text_input("Şifre", type="password")
        
        if islem == "Koç Olarak Kayıt Ol":
            isim_soyisim = st.text_input("Adınız Soyadınız")
            onay_kodu = st.text_input("Koçluk Onay Kodu (Sadece Yetkililer)", type="password")
            submit = st.form_submit_button("Kayıt Ol")
            
            if submit:
                if onay_kodu == ADMIN_KODU and isim_soyisim:
                    if kayit_ol(email, sifre, "Yönetici (Koç)", email, isim_soyisim):
                        st.success("Koç kaydı başarılı! Şimdi giriş yapabilirsiniz.")
                    else:
                        st.error("Bu e-mail adresi zaten kullanımda!")
                elif not isim_soyisim:
                    st.warning("Lütfen adınızı soyadınızı giriniz.")
                else:
                    st.error("Onay kodu hatalı! Kayıt yapılamadı.")
                    
        else: # Giriş Yap
            submit = st.form_submit_button("Giriş")
            if submit:
                kullanici = giris_yap(email, sifre)
                if kullanici:
                    st.session_state.giris_yapildi = True
                    st.session_state.email = email
                    st.session_state.yetki = kullanici[0]
                    st.session_state.isim_soyisim = kullanici[2]
                    st.success("Giriş başarılı!")
                    st.rerun()
                else:
                    st.error("E-mail veya şifre hatalı!")

# --- 2. ANA PANEL ---
if st.session_state.giris_yapildi:
    col_a, col_b = st.columns([4, 1])
    col_a.title("📚 Öğrenci Takip Paneli")
    col_a.write(f"👤 **Giriş Yapan:** {st.session_state.isim_soyisim} ({st.session_state.yetki})")
    if col_b.button("Çıkış Yap"):
        st.session_state.clear()
        st.rerun()
        
    st.divider()

    yks_dersleri = [
        "TYT Türkçe", "TYT Matematik", "TYT Fizik", "TYT Kimya", "TYT Biyoloji", 
        "TYT Tarih", "TYT Coğrafya", "TYT Din", "TYT Felsefe", 
        "AYT Matematik", "AYT Fizik", "AYT Kimya", "AYT Biyoloji",
        "AYT Edebiyat", "AYT Tarih-1", "AYT Coğrafya-1"
    ]

    # --- KOÇ YETKİSİ ÖZEL PANELİ ---
    if st.session_state.yetki == "Yönetici (Koç)":
        koçun_maili = st.session_state.email
        
        sol_kolon, sag_kolon = st.columns(2)
        
        with sol_kolon:
            st.subheader("👤 Yeni Öğrenci Ekle")
            with st.form("ogrenci_ekle_form", clear_on_submit=True):
                ogr_isim = st.text_input("Öğrencinin Adı Soyadı")
                ogr_email = st.text_input("Öğrencinin E-mail Adresi")
                ogr_sifre = st.text_input("Geçici Şifre Belirle")
                if st.form_submit_button("Sisteme Kaydet"):
                    if ogr_isim and ogr_email and ogr_sifre:
                        if kayit_ol(ogr_email, ogr_sifre, "Öğrenci", koçun_maili, ogr_isim):
                            st.success(f"{ogr_isim} başarıyla sisteme eklendi!")
                        else:
                            st.error("Bu öğrenci maili zaten kayıtlı!")
                    else:
                        st.warning("Lütfen tüm alanları doldurunuz.")
            
            st.divider()
            st.subheader("🗑️ Öğrenci Sil")
            c.execute("SELECT email, isim_soyisim FROM kullanicilar WHERE yetki='Öğrenci' AND koc_email=%s", (koçun_maili,))
            silinecek_ogrenciler = c.fetchall()
            
            if silinecek_ogrenciler:
                ogr_sil_sozlugu = {f"{isim} ({mail})": mail for mail, isim in silinecek_ogrenciler}
                with st.form("ogrenci_sil_form"):
                    silinecek_secim = st.selectbox("Silinecek Öğrenciyi Seç", list(ogr_sil_sozlugu.keys()))
                    if st.form_submit_button("Öğrenciyi Sistemden Çıkar"):
                        hedef_mail = ogr_sil_sozlugu[silinecek_secim]
                        ogrenci_sil(hedef_mail)
                        st.success(f"{silinecek_secim} başarıyla silindi!")
                        st.rerun()
            else:
                st.info("Kayıtlı öğrenci bulunmuyor.")
        
        with sag_kolon:
            st.subheader("📌 Görev Ata")
            c.execute("SELECT email, isim_soyisim FROM kullanicilar WHERE yetki='Öğrenci' AND koc_email=%s", (koçun_maili,))
            ogrenciler = c.fetchall()
            
            if ogrenciler:
                ogr_gosterim_sozlugu = {f"{isim} ({mail})": mail for mail, isim in ogrenciler}
                with st.form("konu_ekle_form", clear_on_submit=True):
                    secilen_etiket = st.selectbox("Öğrenci Seç", list(ogr_gosterim_sozlugu.keys()))
                    secilen_ogrenci_maili = ogr_gosterim_sozlugu[secilen_etiket] 
                    
                    ders = st.selectbox("Ders", yks_dersleri)
                    konu = st.text_input("Konu Adı")
                    
                    tarih_col1, tarih_col2 = st.columns(2)
                    baslangic = tarih_col1.date_input("Başlangıç Tarihi", value=date.today())
                    hedef = tarih_col2.date_input("Hedef Bitiş Tarihi", min_value=date.today())
                    
                    if st.form_submit_button("Görevi Ata") and konu:
                        c.execute('''INSERT INTO konular 
                                     (email, ders, konu, baslangic_tarihi, hedef_tarih, tamamlanma_tarihi, bitti_mi, koc_email) 
                                     VALUES (%s, %s, %s, %s, %s, '', 0, %s)''', 
                                  (secilen_ogrenci_maili, ders, konu, str(baslangic), str(hedef), koçun_maili))
                        st.success("Görev başarıyla atandı!")
            else:
                st.info("Önce sol taraftan sisteme öğrenci eklemelisin.")

        st.divider()

        sekme_koc_1, sekme_koc_2 = st.tabs(["⏳ Öğrencilerin Bekleyen Görevleri", "✅ Biten Görevler Geçmişi"])
        
        with sekme_koc_1:
            c.execute('''SELECT k.email, u.isim_soyisim, k.ders, k.konu, k.baslangic_tarihi, k.hedef_tarih 
                         FROM konular k 
                         JOIN kullanicilar u ON k.email = u.email 
                         WHERE k.koc_email=%s AND k.bitti_mi=0 
                         ORDER BY k.hedef_tarih ASC''', (koçun_maili,))
            bekleyenler = c.fetchall()
            
            if not bekleyenler:
                 st.info("Tüm öğrenciler görevlerini tamamlamış, bekleyen görev yok!")
            else:
                koc_bekleyen_gruplu = {}
                for ogr_mail, ogr_isim, d, k, bas, hedef in bekleyenler:
                    gosterim_adi = f"{ogr_isim} ({ogr_mail})"
                    if gosterim_adi not in koc_bekleyen_gruplu:
                        koc_bekleyen_gruplu[gosterim_adi] = {}
                    if d not in koc_bekleyen_gruplu[gosterim_adi]:
                        koc_bekleyen_gruplu[gosterim_adi][d] = []
                    koc_bekleyen_gruplu[gosterim_adi][d].append((k, bas, hedef))
                
                for ogr_adi, ders_sozlugu in koc_bekleyen_gruplu.items():
                    st.markdown(f"### 🧑‍🎓 Öğrenci: {ogr_adi}")
                    for d, gorev_listesi in ders_sozlugu.items():
                        with st.expander(f"📘 {d} ({len(gorev_listesi)} Bekleyen Görev)"):
                            for k, bas, hedef in gorev_listesi:
                                st.warning(f"📖 **{k}** | Başlangıç: {tarih_formatla(bas)} ➡️ Hedef: **{tarih_formatla(hedef)}**")
                    st.divider()

        with sekme_koc_2:
            c.execute('''SELECT k.email, u.isim_soyisim, k.ders, k.konu, k.baslangic_tarihi, k.hedef_tarih, k.tamamlanma_tarihi 
                         FROM konular k 
                         JOIN kullanicilar u ON k.email = u.email 
                         WHERE k.koc_email=%s AND k.bitti_mi=1 
                         ORDER BY k.tamamlanma_tarihi DESC''', (koçun_maili,))
            bitenler = c.fetchall()
            
            if not bitenler:
                 st.info("Henüz tamamlanmış bir görev bulunmuyor.")
            else:
                koc_biten_gruplu = {}
                for ogr_mail, ogr_isim, d, k, bas, hedef, tamamlanma in bitenler:
                    gosterim_adi = f"{ogr_isim} ({ogr_mail})"
                    if gosterim_adi not in koc_biten_gruplu:
                        koc_biten_gruplu[gosterim_adi] = {}
                    if d not in koc_biten_gruplu[gosterim_adi]:
                        koc_biten_gruplu[gosterim_adi][d] = []
                    koc_biten_gruplu[gosterim_adi][d].append((k, bas, hedef, tamamlanma))
                
                for ogr_adi, ders_sozlugu in koc_biten_gruplu.items():
                    st.markdown(f"### 🧑‍🎓 Öğrenci: {ogr_adi}")
                    for d, gorev_listesi in ders_sozlugu.items():
                        with st.expander(f"📚 {d} ({len(gorev_listesi)} Görev Tamamlandı)"):
                            for k, bas, hedef, tamamlanma in gorev_listesi:
                                st.success(f"✔️ **{k}** | 🎯 Hedef: {tarih_formatla(hedef)} | 🏆 Bitiş: **{tarih_formatla(tamamlanma)}**")
                    st.divider()

    # --- ÖĞRENCİ YETKİSİ ÖZEL PANELİ ---
    else: 
        st.subheader(f"🎓 {st.session_state.isim_soyisim} - Çalışma Paneli")
        sekme_ogr_1, sekme_ogr_2 = st.tabs(["⏳ Bekleyen Görevlerim", "✅ Geçmiş (Bitenler)"])
        
        with sekme_ogr_1:
            c.execute("SELECT id, ders, konu, baslangic_tarihi, hedef_tarih FROM konular WHERE email=%s AND bitti_mi=0 ORDER BY hedef_tarih ASC", (st.session_state.email,))
            bekleyenler = c.fetchall()
            
            if not bekleyenler:
                 st.info("Harika! Bekleyen hiçbir görevin yok. Koçun yeni görevler atayacaktır.")
            else:
                bekleyen_gruplu = {}
                for gorev in bekleyenler:
                    gorev_id, d, k, bas, hedef = gorev
                    if d not in bekleyen_gruplu:
                        bekleyen_gruplu[d] = []
                    bekleyen_gruplu[d].append((gorev_id, k, bas, hedef))
                
                for ders_adi, gorev_listesi in bekleyen_gruplu.items():
                    st.markdown(f"#### 📘 {ders_adi}")
                    for gorev_id, k, bas, hedef in gorev_listesi:
                        with st.container(border=True):
                            col1, col2, col3 = st.columns([4, 2, 1])
                            col1.write(f"📖 {k}")
                            col2.write(f"📅 {tarih_formatla(bas)} ➡️ 🎯 **{tarih_formatla(hedef)}**")
                            
                            if col3.button("✔️ Bitti", key=f"btn_{gorev_id}"):
                                bugun = str(date.today())
                                c.execute("UPDATE konular SET bitti_mi=1, tamamlanma_tarihi=%s WHERE id=%s", (bugun, gorev_id))
                                st.rerun()
                                
        with sekme_ogr_2:
            c.execute("SELECT ders, konu, baslangic_tarihi, hedef_tarih, tamamlanma_tarihi FROM konular WHERE email=%s AND bitti_mi=1 ORDER BY tamamlanma_tarihi DESC", (st.session_state.email,))
            bitenler = c.fetchall()
            
            if not bitenler:
                 st.info("Henüz tamamladığın bir görev bulunmuyor.")
            else:
                biten_gruplu = {}
                for gorev in bitenler:
                    d, k, bas, hedef, tamamlanma = gorev
                    if d not in biten_gruplu:
                        biten_gruplu[d] = []
                    biten_gruplu[d].append((k, bas, hedef, tamamlanma))
                
                for ders_adi, gorev_listesi in biten_gruplu.items():
                    with st.expander(f"📚 {ders_adi} ({len(gorev_listesi)} Görev Tamamlandı)"):
                        for k, bas, hedef, tamamlanma in gorev_listesi:
                            st.success(f"✔️ **{k}** | 🎯 Hedef: {tarih_formatla(hedef)} | 🏆 Bitiş: **{tarih_formatla(tamamlanma)}**")
