import streamlit as st
import polars as pl
import plotly.express as px
import plotly.graph_objects as go
from difflib import SequenceMatcher

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(page_title="Campaign Analytics", layout="wide", page_icon="📊")

# CSS personalizado
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e1e2e, #2a2a3e);
        border: 1px solid #3a3a5c;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .stAlert { border-radius: 10px; }
    .mapping-header {
        font-size: 13px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DICCIONARIO DE AUTO-DETECCIÓN DE COLUMNAS
# Cubre Meta Ads, Google Ads, TikTok, etc.
# ─────────────────────────────────────────────
COLUMN_ALIASES = {
    "date": [
        "date", "fecha", "day", "día", "periodo", "period", "report_date",
        "date_start", "date_stop", "segment.date", "day_of_week"
    ],
    "campaign": [
        "campaign", "campaña", "campaign_name", "campaign name", "nombre campaña",
        "ad_campaign", "campaign_id", "nombre de campaña", "adset_name",
        "ad group", "grupo de anuncios", "ad_group_name"
    ],
    "platform": [
        "platform", "plataforma", "source", "fuente", "network", "channel",
        "ad_network", "publisher_platform", "placement", "network_type"
    ],
    "impressions": [
        "impressions", "impresiones", "impr", "views", "vistas", "reach",
        "alcance", "impressions_total", "total_impressions", "frequency"
    ],
    "clicks": [
        "clicks", "clics", "click", "link_clicks", "website_clicks",
        "clics_en_enlace", "total_clicks", "link click", "clics totales"
    ],
    "spend": [
        "spend", "gasto", "cost", "costo", "coste", "amount_spent",
        "importe_gastado", "inversión", "inversion", "budget_spent",
        "total_cost", "cost_micros", "spend_usd", "budget"
    ],
    "conversions": [
        "conversions", "conversiones", "conv", "purchases", "compras",
        "leads", "results", "resultados", "actions", "acciones",
        "website_purchases", "complete_payment", "conversion_value",
        "total_conversions", "objetivo"
    ],
    "revenue": [
        "revenue", "ingresos", "income", "value", "valor", "purchase_value",
        "conversion_value", "roas_value", "sales", "ventas", "gmv",
        "website_purchase_roas", "total_value"
    ],
}

# ─────────────────────────────────────────────
# FUNCIONES AUXILIARES
# ─────────────────────────────────────────────

def similarity(a: str, b: str) -> float:
    """Calcula similitud entre dos strings (case-insensitive)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def auto_detect_columns(df_columns: list) -> dict:
    """
    Intenta mapear automáticamente las columnas del archivo
    a las métricas estándar usando similitud de texto.
    Retorna dict: {metric: best_column_match or None}
    """
    detected = {}
    for metric, aliases in COLUMN_ALIASES.items():
        best_col = None
        best_score = 0.0
        for col in df_columns:
            for alias in aliases:
                score = similarity(col, alias)
                if score > best_score and score >= 0.75:
                    best_score = score
                    best_col = col
        detected[metric] = best_col
    return detected

def safe_sum(df: pl.DataFrame, col: str):
    """Suma segura de una columna, retorna 0 si no existe o tiene error."""
    try:
        if col and col in df.columns:
            return df[col].cast(pl.Float64, strict=False).drop_nulls().sum() or 0
        return 0
    except Exception:
        return 0

def format_number(n, prefix="", suffix="", decimals=0):
    """Formatea números grandes con separadores."""
    try:
        if decimals == 0:
            return f"{prefix}{n:,.0f}{suffix}"
        return f"{prefix}{n:,.{decimals}f}{suffix}"
    except Exception:
        return "N/A"

# ─────────────────────────────────────────────
# INTERFAZ PRINCIPAL
# ─────────────────────────────────────────────

st.title("📊 Campaign Analytics Dashboard")
st.markdown("Sube tu reporte de **Meta Ads, Google Ads, TikTok** u otra plataforma — la app detecta las columnas automáticamente.")

# ── CARGA DE ARCHIVO ──
uploaded_file = st.file_uploader(
    "Arrastra tu archivo aquí",
    type=["csv", "xlsx", "xls"],
    help="Formatos soportados: CSV, Excel (.xlsx, .xls)"
)

if not uploaded_file:
    st.info("⬆️ Sube un archivo para comenzar el análisis.")
    st.stop()

# ── LECTURA DEL ARCHIVO ──
try:
    if uploaded_file.name.endswith(".csv"):
        df_raw = pl.read_csv(uploaded_file, infer_schema_length=1000, ignore_errors=True)
    else:
        df_raw = pl.read_excel(uploaded_file)
    st.success(f"✅ Archivo cargado: **{uploaded_file.name}** — {df_raw.shape[0]:,} filas · {df_raw.shape[1]} columnas")
except Exception as e:
    st.error(f"❌ Error al leer el archivo: {e}")
    st.markdown("💡 Asegúrate de tener instalado: `pip install fastexcel openpyxl`")
    st.stop()

# ── PREVIEW ──
with st.expander("👁 Ver datos crudos (primeras 5 filas)"):
    st.dataframe(df_raw.head(5).to_pandas(), use_container_width=True)

# ─────────────────────────────────────────────
# PASO 1: MAPEO DE COLUMNAS
# ─────────────────────────────────────────────
st.divider()
st.subheader("🗂 Mapeo de Columnas")
st.markdown("La app intentó detectar tus columnas automáticamente. **Revisa y corrige** si es necesario.")

available_cols = df_raw.columns
col_options = ["— No disponible —"] + list(available_cols)

detected = auto_detect_columns(available_cols)

# Mostrar mapeo en grilla 3 columnas
metrics_config = {
    "date":        ("📅 Fecha",        "Para el eje temporal de gráficos"),
    "campaign":    ("📣 Campaña",      "Nombre de la campaña o grupo de anuncios"),
    "platform":    ("🌐 Plataforma",   "Red/canal publicitario"),
    "impressions": ("👁 Impresiones",  "Número de veces que se mostró el anuncio"),
    "clicks":      ("🖱 Clicks",       "Clics totales en el anuncio"),
    "spend":       ("💰 Gasto",        "Inversión publicitaria total"),
    "conversions": ("🎯 Conversiones", "Compras, leads u objetivos cumplidos"),
    "revenue":     ("💵 Ingresos",     "Valor generado por las conversiones"),
}

mapping = {}
cols_ui = st.columns(3)
for i, (metric, (label, help_text)) in enumerate(metrics_config.items()):
    with cols_ui[i % 3]:
        auto_val = detected.get(metric)
        default_idx = col_options.index(auto_val) if auto_val in col_options else 0
        selected = st.selectbox(
            label,
            options=col_options,
            index=default_idx,
            help=help_text,
            key=f"map_{metric}"
        )
        mapping[metric] = None if selected == "— No disponible —" else selected

# Feedback de detección automática
detected_count = sum(1 for v in mapping.values() if v)
st.caption(f"✨ Detectadas automáticamente: **{detected_count}/{len(metrics_config)}** columnas")

# ─────────────────────────────────────────────
# VERIFICACIÓN MÍNIMA
# ─────────────────────────────────────────────
required_for_kpi = ["spend", "impressions", "clicks"]
missing_required = [m for m in required_for_kpi if not mapping.get(m)]
if missing_required:
    st.warning(f"⚠️ Para calcular KPIs necesitas mapear: **{', '.join(missing_required)}**. Revisa el mapeo arriba.")

# ─────────────────────────────────────────────
# FILTROS EN SIDEBAR
# ─────────────────────────────────────────────
df = df_raw.clone()

st.sidebar.header("🔍 Filtros")

if mapping["campaign"]:
    campaigns = df[mapping["campaign"]].drop_nulls().unique().to_list()
    campaigns.sort()
    selected_campaigns = st.sidebar.multiselect(
        "Campaña / Ad Group",
        campaigns,
        default=campaigns,
        placeholder="Todas"
    )
    if selected_campaigns:
        df = df.filter(pl.col(mapping["campaign"]).is_in(selected_campaigns))

if mapping["platform"]:
    platforms = df[mapping["platform"]].drop_nulls().unique().to_list()
    platforms.sort()
    selected_platforms = st.sidebar.multiselect(
        "Plataforma / Red",
        platforms,
        default=platforms,
        placeholder="Todas"
    )
    if selected_platforms:
        df = df.filter(pl.col(mapping["platform"]).is_in(selected_platforms))

st.sidebar.caption(f"Mostrando **{df.shape[0]:,}** de **{df_raw.shape[0]:,}** filas")

# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────
st.divider()
st.subheader("📈 KPIs Generales")

total_spend   = safe_sum(df, mapping["spend"])
total_impr    = safe_sum(df, mapping["impressions"])
total_clicks  = safe_sum(df, mapping["clicks"])
total_conv    = safe_sum(df, mapping["conversions"])
total_revenue = safe_sum(df, mapping["revenue"])

ctr  = (total_clicks / total_impr * 100) if total_impr > 0 else 0
cpc  = (total_spend / total_clicks)       if total_clicks > 0 else 0
cpa  = (total_spend / total_conv)         if total_conv > 0 else 0
roas = (total_revenue / total_spend)      if total_spend > 0 else 0

kpi_cols = st.columns(4)
kpi_data = [
    ("💰 Gasto Total",     format_number(total_spend, "$"),    mapping["spend"]),
    ("👁 Impresiones",     format_number(total_impr),           mapping["impressions"]),
    ("🖱 Clicks Totales",  format_number(total_clicks),         mapping["clicks"]),
    ("🎯 Conversiones",    format_number(total_conv),           mapping["conversions"]),
]

for col, (label, value, source_col) in zip(kpi_cols, kpi_data):
    with col:
        if source_col:
            st.metric(label, value)
        else:
            st.metric(label, "Sin datos")

kpi_cols2 = st.columns(4)
kpi_data2 = [
    ("📊 CTR",         f"{ctr:.2f}%",              mapping["clicks"] and mapping["impressions"]),
    ("💲 CPC",         format_number(cpc, "$", decimals=2), mapping["clicks"] and mapping["spend"]),
    ("🎯 CPA",         format_number(cpa, "$", decimals=2), mapping["conversions"] and mapping["spend"]),
    ("🔥 ROAS",        f"{roas:.2f}x",              mapping["revenue"] and mapping["spend"]),
]

for col, (label, value, available) in zip(kpi_cols2, kpi_data2):
    with col:
        if available:
            st.metric(label, value)
        else:
            st.metric(label, "Sin datos")

# ─────────────────────────────────────────────
# VISUALIZACIONES
# ─────────────────────────────────────────────
st.divider()
st.subheader("📉 Visualizaciones")

tab1, tab2, tab3 = st.tabs(["Tendencia Temporal", "Por Campaña", "Distribución"])

# ── TAB 1: TENDENCIA TEMPORAL ──
with tab1:
    if mapping["date"]:
        try:
            df_trend = (
                df.with_columns(pl.col(mapping["date"]).cast(pl.Utf8))
                .group_by(mapping["date"])
                .agg([
                    pl.col(mapping["clicks"]).cast(pl.Float64).sum().alias("Clicks")  if mapping["clicks"] else pl.lit(None).alias("Clicks"),
                    pl.col(mapping["spend"]).cast(pl.Float64).sum().alias("Gasto")    if mapping["spend"] else pl.lit(None).alias("Gasto"),
                    pl.col(mapping["impressions"]).cast(pl.Float64).sum().alias("Impresiones") if mapping["impressions"] else pl.lit(None).alias("Impresiones"),
                ])
                .sort(mapping["date"])
            )

            metric_choice = st.selectbox(
                "Métrica a visualizar",
                [m for m in ["Clicks", "Gasto", "Impresiones"] if m in df_trend.columns]
            )

            fig = px.line(
                df_trend.to_pandas(),
                x=mapping["date"],
                y=metric_choice,
                title=f"Evolución de {metric_choice} en el tiempo",
                markers=True
            )
            fig.update_layout(xaxis_title="Fecha", yaxis_title=metric_choice, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"No se pudo generar el gráfico temporal: {e}")
    else:
        st.info("Mapea la columna **Fecha** para ver la tendencia temporal.")

# ── TAB 2: POR CAMPAÑA ──
with tab2:
    if mapping["campaign"] and mapping["spend"]:
        try:
            agg_exprs = [pl.col(mapping["spend"]).cast(pl.Float64).sum().alias("Gasto")]
            if mapping["clicks"]:
                agg_exprs.append(pl.col(mapping["clicks"]).cast(pl.Float64).sum().alias("Clicks"))
            if mapping["conversions"]:
                agg_exprs.append(pl.col(mapping["conversions"]).cast(pl.Float64).sum().alias("Conversiones"))

            df_camp = (
                df.group_by(mapping["campaign"])
                .agg(agg_exprs)
                .sort("Gasto", descending=True)
                .head(15)
            )

            bar_metric = st.selectbox(
                "Métrica para barras",
                [c for c in ["Gasto", "Clicks", "Conversiones"] if c in df_camp.columns]
            )

            fig2 = px.bar(
                df_camp.to_pandas(),
                x=bar_metric,
                y=mapping["campaign"],
                orientation="h",
                title=f"Top Campañas por {bar_metric}",
                color=bar_metric,
                color_continuous_scale="Blues"
            )
            fig2.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.warning(f"No se pudo generar el gráfico por campaña: {e}")
    else:
        st.info("Mapea las columnas **Campaña** y **Gasto** para ver este gráfico.")

# ── TAB 3: DISTRIBUCIÓN ──
with tab3:
    if mapping["spend"] and mapping["campaign"]:
        try:
            df_pie = (
                df.group_by(mapping["campaign"])
                .agg(pl.col(mapping["spend"]).cast(pl.Float64).sum().alias("Gasto"))
                .sort("Gasto", descending=True)
                .head(10)
            )
            fig3 = px.pie(
                df_pie.to_pandas(),
                names=mapping["campaign"],
                values="Gasto",
                title="Distribución del Gasto por Campaña (Top 10)"
            )
            st.plotly_chart(fig3, use_container_width=True)
        except Exception as e:
            st.warning(f"No se pudo generar el gráfico de distribución: {e}")
    else:
        st.info("Mapea **Campaña** y **Gasto** para ver la distribución.")

# ─────────────────────────────────────────────
# TABLA RESUMEN
# ─────────────────────────────────────────────
st.divider()
st.subheader("📋 Tabla Resumen por Campaña")

if mapping["campaign"]:
    agg_all = []
    col_labels = {}

    for metric, label in [
        ("spend", "Gasto ($)"), ("impressions", "Impresiones"),
        ("clicks", "Clicks"), ("conversions", "Conversiones"), ("revenue", "Ingresos ($)")
    ]:
        if mapping[metric]:
            agg_all.append(pl.col(mapping[metric]).cast(pl.Float64, strict=False).sum().alias(label))
            col_labels[metric] = label

    if agg_all:
        try:
            df_summary = (
                df.group_by(mapping["campaign"])
                .agg(agg_all)
                .sort("Gasto ($)" if "Gasto ($)" in [e.meta.output_name() for e in agg_all] else agg_all[0].meta.output_name(), descending=True)
            )
            st.dataframe(df_summary.to_pandas(), use_container_width=True)
        except Exception:
            st.dataframe(df.select([mapping["campaign"]] + [mapping[m] for m in col_labels if mapping[m]]).to_pandas(), use_container_width=True)
else:
    st.info("Mapea la columna **Campaña** para ver la tabla resumen.")
