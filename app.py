import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai
import time
import datetime
from statsmodels.tsa.holtwinters import Holt
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(page_title="GenAI-Maint PRO", page_icon="⚙️", layout="wide")

# ==========================================
# SİSTEM HAFIZASI
# ==========================================
if 'makine_durumu' not in st.session_state:
    st.session_state.makine_durumu = 'bekliyor' 
if 'kacinci_satir' not in st.session_state:
    st.session_state.kacinci_satir = 35 
if 'son_rul_degeri' not in st.session_state:
    st.session_state.son_rul_degeri = "Hesaplanıyor..."
if 'son_mail_durumu' not in st.session_state:
    st.session_state.son_mail_durumu = "Henüz mail gönderilmedi."

if 'hata_loglari' not in st.session_state:
    st.session_state.hata_loglari = pd.DataFrame(columns=[
        'Tarih/Saat', 'Vardiya Dk.', 'Olay Tipi', 'Hava Sıc. [K]', 'Hız [RPM]', 'Aşınma [Dk]', 'RUL'
    ])

def sonraki_saglam_veriyi_bul(mevcut_index, veri_seti):
    for j in range(mevcut_index + 1, len(veri_seti)):
        if veri_seti.iloc[j]['Tool wear [min]'] < 15: 
            return j
    return mevcut_index + 1 

# ==========================================
# OTONOM MAİL GÖNDERME MOTORU (YENİ!)
# ==========================================
def otomatik_mail_gonder(olay_tipi, anlik_veri, rul_gosterim, gonderici, sifre, alici):
    if not gonderici or not sifre or not alici:
        return "Mail ayarları eksik olduğu için otonom bildirim gönderilemedi."
    
    try:
        saat = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Olay tipine göre yapılması gerekenleri (Aksiyon Planı) belirliyoruz
        if "Erken Uyarı" in olay_tipi:
            konu = "⚠️ PROAKTİF BAKIM EMRİ: Makine Kritik Eşikte!"
            aksiyon = "Makinenin kalan ömrü kritik eşiğin altına düşmüştür. Makine arızalanmadan önce otonom olarak durdurulmuştur. Lütfen 15 dakika içinde yeni takım montajını gerçekleştirin ve sistemi yeniden başlatın."
        else:
            konu = "🚨 ACİL DURUM: Makine Beklenmedik Şekilde Arızalandı!"
            aksiyon = "Makinede ani takım kırılması / çöküş tespit edilmiştir. Üretim durdu! Lütfen acil müdahale ekibini yönlendirin, hasar tespiti yapın ve mili değiştirin. Detaylı kök neden raporu için GenAI-Maint paneline bakın."

        mesaj_metni = f"""
GenAI-Maint Otonom Sistem Bildirimi
Tarih/Saat: {saat}
Olay: {olay_tipi}

--- ANLIK SENSÖR VERİLERİ ---
Hava Sıcaklığı: {anlik_veri['Air temperature [K]']:.1f} K
Süreç Sıcaklığı: {anlik_veri['Process temperature [K]']:.1f} K
Dönüş Hızı: {anlik_veri['Rotational speed [rpm]']} RPM
Takım Aşınması: {anlik_veri['Tool wear [min]']} Dakika
Kalan Ömür (RUL): {rul_gosterim}

--- YAPILMASI GEREKEN (AKSİYON PLANI) ---
{aksiyon}

Bu mesaj yapay zeka destekli GenAI-Maint sistemi tarafından otonom olarak oluşturulmuştur.
        """
        
        msg = MIMEText(mesaj_metni)
        msg['Subject'] = konu
        msg['From'] = gonderici
        msg['To'] = alici

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(gonderici, sifre)
            smtp_server.sendmail(gonderici, [alici], msg.as_string())
        
        return f"✅ {saat} itibariyle bakım ekibine otonom iş emri başarıyla iletildi."
    except Exception as e:
        return f"❌ Mail gönderilirken hata oluştu: {str(e)}"

# ==========================================
# ARAYÜZ (UI) BAŞLIYOR
# ==========================================
st.title("⚙️ GenAI-Maint 3.0 PRO (Tam Otonom Fabrika)")
st.markdown("*Gerçek Zamanlı Forecasting, Erken Uyarı ve İnsansız Mail Otomasyonu*")

