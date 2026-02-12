import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="Vial Parking - Dashboard",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URL de la API
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Título principal
st.title("🚦 Vial Parking - Sistema de Gestión de Cartelería")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Filtros
    st.subheader("Filtros")
    estado_filter = st.selectbox(
        "Estado",
        ["Todos", "para_reemplazar", "en_proceso", "reemplazado"],
        index=0
    )
    
    operario_filter = st.text_input("Operario", "")
    
    # Rango de fechas
    fecha_desde = st.date_input("Desde", datetime.now() - timedelta(days=30))
    fecha_hasta = st.date_input("Hasta", datetime.now())
    
    st.markdown("---")
    
    # Información del sistema
    st.subheader("📊 Estado del Sistema")
    try:
        health = requests.get(f"{API_URL}/health").json()
        
        for servicio, estado in health.get("services", {}).items():
            if estado == "ok":
                st.success(f"✅ {servicio.upper()}")
            else:
                st.error(f"❌ {servicio.upper()}")
    except:
        st.error("❌ API no disponible")


# Función para obtener datos
@st.cache_data(ttl=30)
def obtener_carteles():
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
tab1, tab2, tab3, tab4 = st.tabs(["📍 Mapa", "📊 Estadísticas", "📦 Stock", "📋 Registros"])

