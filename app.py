import streamlit as st
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import google.generativeai as genai # BÜYÜK BEYİN EKLENDİ

# Sayfa ayarları
st.set_page_config(page_title="GenAI-Maint", page_icon="⚙️", layout="wide")

st.title("⚙️ GenAI-Maint")
st.subheader("LLM Destekli Akıllı Fabrika Bakım Asistanı")

# Sol menüde (Sidebar) API Anahtarı alma alanı - Çok profesyonel durur!
with st.sidebar:
    st.header("🔑 API Ayarları")
    api_key = st.text_input("Gemini API Anahtarınızı Girin:", type="password")
    st.markdown("[API Anahtarını Buradan Ücretsiz Alabilirsiniz](https://aistudio.google.com/app/apikey)")
    st.divider()
    st.info("Bu proje Endüstri Mühendisliği Kestirimci Bakım (Predictive Maintenance) vizyonuyla geliştirilmiştir.")

uploaded_file = st.file_uploader("Makine Sensör Verilerini Yükle (CSV)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("✅ Veri başarıyla sisteme aktarıldı!")
    
    if st.button("🚀 Yapay Zeka ile Arıza Analizi Yap"):
        if not api_key:
            st.error("Lütfen soldaki menüden Gemini API anahtarınızı girin!")
        else:
            with st.spinner("Model eğitiliyor ve veriler analiz ediliyor..."):
                # 1. VERİ İŞLEME
                le = LabelEncoder()
                df['Type_Encoded'] = le.fit_transform(df['Type'])
                
                X = df[['Type_Encoded', 'Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']]
                y = df['Machine failure']
                
                # 2. MODEL EĞİTİMİ
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                model.fit(X, y)
                
                # 3. ÖRNEK TAHMİN (Bilerek arızalı 50. satırı seçiyoruz)
                ornek_makine = X.iloc[50:51] 
                tahmin = model.predict(ornek_makine)
                
                st.subheader("📊 Analiz Sonucu")
                if tahmin[0] == 1:
                    st.error("🚨 KRİTİK UYARI: Makinede arıza (Failure) tespit edildi!")
                    
                    # ---- FAZ 3: LLM (GEMINI) ENTEGRASYONU ----
                    st.info("🧠 Gemini Yapay Zeka, sensör verilerini okuyarak bakım raporu hazırlıyor...")
                    try:
                        # Gemini'yi uyandırıyoruz
                        genai.configure(api_key=api_key)
                        
                        # API'deki GÜNCEL VE ÇALIŞAN MODELİ OTOMATİK BULMA (Kurşungeçirmez Taktik)
                        secilen_model = 'gemini-1.5-flash' # Çökerse diye yedek isim
                        for m in genai.list_models():
                            if 'generateContent' in m.supported_generation_methods:
                                secilen_model = m.name
                                if 'flash' in secilen_model: 
                                    break # En hızlısı Flash olduğu için onu bulunca duruyoruz
                                    
                        llm_model = genai.GenerativeModel(secilen_model)
                        
                        # Gemini'ye vereceğimiz "Endüstri Mühendisi" görevi (Prompt)
                        prompt = f"""
                        Sen kıdemli bir Endüstri Mühendisi ve Kestirimci Bakım Uzmanısın.
                        Fabrikadaki bir CNC makinesinde Random Forest algoritmamız bir arıza tespit etti. 
                        Makinenin o anki sensör verileri şunlar:
                        - Hava Sıcaklığı: {ornek_makine['Air temperature [K]'].values[0]} K
                        - Süreç Sıcaklığı: {ornek_makine['Process temperature [K]'].values[0]} K
                        - Dönüş Hızı: {ornek_makine['Rotational speed [rpm]'].values[0]} RPM
                        - Tork: {ornek_makine['Torque [Nm]'].values[0]} Nm
                        - Takım Aşınması: {ornek_makine['Tool wear [min]'].values[0]} dakika.
                        
                        Lütfen teknisyenler ve fabrika yöneticisi için kısa, profesyonel ve adım adım bir 
                        "Acil Bakım ve Kök Neden Analizi Raporu" yaz. Raporu Markdown formatında ve Türkçe hazırla.
                        Endüstri mühendisliği terminolojisi (duruş maliyeti, OEE, kök neden vb.) kullan.
                        """
                        
                        # Yapay zekadan cevabı alıyoruz
                        response = llm_model.generate_content(prompt)
                        
                        st.success(f"📝 Gemini Bakım Raporu Oluşturuldu! (Kullanılan Model: {secilen_model})")
                        
                        # Raporu ekranda gösteriyoruz
                        st.markdown(response.text)
                        
                    except Exception as e:
                        st.error(f"API Hatası oluştu. Lütfen bağlantınızı veya anahtarınızı kontrol edin: {e}")
                else:
                    st.success("✅ Makine şu an sağlıklı çalışıyor. Anomali yok.")
                    