with st.sidebar:
    st.header("📂 Veri Girişi")
    uploaded_file = st.file_uploader("Sensör Verisi (CSV)", type=["csv"])
    
    st.divider()
    st.header("🔑 YZ Ayarları")
    api_key = st.text_input("Gemini API Anahtarı:", type="password")
    erken_uyari_esigi = st.slider("Erken Uyarı Eşiği (RUL - Vardiya)", 5, 30, 15)
    
    st.divider()
    st.header("✉️ Otomasyon (Mail) Ayarları")
    st.info("Otonom mail atılması için bu alanları doldurun.")
    gnd_mail = st.text_input("Gönderici Gmail:", placeholder="seninmailin@gmail.com")
    gnd_sifre = st.text_input("Uygulama Şifresi:", type="password")
    alc_mail = st.text_input("Alıcı (Bakım Şefi) Maili:", value="bakimsefi@fabrika.com")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Canlı Komuta Merkezi", 
    "🧠 YZ Analizi & Rapor", 
    "🚀 Otomasyon & İş Emri", 
    "📜 Hata/Bakım Logları"
])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    with tab1:
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("▶️ Üretimi Başlat / Devam Ettir"):
                st.session_state.makine_durumu = 'calisiyor'
                st.rerun() 
                
        with col_btn2:
            if st.session_state.makine_durumu == 'bakim_gerekiyor':
                if st.button("🛠️ Otonom Planlı Bakımı Uygula (Parçayı Değiştir)"):
                    st.success("✅ Erken Müdahale Başarılı! Üretim başlıyor...")
                    time.sleep(1.5) 
                    st.session_state.makine_durumu = 'calisiyor'
                    st.session_state.kacinci_satir = sonraki_saglam_veriyi_bul(st.session_state.kacinci_satir, df)
                    st.rerun()
            elif st.session_state.makine_durumu == 'arizali':
                if st.button("🚨 Acil Arıza Müdahalesi Yap ve Parçayı Değiştir"):
                    st.success("✅ Arıza Giderildi! Üretim yeniden başlıyor...")
                    time.sleep(1.5) 
                    st.session_state.makine_durumu = 'calisiyor'
                    st.session_state.kacinci_satir = sonraki_saglam_veriyi_bul(st.session_state.kacinci_satir, df)
                    st.rerun()

        st.divider()

        if st.session_state.makine_durumu == 'calisiyor':
            canli_ekran = st.empty()
            
            for i in range(st.session_state.kacinci_satir, len(df)):
                anlik_veri = df.iloc[i]
                gecmis_veri = df.iloc[max(0, i-30):i+1] 
                
                rul_gosterim = "Hesaplanıyor..."
                rul_sayisal = 999 
                
                if len(gecmis_veri) > 5: 
                    try:
                        y_train = gecmis_veri['Tool wear [min]'].values
                        holt_model = Holt(y_train, initialization_method="estimated").fit(optimized=True)
                        gelecek_tahmin = holt_model.forecast(50) 
                        
                        rul = 0
                        for f in gelecek_tahmin:
                            if f >= 200: break
                            rul += 1
                            
                        rul_sayisal = rul
                        rul_gosterim = f"{rul} Vardiya" if rul < 50 else "50+ (Güvenli)"
                        st.session_state.son_rul_degeri = rul_gosterim 
                    except:
                        pass

                with canli_ekran.container():
                    st.subheader(f"⏱️ Anlık Sensör Okuması (Vardiya Dakikası: {i})")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("🌡️ Hava Sıc.", f"{anlik_veri['Air temperature [K]']:.1f} K")
                    col2.metric("🔥 Süreç Sıc.", f"{anlik_veri['Process temperature [K]']:.1f} K")
                    col3.metric("⚙️ Dönüş Hızı", f"{anlik_veri['Rotational speed [rpm]']} RPM")
                    col4.metric("🛠️ Takım Aşınması", f"{anlik_veri['Tool wear [min]']} Dk")
                    
                    if rul_sayisal <= erken_uyari_esigi:
                        col5.metric("⏳ Kalan Ömür (RUL)", rul_gosterim, delta="⚠️ KRİTİK SEVİYE", delta_color="inverse")
                    else:
                        col5.metric("⏳ Kalan Ömür (RUL)", rul_gosterim, delta="Stabil", delta_color="normal")
                    
                    fig = px.line(gecmis_veri, y='Tool wear [min]', title="🔴 Canlı Aşınma Trendi", markers=True)
                    fig.update_traces(line_color='#00CC96') 
                    st.plotly_chart(fig, use_container_width=True)
                
                # ----------------------------------------------------
                # İŞTE BÜYÜK OTOMASYON BURADA TETİKLENİYOR
                # ----------------------------------------------------
                if 0 < rul_sayisal <= erken_uyari_esigi:
                    olay = '⚠️ Erken Uyarı (Planlı Bakım)'
                    su_an = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 1. Loglara Yaz
                    yeni_log = pd.DataFrame([{'Tarih/Saat': su_an, 'Vardiya Dk.': i, 'Olay Tipi': olay, 'Hava Sıc. [K]': anlik_veri['Air temperature [K]'], 'Hız [RPM]': anlik_veri['Rotational speed [rpm]'], 'Aşınma [Dk]': anlik_veri['Tool wear [min]'], 'RUL': rul_gosterim}])
                    st.session_state.hata_loglari = pd.concat([st.session_state.hata_loglari, yeni_log], ignore_index=True)
                    
                    # 2. OTONOM MAİL AT (Şov Kısmı)
                    mail_sonucu = otomatik_mail_gonder(olay, anlik_veri, rul_gosterim, gnd_mail, gnd_sifre, alc_mail)
                    st.session_state.son_mail_durumu = mail_sonucu
                    
                    # 3. Sistemi Durdur
                    st.session_state.makine_durumu = 'bakim_gerekiyor'
                    st.session_state.kacinci_satir = i 
                    canli_ekran.empty() 
                    st.rerun()
                
                elif anlik_veri['Machine failure'] == 1:
                    olay = '🚨 Beklenmedik Arıza (Çöküş)'
                    su_an = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 1. Loglara Yaz
                    yeni_log = pd.DataFrame([{'Tarih/Saat': su_an, 'Vardiya Dk.': i, 'Olay Tipi': olay, 'Hava Sıc. [K]': anlik_veri['Air temperature [K]'], 'Hız [RPM]': anlik_veri['Rotational speed [rpm]'], 'Aşınma [Dk]': anlik_veri['Tool wear [min]'], 'RUL': '0 Vardiya'}])
                    st.session_state.hata_loglari = pd.concat([st.session_state.hata_loglari, yeni_log], ignore_index=True)
                    
                    # 2. OTONOM MAİL AT
                    mail_sonucu = otomatik_mail_gonder(olay, anlik_veri, "0 Vardiya (Çöktü)", gnd_mail, gnd_sifre, alc_mail)
                    st.session_state.son_mail_durumu = mail_sonucu
                    
                    # 3. Sistemi Durdur
                    st.session_state.makine_durumu = 'arizali'
                    st.session_state.kacinci_satir = i 
                    canli_ekran.empty() 
                    st.rerun() 
                
                time.sleep(0.5)

        # DURMA EKRANLARI (Aynı)
        elif st.session_state.makine_durumu == 'bakim_gerekiyor':
            i = st.session_state.kacinci_satir
            anlik_veri = df.iloc[i]
            gecmis_veri = df.iloc[max(0, i-30):i+1]
            st.warning("⚠️ PROAKTİF UYARI: Kalan Ömür Kritik Eşiğin Altına Düştü! Makine Bozulmadan Durduruldu.")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("🌡️ Hava Sıc.", f"{anlik_veri['Air temperature [K]']:.1f} K")
            col2.metric("🔥 Süreç Sıc.", f"{anlik_veri['Process temperature [K]']:.1f} K")
            col3.metric("⚙️ Dönüş Hızı", f"{anlik_veri['Rotational speed [rpm]']} RPM")
            col4.metric("🛠️ Aşınma", f"{anlik_veri['Tool wear [min]']} Dk", delta="Yüksek", delta_color="inverse")
            col5.metric("⏳ Kalan Ömür", st.session_state.son_rul_degeri, delta="Bakım Şart", delta_color="inverse")
            fig = px.line(gecmis_veri, y='Tool wear [min]', title="⚠️ PLANLI BAKIM ZAMANI", markers=True)
            fig.update_traces(line_color='#FFA500') 
            st.plotly_chart(fig, use_container_width=True)

        elif st.session_state.makine_durumu == 'arizali':
            i = st.session_state.kacinci_satir
            anlik_veri = df.iloc[i]
            gecmis_veri = df.iloc[max(0, i-30):i+1]
            st.error("🚨 KRİTİK ALARM: SİSTEM BEKLENMEDİK ŞEKİLDE ÇÖKTÜ!")
            fig = px.line(gecmis_veri, y='Tool wear [min]', title="🚨 ARIZA ANI EKRANI", markers=True)
            fig.update_traces(line_color='#FF0000') 
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("🤖 Gemini Otonom Yönetici Raporu")
        if st.button("🧠 Mevcut Durum Raporunu Oluştur (Gemini API)"):
            if not api_key:
                st.error("Lütfen sol menüden API anahtarını girin!")
            elif st.session_state.makine_durumu == 'calisiyor':
                st.warning("Makine şu an sağlam çalışıyor.")
            else:
                with st.spinner("Gemini sensör verilerini yorumluyor..."):
                    try:
                        genai.configure(api_key=api_key)
                        secilen_model = 'gemini-pro' 
                        for m in genai.list_models():
                            if 'generateContent' in m.supported_generation_methods:
                                if 'flash' in m.name:
                                    secilen_model = m.name
                                    break
                        llm_model = genai.GenerativeModel(secilen_model)
                        
                        if st.session_state.makine_durumu == 'bakim_gerekiyor':
                            senaryo = f"MÜJDE: Makine henüz bozulmadı! Holt algoritmamız kalan ömrü {st.session_state.son_rul_degeri} olarak tahmin etti ve sistemi proaktif olarak biz durdurduk."
                        else:
                            senaryo = "MAALESEF: Makine beklenmedik bir şekilde tamamen çöktü ve arızalandı."
                        
                        prompt = f"""Sen kıdemli bir Endüstri Mühendisisin. DURUM: {senaryo}
                        GÖREV: Fabrika yönetimine markdown formatında profesyonel bir rapor yaz."""
                        response = llm_model.generate_content(prompt)
                        st.success(f"📝 Rapor Oluşturuldu!")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"API Hatası: {e}")

    # ==========================================
    # SEKME 3: OTOMASYON DURUM EKRANI
    # ==========================================
    with tab3:
        st.subheader("🚀 Otonom İş Emri ve Bildirim Merkezi")
        st.write("Sistem, bir arıza veya erken uyarı tespit ettiğinde sol menüdeki ayarlara göre insan müdahalesi olmadan anında e-posta gönderir.")
        
        st.divider()
        st.markdown("### 📡 Son İletişim Durumu")
        
        # Otonom mail atıldıysa durumu burada göster
        if "Başarıyla" in st.session_state.son_mail_durumu or "✅" in st.session_state.son_mail_durumu:
            st.success(st.session_state.son_mail_durumu)
        elif "eksik" in st.session_state.son_mail_durumu.lower() or "henüz" in st.session_state.son_mail_durumu.lower():
            st.info(st.session_state.son_mail_durumu)
        else:
            st.error(st.session_state.son_mail_durumu)
            
        st.caption("Not: Gerçek zamanlı otonom mail testini yapmak için lütfen sol menüden kendi Gmail bilgilerinizi girin ve makineyi arıza eşiğine kadar çalıştırın.")

    with tab4:
        st.subheader("📜 Kalite Kontrol ve Bakım Logları")
        if len(st.session_state.hata_loglari) > 0:
            st.dataframe(st.session_state.hata_loglari, use_container_width=True)
        else:
            st.success("🎉 Şu ana kadar sistemde hiçbir olay kaydedilmedi.")
else:
    st.info("👈 Lütfen sol menüden CSV verisini yükleyin.")