# TAB 1: MAPA
with tab1:
    st.header("Mapa de Carteles")
    
    carteles = obtener_carteles()
    
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
                <b>Operario:</b> {cartel['operario']}<br>
                <b>Estado:</b> {cartel['estado']}<br>
                <b>Fecha:</b> {cartel['fecha_trabajo'][:10]}<br>
                <b>Dirección:</b> {cartel.get('direccion', 'N/A')}
            </div>
            """
            
            folium.Marker(
                location=[cartel["latitud"], cartel["longitud"]],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=color, icon="info-sign"),
                tooltip=f"{cartel['operario']} - {cartel['estado']}"
            ).add_to(m)
        
        # Mostrar mapa
        st_folium(m, width=None, height=600)
        
        # Leyenda
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("🔴 **Para Reemplazar**")
        with col2:
            st.markdown("🟠 **En Proceso**")
        with col3:
            st.markdown("🟢 **Reemplazado**")
    
    else:
        st.info("No hay carteles registrados con los filtros seleccionados.")


# TAB 2: ESTADÍSTICAS
with tab2:
    st.header("Estadísticas y Métricas")
    
    carteles = obtener_carteles()
    
    if carteles:
        df = pd.DataFrame(carteles)
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total = len(df)
            st.metric("Total de Carteles", total)
        
        with col2:
            para_reemplazar = len(df[df["estado"] == "para_reemplazar"])
            st.metric("Para Reemplazar", para_reemplazar, delta=None)
        
        with col3:
            en_proceso = len(df[df["estado"] == "en_proceso"])
            st.metric("En Proceso", en_proceso)
        
        with col4:
            reemplazados = len(df[df["estado"] == "reemplazado"])
            porcentaje = (reemplazados / total * 100) if total > 0 else 0
            st.metric("Reemplazados", reemplazados, f"{porcentaje:.1f}%")
        
        st.markdown("---")
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Carteles por Estado")
            estados_count = df["estado"].value_counts()
            st.bar_chart(estados_count)
        
        with col2:
            st.subheader("Carteles por Operario")
            operarios_count = df["operario"].value_counts().head(10)
            st.bar_chart(operarios_count)
        
        # Top acciones
        st.subheader("Acciones Más Frecuentes")
        acciones_count = df["accion_vial"].value_counts().head(10)
        st.dataframe(acciones_count, use_container_width=True)
    
    else:
        st.info("No hay datos para mostrar estadísticas.")


# TAB 3: STOCK
with tab3:
    st.header("Gestión de Stock")
    
    # Alertas de stock bajo
    alertas = obtener_alertas_stock()
    if alertas:
        st.error(f"⚠️ **{len(alertas)} alertas de stock bajo**")
        for alerta in alertas:
            with st.expander(f"⚠️ {alerta['tipo_cartel']} - {alerta['cantidad_actual']} unidades"):
                st.warning(alerta['mensaje'])
                st.write(f"**Umbral configurado:** {alerta['threshold']} unidades")
    
    st.markdown("---")
    
    # Tabla de stock
    stock = obtener_stock()
    
    if stock:
        st.subheader("Inventario Actual")
        
        stock_df = pd.DataFrame([
            {"Tipo de Cartel": k, "Cantidad": v, "Estado": "⚠️ Bajo" if v <= 10 else "✅ OK"}
            for k, v in stock.items()
        ]).sort_values("Cantidad")
        
        st.dataframe(stock_df, use_container_width=True, hide_index=True)
        
        # Gráfico de stock
        st.subheader("Niveles de Stock")
        st.bar_chart(stock_df.set_index("Tipo de Cartel")["Cantidad"])
    
    else:
        st.info("No se pudo cargar el stock. Verifica la configuración de Google Sheets.")
    
    # Botón de actualización
    if st.button("🔄 Actualizar Stock"):
        st.cache_data.clear()
        st.rerun()


# TAB 4: REGISTROS
with tab4:
    st.header("Registros Detallados")
    
    carteles = obtener_carteles()
    
    if carteles:
        df = pd.DataFrame(carteles)
        
        # Configurar columnas a mostrar
        columnas_mostrar = [
            "id", "operario", "accion_vial", "estado",
            "direccion", "fecha_trabajo"
        ]
        
        df_mostrar = df[columnas_mostrar].copy()
        df_mostrar["fecha_trabajo"] = pd.to_datetime(df_mostrar["fecha_trabajo"]).dt.strftime("%Y-%m-%d %H:%M")
        
        # Mostrar tabla
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        
        # Detalles de un registro
        st.markdown("---")
        st.subheader("Detalle de Registro")
        
        cartel_id = st.selectbox(
            "Seleccionar ID de cartel",
            options=df["id"].tolist(),
            format_func=lambda x: f"ID {x} - {df[df['id']==x]['operario'].values[0]}"
        )
        
        if cartel_id:
            cartel = df[df["id"] == cartel_id].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**ID:** {cartel['id']}")
                st.write(f"**Operario:** {cartel['operario']}")
                st.write(f"**Acción:** {cartel['accion_vial']}")
                st.write(f"**Estado:** {cartel['estado']}")
                st.write(f"**Fecha:** {cartel['fecha_trabajo']}")
            
            with col2:
                st.write(f"**Latitud:** {cartel['latitud']}")
                st.write(f"**Longitud:** {cartel['longitud']}")
                st.write(f"**Dirección:** {cartel.get('direccion', 'N/A')}")
                st.write(f"**WhatsApp:** {cartel.get('whatsapp_number', 'N/A')}")
                st.write(f"**Notas:** {cartel.get('notas', 'N/A')}")
            
            # Actualizar estado
            st.markdown("---")
            nuevo_estado = st.selectbox(
                "Cambiar estado",
                ["para_reemplazar", "en_proceso", "reemplazado"],
                index=["para_reemplazar", "en_proceso", "reemplazado"].index(cartel["estado"])
            )
            
            if st.button("Actualizar Estado"):
                try:
                    response = requests.put(
                        f"{API_URL}/carteles/{cartel_id}/estado",
                        params={"nuevo_estado": nuevo_estado}
                    )
                    if response.status_code == 200:
                        st.success("✅ Estado actualizado correctamente")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ Error al actualizar el estado")
                except:
                    st.error("❌ No se pudo conectar con la API")
    
    else:
        st.info("No hay registros para mostrar.")

# Footer
st.markdown("---")
st.caption("Vial Parking © 2026 - Sistema de Gestión de Cartelería Vial CABA")
