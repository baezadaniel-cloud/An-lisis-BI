import streamlit as st
import polars as pl
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Campaign Analytics", layout="wide")

st.title("🚀 Dashboard de Análisis de Campañas")
st.markdown("Sube tus reportes de Meta Ads, Google Ads o TikTok para analizar rendimiento.")

# --- 1. CARGA DE DATOS ---
uploaded_file = st.file_uploader("Sube tu archivo CSV o Excel", type=['csv', 'xlsx'])

if uploaded_file:
    # Detectar tipo y cargar con Polars (Más rápido que Pandas)
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pl.read_csv(uploaded_file)
        else:
            df = pl.read_excel(uploaded_file)
            
        st.success("✅ Archivo cargado correctamente con Polars")
        
        # Mostrar datos crudos (Preview)
        with st.expander("Ver datos crudos"):
            st.dataframe(df.to_pandas()) # Streamlit lee mejor Pandas/Arrow nativo

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.stop()

    # --- 2. SELECTORES (FILTROS) ---
    st.sidebar.header("Filtros")
    
    # Asumimos que tienes columnas 'Campaign', 'Date', 'Platform'
    # Si no existen, el código debería adaptarse o pedir mapeo de columnas
    
    # Ejemplo de filtro dinámico
    if 'Campaign' in df.columns:
        campaigns = df['Campaign'].unique().to_list()
        selected_campaign = st.sidebar.multiselect("Selecciona Campaña", campaigns, default=campaigns)
        
        # Filtrar Dataframe con Polars
        df_filtered = df.filter(pl.col('Campaign').is_in(selected_campaign))
    else:
        df_filtered = df

    # --- 3. CÁLCULO DE KPIs ---
    # Asumimos columnas estándar. En una app real, harías un mapeo de columnas.
    try:
        # Sumarizamos métricas totales
        total_spend = df_filtered['Spend'].sum()
        total_impr = df_filtered['Impressions'].sum()
        total_clicks = df_filtered['Clicks'].sum()
        total_conv = df_filtered['Conversions'].sum()
        
        # Cálculos derivados
        ctr = (total_clicks / total_impr) * 100 if total_impr > 0 else 0
        cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
        cpa = (total_spend / total_conv) if total_conv > 0 else 0

        # Mostrar KPIs en columnas
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Gasto Total", f"${total_spend:,.0f}")
        kpi2.metric("CTR Promedio", f"{ctr:.2f}%")
        kpi3.metric("CPC Promedio", f"${cpc:.2f}")
        kpi4.metric("Conversiones", f"{total_conv}")

    except Exception as e:
        st.warning("No pudimos calcular KPIs. Asegúrate que tu CSV tenga columnas: Spend, Impressions, Clicks, Conversions")

    # --- 4. VISUALIZACIÓN ---
    st.subheader("Tendencia de Rendimiento")
    
    # Gráfico de Líneas con Plotly
    # Plotly necesita Pandas o listas, convertimos solo lo necesario
    if 'Date' in df_filtered.columns:
        # Agrupar por fecha usando Polars
        df_trend = (df_filtered
                    .group_by("Date")
                    .agg([pl.col("Clicks").sum(), pl.col("Spend").sum()])
                    .sort("Date"))
        
        fig = px.line(df_trend.to_pandas(), x='Date', y=['Clicks', 'Spend'], 
                      title="Evolución Diaria: Clicks vs Gasto")
        st.plotly_chart(fig, use_container_width=True)
    
else:
    st.info("Esperando archivo... Por favor sube un dataset para comenzar.")
