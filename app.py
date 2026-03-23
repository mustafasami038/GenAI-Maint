import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai
import time
import datetime # ZAMAN/SAAT KÜTÜPHANESİ EKLENDİ

# 1. SAYFA AYARLARI
st.set_page_config(page_title="GenAI-Maint PRO", page_icon="⚙️", layout="wide")

# ==========================================
# SİSTEM HAFIZASI VE LOG (KAYIT) DEFTERİ KURULUMU
# ==========================================
if 'makine_durumu' not in st.session_state:
    st.session_state.makine_durumu = 'bekliyor' 
if 'kacinci_satir' not in st.session_state:
    st.session_state.kacinci_satir = 35 

# KALİTE KONTROL: Hata loglarını tutacağımız boş tabloyu yaratıyoruz
if 'hata_loglari' not in st.session_state:
    st.session_state.hata_loglari = pd.DataFrame(columns=[
        'Tarih/Saat', 'Vardiya Dk.', 'Hava Sıc. [K]', 'Süreç Sıc. [K]', 'Hız [RPM]', 'Tork [Nm]', 'Aşınma [Dk]'
    ])

st.title("⚙️ GenAI-Maint 3.0 PRO (Canlı IoT Simülasyonu)")
st.markdown("*Gerçek Zamanlı Sensör Verisi Akışı ve Otonom Müdahale Sistemi*")

# SOL MENÜ
with st.sidebar:
    st.header("📂 Veri Girişi")
    uploaded_file = st.file_uploader("Sensör Verisi (CSV)", type=["csv"])
    st.divider()
    st.header("🔑 Sistem Ayarları")
    api_key = st.text_input("Gemini API Anahtarınızı Girin:", type="password")

