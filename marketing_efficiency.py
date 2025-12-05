import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(
    page_title="Dashboard Segmentasi Pelanggan & Efisiensi Marketing",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Judul & Intro ---
st.title("Dashboard Segmentasi Pelanggan & Efisiensi Marketing")
st.markdown("""
Aplikasi ini menganalisis perilaku pelanggan menggunakan **K-Means Clustering** untuk mengidentifikasi persona user
dan mengevaluasi efektivitas channel marketing berdasarkan data **Digital Marketing**.
""")


# --- 1. Load Data ---
@st.cache_data
def load_data():
    # Menggunakan URL dataset dari notebook
    url = 'https://storage.googleapis.com/dqlab-dataset/komdigi/tbl_customer.csv'
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return None


df = load_data()

if df is not None:
    # Sidebar untuk Filter
    st.sidebar.header("⚙️ Konfigurasi")

    # Opsi melihat data mentah
    if st.sidebar.checkbox("Tampilkan Data Mentah", False):
        st.subheader("Dataset Preview")
        st.write(df.head())
        st.write(f"Total Baris: {df.shape[0]}, Total Kolom: {df.shape[1]}")

    # --- 2. Data Preparation & Clustering ---
    features = ['clicks', 'page_views', 'time_spent', 'add_to_cart']
    X = df[features]

    # Scaling
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Sidebar untuk jumlah cluster
    n_clusters = st.sidebar.slider("Jumlah Cluster (K-Means)", 2, 6, 4)

    # Menjalankan K-Means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_scaled)
    df['cluster'] = cluster_labels

    # Profiling Cluster
    cluster_summary = df.groupby('cluster')[features + ['conversion_label']].mean()
    cluster_summary['count'] = df['cluster'].value_counts()
    cluster_summary['conversion_rate'] = cluster_summary['conversion_label'] * 100


    # Logic penamaan cluster otomatis (Heuristik sederhana berdasarkan nilai max)
    # Kita mencoba memetakan nama berdasarkan karakteristik dominan
    def get_cluster_name(row):
        # Jika add_to_cart sangat tinggi -> Ready to Buy
        if row['add_to_cart'] > 0.8: return "The Ready-to-Buy (VIP)"
        # Jika time_spent sangat tinggi -> Deep Researcher
        if row['time_spent'] > 300: return "The Deep Researcher"
        # Jika clicks tinggi tapi add_to_cart rendah -> Window Shopper
        if row['clicks'] > 5 and row['add_to_cart'] < 0.2: return "The Window Shopper"
        # Sisanya -> Casual/Low Engagement
        return "Low Engagement / Passerby"


    cluster_summary['Persona'] = cluster_summary.apply(get_cluster_name, axis=1)

    # --- 3. Dashboard Layout ---

    # Tab Navigasi
    tab1, tab2, tab3 = st.tabs(["Segmentasi User (Persona)", "Efisiensi Channel", "Action Plan"])

    with tab1:
        st.subheader("Analisis Persona User")

        col1, col2 = st.columns([2, 1])

        with col1:
            # Heatmap
            st.markdown("**Fingerprint Perilaku per Cluster**")
            fig_heat, ax_heat = plt.subplots(figsize=(10, 6))
            sns.heatmap(cluster_summary[features].T, cmap='YlGnBu', annot=True, fmt='.2f', ax=ax_heat)
            st.pyplot(fig_heat)

        with col2:
            st.markdown("**Statistik Ringkasan Cluster**")
            # Menampilkan dataframe summary yang sudah dirapikan
            display_cols = ['Persona', 'count', 'conversion_rate', 'time_spent']
            st.dataframe(
                cluster_summary[display_cols].style.background_gradient(subset=['conversion_rate'], cmap='Greens'))

        # PCA Plot
        st.markdown("---")
        st.markdown("**Peta Persebaran User (PCA 2D)**")

        pca = PCA(n_components=2)
        coords = pca.fit_transform(X_scaled)
        pca_df = pd.DataFrame(coords, columns=['PC1', 'PC2'])
        pca_df['cluster'] = df['cluster'].astype(str)
        pca_df['Persona'] = df['cluster'].map(cluster_summary['Persona'])

        fig_pca, ax_pca = plt.subplots(figsize=(10, 6))
        sns.scatterplot(data=pca_df, x='PC1', y='PC2', hue='Persona', palette='viridis', alpha=0.6, s=15, ax=ax_pca)
        plt.title("Visualisasi Cluster dalam 2 Dimensi")
        st.pyplot(fig_pca)

    with tab2:
        st.subheader("Analisis Performa Channel Marketing")

        # Hitung Efisiensi
        marketing_efficiency = df.groupby('referral_source').agg({
            'conversion_label': 'mean',
            'time_spent': 'mean',
            'user_id': 'count'
        }).rename(columns={'conversion_label': 'conversion_rate', 'user_id': 'traffic_volume'})

        marketing_efficiency['conversion_rate'] = marketing_efficiency['conversion_rate'] * 100

        # Layout 2 Kolom
        col_eff1, col_eff2 = st.columns(2)

        with col_eff1:
            st.markdown("**1. Conversion Rate per Channel (%)**")
            fig_bar, ax_bar = plt.subplots(figsize=(8, 5))
            barplot = sns.barplot(x=marketing_efficiency.index, y='conversion_rate', data=marketing_efficiency,
                                  palette='viridis', ax=ax_bar)

            # Labeling
            for container in ax_bar.containers:
                ax_bar.bar_label(container, fmt='%.1f%%', padding=3)

            plt.ylim(0, 25)
            plt.ylabel("Conversion Rate (%)")
            st.pyplot(fig_bar)
            st.caption("Insight: Conversion rate relatif merata (flat) di semua channel.")

        with col_eff2:
            st.markdown("**2. Volume Traffic per Channel**")
            fig_vol, ax_vol = plt.subplots(figsize=(8, 5))
            sns.barplot(x=marketing_efficiency.index, y='traffic_volume', data=marketing_efficiency, palette='magma',
                        ax=ax_vol)
            plt.ylabel("Jumlah User")
            st.pyplot(fig_vol)
            st.caption("Insight: Google (Organic) dan Instagram mendominasi traffic.")

        st.markdown("---")
        st.markdown("**3. Kualitas Traffic: Segmen mana yang dibawa oleh Channel mana?**")

        # Attribution Stacked Bar
        channel_cluster_dist = pd.crosstab(df['referral_source'], df['cluster'], normalize='index') * 100

        # Mapping nama persona ke kolom untuk legend yang lebih baik
        persona_map = cluster_summary['Persona'].to_dict()
        channel_cluster_dist.columns = [persona_map.get(c, c) for c in channel_cluster_dist.columns]

        fig_stack, ax_stack = plt.subplots(figsize=(10, 6))
        channel_cluster_dist.plot(kind='bar', stacked=True, colormap='Set2', ax=ax_stack)

        # Label di tengah bar
        for c in ax_stack.containers:
            ax_stack.bar_label(c, fmt='%.0f%%', label_type='center', color='white', fontweight='bold', fontsize=9)

        plt.legend(title='Persona', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.title("Proporsi Persona User di Setiap Channel")
        plt.ylabel("Proporsi (%)")
        st.pyplot(fig_stack)

        st.info("""
        **Analisis Atribusi:**
        Perhatikan bahwa proporsi setiap persona (warna bar) hampir identik di setiap channel. 
        Ini menunjukkan bahwa **targeting iklan (Ads/Instagram) masih bersifat 'Broad' (umum)**, 
        karena tidak spesifik mendatangkan persona 'Ready-to-Buy' lebih banyak dibandingkan channel organik.
        """)

    with tab3:
        st.subheader("Kesimpulan & Action Plan")

        st.success("### Ringkasan Insight")

        rekomendasi_col1, rekomendasi_col2 = st.columns(2)

        with rekomendasi_col1:
            st.markdown("1. Evaluasi Budget 'Ads'")
            st.write("""
            - **Fakta:** Conversion Rate dari *Paid Ads* (19.9%) ternyata lebih rendah atau setara dengan traffic gratisan dari Google/Direct.
            - **Action:** Pertimbangkan untuk **mengurangi budget Ads** atau **memperbaiki targeting**. Saat ini, Anda membayar untuk kualitas user yang sama dengan yang Anda dapatkan secara gratis.
            """)

        with rekomendasi_col2:
            st.markdown("2. Maksimalkan Organic & Social")
            st.write("""
            - **Fakta:** Google Search adalah penyumbang traffic terbesar. Instagram memiliki volume besar dengan konversi yang sehat.
            - **Action:** Pertahankan SEO agar ranking Google tidak turun. Perkuat konten Instagram karena terbukti mendatangkan user dengan biaya akuisisi (CAC) yang kemungkinan lebih rendah dari Ads.
            """)

        st.markdown("#### 3. Strategi Per-Persona")

        # Menemukan persona spesifik dari data summary
        try:
            researcher_stats = cluster_summary[cluster_summary['Persona'].str.contains('Researcher')]
            if not researcher_stats.empty:
                time_spent = researcher_stats['time_spent'].values[0]
                st.write(
                    f"- **Untuk 'The Deep Researcher':** Mereka menghabiskan waktu rata-rata **{time_spent:.0f} detik**! Berikan mereka konten detail, comparison chart, atau *social proof* (testimoni) untuk meyakinkan mereka agar segera checkout.")
        except:
            pass

else:
    st.warning("Menunggu data dimuat...")