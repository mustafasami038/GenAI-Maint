import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai
import time
import datetime
from statsmodels.tsa.holtwinters import Holt
from sklearn.ensemble import RandomForestClassifier
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
        'Tarih/Saat', 'Vardiya Dk.', 'Tetikleyen AI', 'Olay Tipi', 'Hava Sıc.', 'Hız', 'Aşınma'
    ])
# --- CHATBOT HAFIZASI ---
if 'messages' not in st.session_state:
    st.session_state.messages = []

def sonraki_saglam_veriyi_bul(mevcut_index, veri_seti):
    for j in range(mevcut_index + 1, len(veri_seti)):
        if veri_seti.iloc[j]['Tool wear [min]'] < 15: 
            return j
    return mevcut_index + 1 

@st.cache_resource
def rf_modelini_egit(veri):
    rf = RandomForestClassifier(n_estimators=50, random_state=42)
    ozellikler = ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']
    rf.fit(veri[ozellikler], veri['Machine failure'])
    return rf

def otomatik_mail_gonder(tetikleyen_ai, olay_tipi, anlik_veri, rul_gosterim, gonderici, sifre, alici):
    if not gonderici or not sifre or not alici:
        return "Mail ayarları eksik olduğu için otonom bildirim gönderilemedi."
    try:
        saat = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "Holt" in tetikleyen_ai:
            konu = "⚠️ SARI ALARM (HOLT RUL): Makine Yaşlanma Sınırında!"
            aksiyon = "Holt algoritması kalan ömrün kritik eşiğin altına düştüğünü tespit etti. Planlı bakım başlatıldı."
        else:
            konu = "🚨 KIRMIZI ALARM (RANDOM FOREST): Ani Anomali Tespit Edildi!"
            aksiyon = "Random Forest makine öğrenmesi modeli ani bir şok/kalp krizi tespit etti. Üretim acil durduruldu."

        mesaj_metni = f"GenAI-Maint Bildirimi\nTarih: {saat}\nTetikleyen AI: {tetikleyen_ai}\nOlay: {olay_tipi}\n\n--- SENSÖR DURUMU ---\nHava Sıc: {anlik_veri['Air temperature [K]']:.1f} K\nHız: {anlik_veri['Rotational speed [rpm]']} RPM\nAşınma: {anlik_veri['Tool wear [min]']} Dk\n\n--- AKSİYON ---\n{aksiyon}"
        msg = MIMEText(mesaj_metni)
        msg['Subject'] = konu
        msg['From'] = gonderici
        msg['To'] = alici
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(gonderici, sifre)
            smtp_server.sendmail(gonderici, [alici], msg.as_string())
        return f"✅ {saat} itibariyle otonom iş emri başarıyla iletildi."
    except Exception as e:
        return f"❌ Mail gönderilirken hata oluştu: {str(e)}"

# ==========================================
# ARAYÜZ (UI) BAŞLIYOR
# ==========================================
st.title("⚙️ GenAI-Maint 3.0 PRO (Hibrit AI & Chatbot)")
st.markdown("*Random Forest & Holt Çift Motorlu Otonom Bakım ve Canlı Asistan*")

with st.sidebar:
    st.header("📂 Veri Girişi")
    uploaded_file = st.file_uploader("Sensör Verisi (CSV)", type=["csv"])
    
    st.divider()
    st.header("🔑 YZ Ayarları")
    api_key = st.text_input("Gemini API Anahtarı:", type="password")
    erken_uyari_esigi = st.slider("Holt Erken Uyarı Eşiği (RUL)", 5, 30, 15)
    
    st.divider()
    st.header("✉️ Otomasyon (Mail) Ayarları")
    gnd_mail = st.text_input("Gönderici Gmail:", placeholder="seninmailin@gmail.com")
    gnd_sifre = st.text_input("Uygulama Şifresi:", type="password")
    alc_mail = st.text_input("Alıcı (Bakım Şefi) Maili:", value="bakimsefi@fabrika.com")

