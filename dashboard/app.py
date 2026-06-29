import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Permitir importar el módulo i18n que vive en esta misma carpeta
sys.path.append(str(Path(__file__).parent))
from i18n import t, language_selector, estado_label

load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title=t("page_title"),
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URL de la API
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Título principal
st.title(t("app_title"))
st.markdown("---")

# Sidebar
with st.sidebar:
    # Selector de idioma (lo más arriba posible)
    language_selector()
    st.markdown("---")

    st.header(t("sb_config"))

    # Filtros
    st.subheader(t("sb_filters"))
    estado_filter = st.selectbox(
        t("lbl_estado"),
        ["Todos", "para_reemplazar", "en_proceso", "reemplazado"],
        index=0,
        format_func=estado_label,
    )

    operario_filter = st.text_input(t("lbl_operario"), "")

    # Rango de fechas
    fecha_desde = st.date_input(t("lbl_desde"), datetime.now() - timedelta(days=30))
    fecha_hasta = st.date_input(t("lbl_hasta"), datetime.now())

    st.markdown("---")

    # Información del sistema
    st.subheader(t("sb_system_status"))
    try:
        health = requests.get(f"{API_URL}/health").json()

        for servicio, estado in health.get("services", {}).items():
            if estado == "ok":
                st.success(f"✅ {servicio.upper()}")
            else:
                st.error(f"❌ {servicio.upper()}")
    except:
        st.error(t("api_unavailable"))


# Función para obtener datos
@st.cache_data(ttl=30)
def obtener_carteles(estado_filter, operario_filter):
    try:
        params = {}
        if estado_filter != "Todos":
            params["estado"] = estado_filter
        if operario_filter:
            params["operario"] = operario_filter

        response = requests.get(f"{API_URL}/carteles", params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []


@st.cache_data(ttl=60)
def obtener_stock():
    try:
        response = requests.get(f"{API_URL}/stock")
        if response.status_code == 200:
            return response.json().get("stock", {})
        return {}
    except:
        return {}


@st.cache_data(ttl=60)
def obtener_alertas_stock():
    try:
        response = requests.get(f"{API_URL}/stock/alertas")
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []


# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs([
    t("tab_map"), t("tab_stats"), t("tab_stock"), t("tab_records")
])

# TAB 1: MAPA
with tab1:
    st.header(t("map_header"))

    carteles = obtener_carteles(estado_filter, operario_filter)

    if carteles:
        # Crear mapa centrado en CABA
        m = folium.Map(
            location=[-34.6037, -58.3816],
            zoom_start=12,
            tiles="OpenStreetMap"
        )

        # Colores según estado
        colores = {
            "para_reemplazar": "red",
            "en_proceso": "orange",
            "reemplazado": "green"
        }

        # Agregar marcadores
        for cartel in carteles:
            color = colores.get(cartel["estado"], "gray")

            popup_html = f"""
            <div style="font-family: Arial; min-width: 200px;">
                <h4 style="margin: 0;">{cartel['accion_vial']}</h4>
                <hr style="margin: 5px 0;">
                <b>{t('popup_operario')}:</b> {cartel['operario']}<br>
                <b>{t('popup_estado')}:</b> {estado_label(cartel['estado'])}<br>
                <b>{t('popup_fecha')}:</b> {cartel['fecha_trabajo'][:10]}<br>
                <b>{t('popup_direccion')}:</b> {cartel.get('direccion', 'N/A')}
            </div>
            """

            folium.Marker(
                location=[cartel["latitud"], cartel["longitud"]],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=color, icon="info-sign"),
                tooltip=f"{cartel['operario']} - {estado_label(cartel['estado'])}"
            ).add_to(m)

        # Mostrar mapa
        st_folium(m, width=None, height=600)

        # Leyenda
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(t("legend_para_reemplazar"))
        with col2:
            st.markdown(t("legend_en_proceso"))
        with col3:
            st.markdown(t("legend_reemplazado"))

    else:
        st.info(t("no_carteles_filtros"))


# TAB 2: ESTADÍSTICAS
with tab2:
    st.header(t("stats_header"))

    carteles = obtener_carteles(estado_filter, operario_filter)

    if carteles:
        df = pd.DataFrame(carteles)

        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total = len(df)
            st.metric(t("metric_total"), total)

        with col2:
            para_reemplazar = len(df[df["estado"] == "para_reemplazar"])
            st.metric(t("metric_para_reemplazar"), para_reemplazar, delta=None)

        with col3:
            en_proceso = len(df[df["estado"] == "en_proceso"])
            st.metric(t("metric_en_proceso"), en_proceso)

        with col4:
            reemplazados = len(df[df["estado"] == "reemplazado"])
            porcentaje = (reemplazados / total * 100) if total > 0 else 0
            st.metric(t("metric_reemplazados"), reemplazados, f"{porcentaje:.1f}%")

        st.markdown("---")

        # Gráficos
        col1, col2 = st.columns(2)

        with col1:
            st.subheader(t("chart_por_estado"))
            estados_count = df["estado"].value_counts()
            st.bar_chart(estados_count)

        with col2:
            st.subheader(t("chart_por_operario"))
            operarios_count = df["operario"].value_counts().head(10)
            st.bar_chart(operarios_count)

        # Top acciones
        st.subheader(t("chart_acciones"))
        acciones_count = df["accion_vial"].value_counts().head(10)
        st.dataframe(acciones_count, use_container_width=True)

    else:
        st.info(t("no_datos_stats"))