# YENİ MİMARİ: ARTIK 4 SEKMEMİZ VAR
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Canlı Komuta Merkezi", 
    "🧠 YZ Analizi & Rapor", 
    "🚀 Otomasyon & İş Emri", 
    "📜 Hata Logları (Kalite Kontrol)"
])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # ==========================================
    # SEKME 1: CANLI DASHBOARD SİMÜLASYONU
    # ==========================================
    with tab1:
        st.info("💡 **Sunum Modu:** Canlı akışı başlatın, arızayı görün ve otonom müdahale ile sistemi kurtarın.")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("▶️ Makineyi Çalıştır / Devam Ettir"):
                st.session_state.makine_durumu = 'calisiyor'
                st.rerun() 
                
        with col_btn2:
            if st.session_state.makine_durumu == 'arizali':
                if st.button("🔧 Parçayı Değiştir ve Üretime Devam Et"):
                    st.success("✅ Otonom Bakım Tamamlandı! Hatalı parça değiştirildi. Sistem yeniden başlatılıyor...")
                    time.sleep(1.5) 
                    st.session_state.makine_durumu = 'calisiyor'
                    st.session_state.kacinci_satir += 1 # Arızayı atlayıp tam 1 sonrasından devam et
                    st.rerun()

        st.divider()

        # CANLI AKIŞ MOTORU
        if st.session_state.makine_durumu == 'calisiyor':
            canli_ekran = st.empty()
            
            for i in range(st.session_state.kacinci_satir, len(df)):
                anlik_veri = df.iloc[i]
                gecmis_veri = df.iloc[max(0, i-20):i+1] 
                
                with canli_ekran.container():
                    st.subheader(f"⏱️ Anlık Sensör Okuması (Vardiya Dakikası: {i})")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    col1.metric(label="🌡️ Hava Sıcaklığı", value=f"{anlik_veri['Air temperature [K]']:.1f} K")
                    col2.metric(label="🔥 Süreç Sıcaklığı", value=f"{anlik_veri['Process temperature [K]']:.1f} K")
                    col3.metric(label="⚙️ Dönüş Hızı", value=f"{anlik_veri['Rotational speed [rpm]']} RPM")
                    col4.metric(label="🛠️ Takım Aşınması", value=f"{anlik_veri['Tool wear [min]']} Dk")
                    
                    fig = px.line(gecmis_veri, y='Tool wear [min]', title="🔴 Canlı Aşınma Trendi", markers=True)
                    fig.update_traces(line_color='#00CC96') 
                    st.plotly_chart(fig, use_container_width=True)
                
                # 🚨 ARIZA TESPİTİ VE KAYIT (LOG) İŞLEMİ
                if anlik_veri['Machine failure'] == 1:
                    if st.session_state.makine_durumu == 'calisiyor':
                        # 1. O anın saatini al
                        su_an = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 2. Verileri paketle
                        yeni_hata = pd.DataFrame([{
                            'Tarih/Saat': su_an,
                            'Vardiya Dk.': i,
                            'Hava Sıc. [K]': anlik_veri['Air temperature [K]'],
                            'Süreç Sıc. [K]': anlik_veri['Process temperature [K]'],
                            'Hız [RPM]': anlik_veri['Rotational speed [rpm]'],
                            'Tork [Nm]': anlik_veri['Torque [Nm]'],
                            'Aşınma [Dk]': anlik_veri['Tool wear [min]']
                        }])
                        
                        # 3. Log defterine (hafızaya) yeni satırı ekle
                        st.session_state.hata_loglari = pd.concat([st.session_state.hata_loglari, yeni_hata], ignore_index=True)
                        
                        # 4. Sistemi durdur
                        st.session_state.makine_durumu = 'arizali'
                        st.session_state.kacinci_satir = i 
                        canli_ekran.empty() 
                        st.rerun() 
                
                time.sleep(0.5)

        # ARIZA EKRANI
        elif st.session_state.makine_durumu == 'arizali':
            i = st.session_state.kacinci_satir
            anlik_veri = df.iloc[i]
            gecmis_veri = df.iloc[max(0, i-20):i+1]
            
            st.error("🚨 KRİTİK ALARM: SİSTEMDE ANOMALİ TESPİT EDİLDİ! MAKİNE ACİL DURDURULDU!")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(label="🌡️ Hava Sıcaklığı", value=f"{anlik_veri['Air temperature [K]']:.1f} K", delta="Kritik", delta_color="inverse")
            col2.metric(label="🔥 Süreç Sıcaklığı", value=f"{anlik_veri['Process temperature [K]']:.1f} K", delta="Kritik", delta_color="inverse")
            col3.metric(label="⚙️ Dönüş Hızı", value=f"{anlik_veri['Rotational speed [rpm]']} RPM", delta="Kritik", delta_color="inverse")
            col4.metric(label="🛠️ Takım Aşınması", value=f"{anlik_veri['Tool wear [min]']} Dk", delta="Kritik", delta_color="inverse")
            
            fig = px.line(gecmis_veri, y='Tool wear [min]', title="🚨 ARIZA ANI EKRANI", markers=True)
            fig.update_traces(line_color='#FF0000') 
            st.plotly_chart(fig, use_container_width=True)
            
            st.warning("👉 Otonom sistemi test etmek için yukarıdaki '🔧 Parçayı Değiştir' butonuna basarak üretime devam edin!")

    # ==========================================
    # SEKME 2 & 3: YZ ANALİZİ VE OTOMASYON
    # ==========================================
    with tab2:
        st.subheader("🤖 Gemini Otonom Kök Neden Analizi")
        if st.button("🧠 Arıza Raporu Oluştur (Gemini API)"):
            if not api_key:
                st.error("Lütfen sol menüden API anahtarını girin!")
            else:
                with st.spinner("Gemini sensör verilerini yorumluyor..."):
                    try:
                        genai.configure(api_key=api_key)
                        secilen_model = 'gemini-1.5-flash'
                        for m in genai.list_models():
                            if 'generateContent' in m.supported_generation_methods:
                                secilen_model = m.name
                                if 'flash' in secilen_model: break
                                    
                        llm_model = genai.GenerativeModel(secilen_model)
                        prompt = f"""Bir Endüstri Mühendisi olarak şu anki makine verilerine göre arıza raporu yaz: Makine arıza yaptı. Takım aşınması kritik seviyede. Ne yapılmalı?"""
                        response = llm_model.generate_content(prompt)
                        st.success(f"📝 Rapor Oluşturuldu!")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"API Hatası: {e}")

    with tab3:
        st.subheader("Otonom İş Emri ve Bildirim Merkezi")
        st.write("Bakım Şefine mail atılacak alan.")

    # ==========================================
    # SEKME 4: YENİ HATALAR (LOG) SAYFASI
    # ==========================================
    with tab4:
        st.subheader("📜 Geçmiş Arıza Kayıtları (Loglar)")
        st.write("Sistem çalışırken tespit edilen tüm anomaliler ve sensör verileri burada tarihsel olarak tutulur.")
        
        # Eğer log defterinde veri varsa ekrana bas
        if len(st.session_state.hata_loglari) > 0:
            st.dataframe(st.session_state.hata_loglari, use_container_width=True)
            
            # Excel olarak indirme şovu
            csv = st.session_state.hata_loglari.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Logları Excel (CSV) Olarak İndir",
                data=csv,
                file_name='ariza_loglari.csv',
                mime='text/csv',
            )
        else:
            st.success("🎉 Şu ana kadar sistemde hiçbir arıza kaydedilmedi. Üretim kusursuz devam ediyor.")

else:
    st.info("👈 Lütfen sol menüden CSV verisini yükleyin.")