# 5 SEKME OLDU!
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Hibrit Komuta Merkezi", 
    "🧠 Gemini Kök Neden Analizi", 
    "🚀 Otonom İş Emri", 
    "📜 Kalite Kontrol Logları",
    "💬 Canlı Asistan (Chatbot)"
])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    rf_model = rf_modelini_egit(df) 
    
    # ==========================================
    # SEKME 1: ESKİ KUSURSUZ KOMUTA MERKEZİ (DEĞİŞTİRİLMEDİ)
    # ==========================================
    with tab1:
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("▶️ Hibrit Üretimi Başlat / Devam Ettir"):
                st.session_state.makine_durumu = 'calisiyor'
                st.rerun() 
                
        with col_btn2:
            if st.session_state.makine_durumu == 'bakim_gerekiyor':
                if st.button("🛠️ Holt Planlı Bakımı Uygula (Parçayı Değiştir)"):
                    st.success("✅ Erken Müdahale Başarılı!")
                    time.sleep(1.5) 
                    st.session_state.makine_durumu = 'calisiyor'
                    st.session_state.kacinci_satir = sonraki_saglam_veriyi_bul(st.session_state.kacinci_satir, df)
                    st.rerun()
            elif st.session_state.makine_durumu == 'arizali':
                if st.button("🚨 Acil RF Arıza Müdahalesi Yap ve Parçayı Değiştir"):
                    st.success("✅ Arıza Giderildi!")
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
                
                ozellikler = ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']
                anlik_features = anlik_veri[ozellikler].to_frame().T
                rf_tahmin = rf_model.predict(anlik_features)[0]
                
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
                    st.markdown("### 🧠 Aktif Yapay Zeka Motorları")
                    col_ai1, col_ai2 = st.columns(2)
                    col_ai1.info("🌲 Random Forest: **Aktif (Ani Şok İzleniyor)**")
                    col_ai2.info("📈 Holt Zaman Serisi: **Aktif (Yaşlanma İzleniyor)**")
                    
                    st.subheader(f"⏱️ Anlık Sensör Okuması (Vardiya Dakikası: {i})")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("🌡️ Hava Sıc.", f"{anlik_veri['Air temperature [K]']:.1f} K")
                    col2.metric("🔥 Süreç Sıc.", f"{anlik_veri['Process temperature [K]']:.1f} K")
                    col3.metric("⚙️ Dönüş Hızı", f"{anlik_veri['Rotational speed [rpm]']} RPM")
                    col4.metric("🛠️ Aşınma", f"{anlik_veri['Tool wear [min]']} Dk")
                    
                    if rul_sayisal <= erken_uyari_esigi:
                        col5.metric("⏳ RUL (Holt)", rul_gosterim, delta="⚠️ SARI ALARM", delta_color="inverse")
                    else:
                        col5.metric("⏳ RUL (Holt)", rul_gosterim, delta="Stabil", delta_color="normal")
                    
                    fig = px.line(gecmis_veri, y='Tool wear [min]', title="🔴 Canlı Aşınma Trendi", markers=True)
                    fig.update_traces(line_color='#00CC96') 
                    st.plotly_chart(fig, use_container_width=True)
                
                if rf_tahmin == 1 or anlik_veri['Machine failure'] == 1:
                    olay = '🚨 Beklenmedik Arıza / Anomali'
                    tetikleyen = 'Random Forest Classifier'
                    su_an = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    yeni_log = pd.DataFrame([{'Tarih/Saat': su_an, 'Vardiya Dk.': i, 'Tetikleyen AI': tetikleyen, 'Olay Tipi': olay, 'Hava Sıc.': anlik_veri['Air temperature [K]'], 'Hız': anlik_veri['Rotational speed [rpm]'], 'Aşınma': anlik_veri['Tool wear [min]']}])
                    st.session_state.hata_loglari = pd.concat([st.session_state.hata_loglari, yeni_log], ignore_index=True)
                    st.session_state.son_mail_durumu = otomatik_mail_gonder(tetikleyen, olay, anlik_veri, "Sıfırlandı (Şok)", gnd_mail, gnd_sifre, alc_mail)
                    st.session_state.makine_durumu = 'arizali'
                    st.session_state.kacinci_satir = i 
                    canli_ekran.empty() 
                    st.rerun() 
                
                elif 0 < rul_sayisal <= erken_uyari_esigi:
                    olay = '⚠️ Erken Uyarı (Yaşlanma Sınırı)'
                    tetikleyen = 'Holt Linear Trend'
                    su_an = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    yeni_log = pd.DataFrame([{'Tarih/Saat': su_an, 'Vardiya Dk.': i, 'Tetikleyen AI': tetikleyen, 'Olay Tipi': olay, 'Hava Sıc.': anlik_veri['Air temperature [K]'], 'Hız': anlik_veri['Rotational speed [rpm]'], 'Aşınma': anlik_veri['Tool wear [min]']}])
                    st.session_state.hata_loglari = pd.concat([st.session_state.hata_loglari, yeni_log], ignore_index=True)
                    st.session_state.son_mail_durumu = otomatik_mail_gonder(tetikleyen, olay, anlik_veri, rul_gosterim, gnd_mail, gnd_sifre, alc_mail)
                    st.session_state.makine_durumu = 'bakim_gerekiyor'
                    st.session_state.kacinci_satir = i 
                    canli_ekran.empty() 
                    st.rerun()
                
                time.sleep(0.5)

        elif st.session_state.makine_durumu == 'bakim_gerekiyor':
            i = st.session_state.kacinci_satir
            anlik_veri = df.iloc[i]
            gecmis_veri = df.iloc[max(0, i-30):i+1]
            st.warning("⚠️ HOLT SARI ALARM: Kalan Ömür Kritik Eşiğin Altına Düştü! Makine Proaktif Olarak Durduruldu.")
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
            st.error("🚨 RANDOM FOREST KIRMIZI ALARM: Sistemde Ani Bir Anomali ve Çöküş Tespit Edildi!")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("🌡️ Hava Sıc.", f"{anlik_veri['Air temperature [K]']:.1f} K", delta="Kritik", delta_color="inverse")
            col2.metric("🔥 Süreç Sıc.", f"{anlik_veri['Process temperature [K]']:.1f} K", delta="Kritik", delta_color="inverse")
            col3.metric("⚙️ Dönüş Hızı", f"{anlik_veri['Rotational speed [rpm]']} RPM", delta="Kritik", delta_color="inverse")
            col4.metric("🛠️ Aşınma", f"{anlik_veri['Tool wear [min]']} Dk", delta="Kritik", delta_color="inverse")
            col5.metric("⏳ Kalan Ömür", "0 Dk", delta="Çöktü", delta_color="inverse")
            fig = px.line(gecmis_veri, y='Tool wear [min]', title="🚨 ARIZA ANI EKRANI", markers=True)
            fig.update_traces(line_color='#FF0000') 
            st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # SEKME 2, 3, 4: ESKİ KUSURSUZ SÜRÜMLER (DEĞİŞTİRİLMEDİ)
    # ==========================================
    with tab2:
        st.subheader("🤖 Gemini Hibrit Kök Neden Analizi")
        if st.button("🧠 Mevcut Durum Raporunu Oluştur (Gemini API)"):
            if not api_key:
                st.error("Lütfen API anahtarını girin!")
            elif st.session_state.makine_durumu == 'calisiyor':
                st.warning("Makine şu an sağlam çalışıyor.")
            else:
                with st.spinner("Gemini sensör verilerini yorumluyor..."):
                    try:
                        genai.configure(api_key=api_key)
                        secilen_model = 'gemini-pro' 
                        for m in genai.list_models():
                            if 'generateContent' in m.supported_generation_methods and 'flash' in m.name:
                                secilen_model = m.name
                                break
                        llm_model = genai.GenerativeModel(secilen_model)
                        
                        if st.session_state.makine_durumu == 'bakim_gerekiyor':
                            senaryo = "SARI ALARM: Holt modeli kalan ömrün bittiğini tespit edip makineyi bozulmadan durdurdu. (Proaktif Başarı)"
                        else:
                            senaryo = "KIRMIZI ALARM: Random Forest modeli, takım aşınmasından bağımsız olarak sıcaklık/tork verilerinde ani bir kalp krizi yakalayıp sistemi kilitledi. (Reaktif Şok)"
                        
                        prompt = f"""Sen kıdemli bir Endüstri Mühendisisin. DURUM: {senaryo}
                        GÖREV: Fabrika yönetimine bu olayın teknik kök nedenini (Holt ve Random Forest bağlamında) ve hemen yapılması gerekenleri açıklayan bir rapor yaz."""
                        response = llm_model.generate_content(prompt)
                        st.success(f"📝 Rapor Oluşturuldu!")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"API Hatası: {e}")

    with tab3:
        st.subheader("🚀 Otonom İş Emri Merkezi")
        if "Başarıyla" in st.session_state.son_mail_durumu or "✅" in st.session_state.son_mail_durumu:
            st.success(st.session_state.son_mail_durumu)
        else:
            st.info(st.session_state.son_mail_durumu)

    with tab4:
        st.subheader("📜 Kalite Kontrol ve Bakım Logları")
        if len(st.session_state.hata_loglari) > 0:
            st.dataframe(st.session_state.hata_loglari, use_container_width=True)
        else:
            st.success("🎉 Şu ana kadar sistemde hiçbir olay kaydedilmedi.")

    # ==========================================
    # YENİ SEKME 5: CANLI ASİSTAN (CHATBOT) DÜZELTİLDİ
    # ==========================================
    with tab5:
        st.subheader("💬 Gemini Canlı Bakım Asistanı")
        st.write("Makine durduğunda (Sarı veya Kırmızı Alarm), o anki verilere dayanarak asistanla teknik konularda sohbet edebilirsiniz.")
        
        # Makine çalışırken kullanıcıyı uyar
        if st.session_state.makine_durumu == 'calisiyor':
            st.warning("⚠️ Makine şu an aktif üretimde. Chatbot'u kullanabilmek için sistemin durmasını (Arıza veya Erken Uyarı) bekleyin.")
        
        chat_container = st.container(height=450, border=True)
        for message in st.session_state.messages:
            with chat_container.chat_message(message["role"]):
                st.markdown(message["content"])
                
        # Makine çalışmıyorsa mesaj kutusunu aktif et
        if st.session_state.makine_durumu != 'calisiyor':
            if prompt := st.chat_input("Gemini Asistanına makine durumuyla ilgili bir soru sor..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with chat_container.chat_message("user"):
                    st.markdown(prompt)
                    
                if not api_key:
                    st.session_state.messages.append({"role": "assistant", "content": "Lütfen sol menüden API anahtarını girin."})
                    st.rerun()
                else:
                    with st.spinner("Gemini düşünüyor..."):
                        try:
                            genai.configure(api_key=api_key)
                            
                            # --- HATAYI ÇÖZEN DİNAMİK MODEL BULUCU ---
                            secilen_model = 'gemini-pro' 
                            for m in genai.list_models():
                                if 'generateContent' in m.supported_generation_methods and 'flash' in m.name:
                                    secilen_model = m.name
                                    break
                            model = genai.GenerativeModel(secilen_model)
                            # ----------------------------------------
                            
                            d = df.iloc[st.session_state.kacinci_satir] 
                            canli_context = f"""
                            Sen fabrikada çalışan teknisyenlere yardım eden bir Endüstri Mühendisi Asistanısın. 
                            Şu an makinenin durumu: {st.session_state.makine_durumu.upper()}.
                            CANLI sensör verileri: 
                            Hava Sıc: {d['Air temperature [K]']}K, Süreç Sıc: {d['Process temperature [K]']}K, 
                            Devir: {d['Rotational speed [rpm]']}RPM, Aşınma: {d['Tool wear [min]']} Dk.
                            Kalan Ömür (Holt RUL): {st.session_state.son_rul_degeri}
                            
                            Kullanıcının sorusu: {prompt}
                            Lütfen bu verilere dayanarak net, teknik ve çözüm odaklı bir cevap ver.
                            """
                            response = model.generate_content(canli_context)
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                            st.rerun()
                        except Exception as e:
                            st.error(f"Chatbot Hatası: {e}")

else:
    st.info("👈 Lütfen sol menüden CSV verisini yükleyin.")