# TAB 3: STOCK
with tab3:
    st.header(t("stock_header"))

    # Alertas de stock bajo
    alertas = obtener_alertas_stock()
    if alertas:
        st.error(t("stock_alertas", n=len(alertas)))
        for alerta in alertas:
            with st.expander(t("stock_expander", tipo=alerta['tipo_cartel'], cant=alerta['cantidad_actual'])):
                st.warning(alerta['mensaje'])
                st.write(t("stock_umbral", n=alerta['threshold']))

    st.markdown("---")

    # Tabla de stock
    stock = obtener_stock()

    if stock:
        st.subheader(t("stock_inventario"))

        col_tipo = t("stock_col_tipo")
        col_cant = t("stock_col_cantidad")
        col_est = t("stock_col_estado")

        stock_df = pd.DataFrame([
            {col_tipo: k, col_cant: v, col_est: t("stock_bajo") if v <= 10 else t("stock_ok")}
            for k, v in stock.items()
        ]).sort_values(col_cant)

        st.dataframe(stock_df, use_container_width=True, hide_index=True)

        # Gráfico de stock
        st.subheader(t("stock_niveles"))
        st.bar_chart(stock_df.set_index(col_tipo)[col_cant])

    else:
        st.info(t("stock_error_carga"))

    # Botón de actualización
    if st.button(t("btn_update_stock")):
        st.cache_data.clear()
        st.rerun()


# TAB 4: REGISTROS
with tab4:
    st.header(t("records_header"))

    carteles = obtener_carteles(estado_filter, operario_filter)

    if carteles:
        df = pd.DataFrame(carteles)

        # Configurar columnas a mostrar
        columnas_mostrar = [
            "id", "operario", "accion_vial", "estado",
            "direccion", "fecha_trabajo"
        ]

        df_mostrar = df[columnas_mostrar].copy()
        df_mostrar["fecha_trabajo"] = pd.to_datetime(df_mostrar["fecha_trabajo"]).dt.strftime("%Y-%m-%d %H:%M")
        df_mostrar["estado"] = df_mostrar["estado"].apply(estado_label)
        df_mostrar = df_mostrar.rename(columns={
            "id": t("col_id"),
            "operario": t("col_operario"),
            "accion_vial": t("col_accion"),
            "estado": t("col_estado"),
            "direccion": t("col_direccion"),
            "fecha_trabajo": t("col_fecha"),
        })

        # Mostrar tabla
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

        # Detalles de un registro
        st.markdown("---")
        st.subheader(t("record_detail"))

        cartel_id = st.selectbox(
            t("select_cartel_id"),
            options=df["id"].tolist(),
            format_func=lambda x: t("record_fmt_id", x=x, op=df[df['id'] == x]['operario'].values[0])
        )

        if cartel_id:
            cartel = df[df["id"] == cartel_id].iloc[0]

            col1, col2 = st.columns(2)

            with col1:
                st.write(f"{t('fld_id')} {cartel['id']}")
                st.write(f"{t('fld_operario')} {cartel['operario']}")
                st.write(f"{t('fld_accion')} {cartel['accion_vial']}")
                st.write(f"{t('fld_estado')} {estado_label(cartel['estado'])}")
                st.write(f"{t('fld_fecha')} {cartel['fecha_trabajo']}")

            with col2:
                st.write(f"{t('fld_latitud')} {cartel['latitud']}")
                st.write(f"{t('fld_longitud')} {cartel['longitud']}")
                st.write(f"{t('fld_direccion')} {cartel.get('direccion', 'N/A')}")
                st.write(f"{t('fld_whatsapp')} {cartel.get('whatsapp_number', 'N/A')}")
                st.write(f"{t('fld_notas')} {cartel.get('notas', 'N/A')}")

            # Actualizar estado
            st.markdown("---")
            nuevo_estado = st.selectbox(
                t("select_cambiar_estado"),
                ["para_reemplazar", "en_proceso", "reemplazado"],
                index=["para_reemplazar", "en_proceso", "reemplazado"].index(cartel["estado"]),
                format_func=estado_label,
            )

            if st.button(t("btn_update_estado")):
                try:
                    response = requests.put(
                        f"{API_URL}/carteles/{cartel_id}/estado",
                        params={"nuevo_estado": nuevo_estado}
                    )
                    if response.status_code == 200:
                        st.success(t("estado_actualizado"))
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(t("error_actualizar_estado"))
                except:
                    st.error(t("error_conexion_api"))

    else:
        st.info(t("no_registros"))

# Footer
st.markdown("---")
st.caption(t("footer"))
