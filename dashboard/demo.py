import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path

# Agregar el directorio padre al path para importar los servicios
sys.path.append(str(Path(__file__).parent.parent))

from services.google_sheets import GoogleSheetsService

# Configuración de la página
st.set_page_config(
    page_title="Vial Parking - Demo Dashboard",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Logo
try:
    logo_path = os.path.join(Path(__file__).parent.parent, "data", "Logo original - Fondo negro - 1057 x 511 px.png")
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path)
    else:
        # Intentar con el otro logo
        logo_path = os.path.join(Path(__file__).parent.parent, "data", "Logo original - 1.600x772 px.png")
        if os.path.exists(logo_path):
            st.sidebar.image(logo_path)
except Exception as e:
    st.sidebar.error(f"Logo no encontrado: {e}")

# CSS personalizado
st.markdown("""
<style>
    .whatsapp-msg {
        background-color: #DCF8C6;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
        max-width: 70%;
        color: #000000 !important;
        border: 1px solid #a8e6a1;
    }
    .whatsapp-msg-received {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
        max-width: 70%;
        color: #000000 !important;
        border: 1px solid #e0e0e0;
    }
    .whatsapp-msg small, .whatsapp-msg-received small {
        color: #666666 !important;
        font-weight: bold;
    }
    .whatsapp-msg p, .whatsapp-msg-received p {
        color: #000000 !important;
        margin: 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .status-badge {
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        display: inline-block;
        margin: 5px 0;
    }
    .status-realizado {
        background-color: #d4edda;
        color: #155724;
    }
    .status-proceso {
        background-color: #fff3cd;
        color: #856404;
    }
    .status-espera {
        background-color: #f8d7da;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar servicios
@st.cache_resource
def init_services():
    """Inicializa el servicio de Google Sheets"""
    try:
        sheets_service = GoogleSheetsService()
        return sheets_service
    except Exception as e:
        st.sidebar.error(f"Error al inicializar Google Sheets: {str(e)}")
        return None

sheets_service = init_services()

# Título principal
st.title("🚦 Vial Parking - Gestión ECOGAS")
st.markdown("### Sistema de gestión de cartelería de gasoductos al servicio de ECOGAS")
st.markdown("**Gestión Integral de Señalización de Gasoductos y Ramales**")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Panel de Control")
    
    # Modo de vista
    modo = st.radio(
        "Modo de Vista",
        ["📊 Dashboard", "💬 WhatsApp Demo", "📦 Gestión Stock", "👷 Empleados", "📋 Órdenes", "🗺️ Zonas y Ramales"],
        index=0
    )
    
    st.markdown("---")
    
    # Información
    st.info("🔹 **Demo Mode**\nDatos en tiempo real desde Google Sheets")
    
    # Estado de servicios
    st.subheader("📡 Estado")
    if sheets_service:
        st.success("✅ Google Sheets conectado")
    else:
        st.error("❌ Google Sheets no disponible")


# ===== MODO DASHBOARD =====
if modo == "📊 Dashboard":
    st.header("Dashboard Principal - ECOGAS")
    
    # Usar caché para reducir llamadas a Google Sheets
    @st.cache_data(ttl=300)  # 5 minutos de caché
    def get_carteles_cached():
        if sheets_service:
            try:
                return sheets_service.obtener_carteles_ecogas()
            except:
                return []
        return []
    
    @st.cache_data(ttl=300)
    def get_empleados_cached():
        if sheets_service:
            try:
                return sheets_service.obtener_empleados()
            except:
                return []
        return []
    
    @st.cache_data(ttl=300)
    def get_stock_cached():
        if sheets_service:
            try:
                return sheets_service.obtener_stock()
            except:
                return {}
        return {}
    
    # Métricas principales de carteles ECOGAS
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        try:
            carteles = get_carteles_cached()
            st.metric("Total Carteles", len(carteles), delta="ECOGAS")
        except:
            st.metric("Total Carteles", 0)
    
    with col2:
        try:
            carteles = get_carteles_cached()
            carteles_con_coords = [c for c in carteles if c.get('latitud') and c.get('longitud')]
            st.metric("Georeferenciados", len(carteles_con_coords), delta=f"{len(carteles_con_coords)/len(carteles)*100:.0f}%" if carteles else "0%")
        except:
            st.metric("Georeferenciados", 0)
    
    with col3:
        try:
            carteles = get_carteles_cached()
            ramales = set([' '.join(c.get('gasoducto_ramal', '').split()) for c in carteles if c.get('gasoducto_ramal')])
            st.metric("Ramales", len(ramales))
        except:
            st.metric("Ramales", 0)
    
    with col4:
        try:
            carteles = get_carteles_cached()
            zonas = set([c.get('zona', 'Sin zona') for c in carteles if c.get('zona')])
            st.metric("Zonas Operativas", len(zonas))
        except:
            st.metric("Zonas Operativas", 0)
    
    st.markdown("---")
    
    # Resumen por tipo de cartel
    try:
        carteles = get_carteles_cached()
        if carteles:
            col_tipo1, col_tipo2 = st.columns(2)
            
            with col_tipo1:
                st.markdown("### 📊 Distribución por Tipo")
                tipos_count = {}
                for cartel in carteles:
                    tipo = cartel.get('tipo_cartel', 'Sin clasificar')
                    tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
                
                df_tipos = pd.DataFrame([
                    {"Tipo": k, "Cantidad": v, "Porcentaje": f"{v/len(carteles)*100:.1f}%"}
                    for k, v in sorted(tipos_count.items(), key=lambda x: x[1], reverse=True)
                ])
                st.dataframe(df_tipos, hide_index=True)
            
            with col_tipo2:
                st.markdown("### 🗺️ Distribución por Zona")
                zonas_count = {}
                for cartel in carteles:
                    zona = cartel.get('zona', 'Sin zona')
                    if not zona or zona == '':
                        zona = 'Sin zona'
                    zonas_count[zona] = zonas_count.get(zona, 0) + 1
                
                df_zonas = pd.DataFrame([
                    {"Zona": k, "Cantidad": v}
                    for k, v in sorted(zonas_count.items(), key=lambda x: x[1], reverse=True)[:10]
                ])
                st.dataframe(df_zonas, hide_index=True)
    except:
        pass
    
    st.markdown("---")
    
    # Mapa de carteles ECOGAS
    st.subheader("📍 Mapa de Carteles - Ramales ECOGAS")
    st.markdown("*Visualización de carteles de señalización en ramales de gasoductos*")
    
    # Filtros del mapa
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    with col_filtro1:
        # Obtener tipos de cartel únicos
        try:
            carteles_temp = get_carteles_cached()
            tipos_cartel = sorted(list(set([c.get('tipo_cartel', 'Cartel') for c in carteles_temp if c.get('tipo_cartel')])))
            tipo_filtro = st.multiselect(
                "Filtrar por tipo de cartel",
                options=tipos_cartel,
                default=[]
            )
        except:
            tipo_filtro = []
    
    with col_filtro2:
        try:
            carteles_temp = get_carteles_cached()
            # Normalizar pero preservar estructura (solo quitar espacios múltiples y saltos de línea)
            ramales = sorted(list(set([' '.join(c.get('gasoducto_ramal', '').split()) for c in carteles_temp if c.get('gasoducto_ramal')])))
            ramal_filtro = st.selectbox("Filtrar por ramal", ["Todos"] + ramales, help=f"Total: {len(ramales)} ramales")
        except:
            ramal_filtro = "Todos"
    
    with col_filtro3:
        busqueda_ubicacion = st.text_input("Buscar ubicación")
    
    try:
        carteles = get_carteles_cached()
        
        # Aplicar filtros
        carteles_filtrados = []
        for cartel in carteles:
            # Solo carteles con coordenadas
            if not cartel.get('latitud') or not cartel.get('longitud'):
                continue
            
            # Filtro por tipo
            if tipo_filtro and cartel.get('tipo_cartel') not in tipo_filtro:
                continue
            
            # Filtro por ramal
            if ramal_filtro != "Todos":
                ramal_norm = ' '.join(cartel.get('gasoducto_ramal', '').split())
                if ramal_norm != ramal_filtro:
                    continue
            
            # Filtro por ubicación
            if busqueda_ubicacion:
                ubicacion = cartel.get('ubicacion', '')
                if busqueda_ubicacion.lower() not in ubicacion.lower():
                    continue
            
            carteles_filtrados.append(cartel)
        
        if carteles_filtrados:
            # Calcular centro del mapa basado en carteles filtrados
            lats = [c['latitud'] for c in carteles_filtrados if c.get('latitud')]
            lons = [c['longitud'] for c in carteles_filtrados if c.get('longitud')]
            
            if lats and lons:
                centro_lat = sum(lats) / len(lats)
                centro_lon = sum(lons) / len(lons)
                # Ajustar zoom según dispersión de puntos
                lat_range = max(lats) - min(lats)
                lon_range = max(lons) - min(lons)
                max_range = max(lat_range, lon_range)
                
                # Calcular zoom apropiado
                if max_range > 20:
                    zoom = 5
                elif max_range > 10:
                    zoom = 6
                elif max_range > 5:
                    zoom = 7
                elif max_range > 2:
                    zoom = 8
                elif max_range > 1:
                    zoom = 9
                else:
                    zoom = 10
            else:
                centro_lat, centro_lon, zoom = -38.4161, -63.6167, 5
            
            # Crear mapa centrado en los datos
            m = folium.Map(
                location=[centro_lat, centro_lon],
                zoom_start=zoom,
                tiles="OpenStreetMap"
            )
            
            # Configuración de colores según estado de trabajo
            colores_estado = {
                'realizado': 'green',
                'en_proceso': 'red',
                'pendiente': 'orange',
                'revisado': 'blue',
                'N/A': 'gray',
                '': 'gray'
            }
            
            # Agregar marcadores para cada cartel
            for cartel in carteles_filtrados:
                lat = cartel.get('latitud')
                lon = cartel.get('longitud')
                
                if lat and lon:
                    tipo = cartel.get('tipo_cartel', 'Cartel')
                    numero = cartel.get('numero', 'N/A')
                    numero_str = str(numero)
                    ramal = cartel.get('gasoducto_ramal', 'N/A')
                    ubicacion = cartel.get('ubicacion', 'Sin ubicación')
                    observaciones = cartel.get('observaciones', 'Sin observaciones')
                    zona = cartel.get('zona', 'N/A')
                    estado_planilla = cartel.get('estado', 'N/A')
                    
                    # Asignar estado y color según número para ejemplos
                    # Items 1, 2, 3 en proceso (rojo)
                    if numero_str in ['1', '2', '3']:
                        estado_asignado = 'en_proceso'
                        color = 'red'
                    # Item 4 realizado (verde)
                    elif numero_str == '4':
                        estado_asignado = 'realizado'
                        color = 'green'
                    # Resto según estado de la planilla
                    else:
                        estado_lower = str(estado_planilla).lower().strip()
                        if 'realiz' in estado_lower or 'complet' in estado_lower:
                            estado_asignado = 'realizado'
                            color = colores_estado['realizado']
                        elif 'proces' in estado_lower:
                            estado_asignado = 'en_proceso'
                            color = colores_estado['en_proceso']
                        elif 'revis' in estado_lower:
                            estado_asignado = 'revisado'
                            color = colores_estado['revisado']
                        elif 'pend' in estado_lower:
                            estado_asignado = 'pendiente'
                            color = colores_estado['pendiente']
                        else:
                            estado_asignado = 'pendiente'
                            color = colores_estado.get('pendiente', 'gray')
                    
                    # Crear texto del estado para mostrar
                    estado_texto = '🔴 En Proceso' if estado_asignado == 'en_proceso' else '✅ Realizado' if estado_asignado == 'realizado' else '🔵 Revisado' if estado_asignado == 'revisado' else '🟠 Pendiente' if estado_asignado == 'pendiente' else estado_planilla
                    
                    popup_html = f"""
                    <div style="font-family: Arial; width: 280px; padding: 10px;">
                        <h4 style="margin: 0 0 10px 0; color: #333; border-bottom: 2px solid {color};">
                            🚧 Cartel #{numero}
                        </h4>
                        <p style="margin: 5px 0;">
                            <b>Estado:</b> 
                            <span style="color: {color}; font-weight: bold;">
                                {estado_texto}
                            </span>
                        </p>
                        <p style="margin: 5px 0;"><b>📝 Tipo:</b> {tipo}</p>
                        <p style="margin: 5px 0;"><b>🛣️ Ramal:</b> {ramal}</p>
                        <p style="margin: 5px 0;"><b>📍 Ubicación:</b> {ubicacion}</p>
                        <p style="margin: 5px 0;"><b>🏢 Zona:</b> {zona}</p>
                        <p style="margin: 5px 0;"><b>💬 Obs:</b> {observaciones[:50]}{'...' if len(observaciones) > 50 else ''}</p>
                    </div>
                    """
                    
                    # Agregar marcador al mapa
                    folium.Marker(
                        location=[float(lat), float(lon)],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"#{numero} - {ramal} - {estado_texto}",
                        icon=folium.Icon(
                            color=color,
                            icon='info-sign'
                        )
                    ).add_to(m)
                    
                    # Agregar círculo para mejor visualización
                    folium.CircleMarker(
                        location=[float(lat), float(lon)],
                        radius=6,
                        color=color,
                        fill=True,
                        fillColor=color,
                        fillOpacity=0.4,
                        weight=2
                    ).add_to(m)
            
            # Mostrar el mapa
            st_folium(m, width=1400, height=500)
            
            # Mostrar resumen
            st.info(f"📍 Mostrando {len(carteles_filtrados)} carteles de {len(carteles)} totales")
            
            # Leyenda de estados de trabajo
            st.markdown("### 📋 Leyenda de Estados de Trabajo")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown("🔴 **En Proceso** (Ej: Items 1-3)")
            with col2:
                st.markdown("✅ **Realizado** (Ej: Item 4)")
            with col3:
                st.markdown("🟠 **Pendiente**")
            with col4:
                st.markdown("🔵 **Revisado**")
            
        else:
            st.warning("⚠️ No hay carteles que coincidan con los filtros seleccionados")
    except Exception as e:
        st.error(f"❌ Error al cargar el mapa: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    # Stock actual
    st.subheader("📦 Stock Actual")
    try:
        stock = get_stock_cached()
        if stock:
            stock_df = pd.DataFrame([
                {"Tipo": k, "Cantidad": v, "Estado": "⚠️ Bajo" if v <= 10 else "✅ OK"}
                for k, v in stock.items()
            ]).sort_values("Cantidad")
            
            st.dataframe(stock_df, hide_index=True)
            
            # Gráfico
            st.bar_chart(stock_df.set_index("Tipo")["Cantidad"])
        else:
            st.info("No hay datos de stock disponibles")
    except Exception as e:
        st.info(f"No se pudo cargar el stock: {e}")


# ===== MODO WHATSAPP DEMO =====
elif modo == "💬 WhatsApp Demo":
    st.header("💬 Integración WhatsApp + Twilio")
    
    st.info("🔹 **Demo Interactiva**: Simula ser un operario y recibe respuestas del bot ECOGAS")
    
    tab1, tab2 = st.tabs(["📱 Simulación Interactiva", "📊 Registro de Trabajos"])
    
    # Tab 1: Simulación interactiva
    with tab1:
        st.subheader("💬 Conversación Operario - Bot ECOGAS")
        
        # Estilo de chat con texto visible
        st.markdown("""
        <style>
        .chat-container {
            max-width: 800px;
            margin: 0 auto;
        }
        .message-operario {
            background: #DCF8C6;
            border-radius: 10px;
            padding: 12px 15px;
            margin: 10px 50px 10px 10px;
            text-align: left;
            color: #000000;
        }
        .message-bot {
            background: #E8E8E8;
            border-radius: 10px;
            padding: 12px 15px;
            margin: 10px 10px 10px 50px;
            text-align: left;
            color: #000000;
        }
        .timestamp {
            font-size: 11px;
            color: #666;
            margin-top: 5px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Inicializar estado de la conversación
        if 'paso_whatsapp' not in st.session_state:
            st.session_state.paso_whatsapp = 0
            st.session_state.foto_subida = None
            st.session_state.coordenadas = None
            st.session_state.historial_chat = []
        
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        
        # Mostrar historial de chat
        for msg in st.session_state.historial_chat:
            st.markdown(msg, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Paso 1: Subir foto
        if st.session_state.paso_whatsapp == 0:
            st.markdown("### 📸 Paso 1: Enviar Foto del Cartel")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                uploaded_file = st.file_uploader("Sube una foto del cartel", type=['jpg', 'jpeg', 'png'])
                
                if uploaded_file is not None:
                    st.image(uploaded_file, caption="Foto del cartel", use_container_width=True)
                    
                    if st.button("📤 Enviar Foto al Bot", type="primary"):
                        st.session_state.foto_subida = uploaded_file.name
                        
                        # Agregar mensaje del operario
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        
                        st.session_state.historial_chat.append(f"""
                        <div class='message-operario'>
                            <strong style='color: #000;'>👷 Operario</strong><br/>
                            <em style='color: #000;'>📸 [Imagen adjunta: {uploaded_file.name}]</em><br/>
                            <div class='timestamp'>Hoy {timestamp}</div>
                        </div>
                        """)
                        
                        # Respuesta del bot
                        import time
                        time.sleep(0.5)
                        timestamp2 = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        
                        st.session_state.historial_chat.append(f"""
                        <div class='message-bot'>
                            <strong style='color: #000;'>🤖 Bot ECOGAS</strong><br/>
                            <span style='color: #000;'>📸 Imagen recibida. Ahora comparte tu ubicación GPS para identificar el cartel.</span>
                            <div class='timestamp'>Hoy {timestamp2}</div>
                        </div>
                        """)
                        
                        st.session_state.paso_whatsapp = 1
                        st.rerun()
            
            with col2:
                st.info("💡 **Tip**: Puedes usar cualquier foto o seleccionar la imagen del ejemplo desde la carpeta data/")
        
        # Paso 2: Enviar coordenadas
        elif st.session_state.paso_whatsapp == 1:
            st.markdown("### 📍 Paso 2: Enviar Ubicación GPS")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                coordenadas_input = st.text_input(
                    "Ingresa las coordenadas GPS",
                    placeholder="-33.16225, -64.38010",
                    help="Formato: latitud, longitud"
                )
                
                if st.button("📤 Enviar Ubicación", type="primary"):
                    if coordenadas_input:
                        st.session_state.coordenadas = coordenadas_input
                        
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        
                        # Mensaje del operario con coordenadas
                        st.session_state.historial_chat.append(f"""
                        <div class='message-operario'>
                            <strong style='color: #000;'>👷 Operario</strong><br/>
                            <span style='color: #000;'>📍 {coordenadas_input}</span>
                            <div class='timestamp'>Hoy {timestamp}</div>
                        </div>
                        """)
                        
                        # Bot procesando
                        import time
                        time.sleep(0.3)
                        timestamp2 = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        
                        st.session_state.historial_chat.append(f"""
                        <div class='message-bot'>
                            <strong style='color: #000;'>🤖 Bot ECOGAS</strong><br/>
                            <span style='color: #000;'>📝 Solicitud recibida, {coordenadas_input.split(',')[0]}.<br/><br/>
                            ⏳ Identificando el cartel más cercano...<br/><br/>
                            Te responderé en unos momentos.</span>
                            <div class='timestamp'>Hoy {timestamp2}</div>
                        </div>
                        """)
                        
                        st.session_state.paso_whatsapp = 2
                        st.rerun()
                    else:
                        st.error("Por favor ingresa las coordenadas")
            
            with col2:
                st.info("💡 **Ejemplos**:\n- -33.16225, -64.38010\n- -33.16254, -64.38082")
        
        # Paso 3: Respuesta final del bot
        elif st.session_state.paso_whatsapp == 2:
            # Buscar cartel más cercano
            try:
                carteles = sheets_service.obtener_carteles_ecogas()
                coords = st.session_state.coordenadas.split(',')
                lat_operario = float(coords[0].strip())
                lon_operario = float(coords[1].strip())
                
                # Encontrar cartel más cercano
                cartel_cercano = None
                distancia_min = float('inf')
                
                for cartel in carteles:
                    if cartel.get('latitud') and cartel.get('longitud'):
                        lat_c = cartel['latitud']
                        lon_c = cartel['longitud']
                        distancia = ((lat_c - lat_operario)**2 + (lon_c - lon_operario)**2)**0.5
                        if distancia < distancia_min:
                            distancia_min = distancia
                            cartel_cercano = cartel
                
                if cartel_cercano:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    
                    numero = cartel_cercano.get('numero', 'N/A')
                    tipo = cartel_cercano.get('tipo_cartel', 'N/A')
                    ramal = cartel_cercano.get('gasoducto_ramal', 'N/A')
                    distancia_km = round(distancia_min * 111, 1)  # Aproximación a km
                    
                    st.session_state.historial_chat.append(f"""
                    <div class='message-bot'>
                        <strong style='color: #000;'>🤖 Bot ECOGAS</strong><br/>
                        <span style='color: #000;'>📍 <strong>CARTEL IDENTIFICADO</strong><br/><br/>
                        📋 <strong>Número:</strong> {numero}<br/>
                        📏 <strong>Distancia:</strong> {distancia_km} km<br/>
                        🏷️ <strong>Tipo:</strong> {tipo}<br/>
                        🔧 <strong>Acción a realizar:</strong> Instalación completa.<br/>
                        🚰 <strong>Gasoducto:</strong> {ramal}<br/><br/>
                        📸 Imagen almacenada en Drive<br/><br/>
                        ✅ Procede con la acción indicada.</span>
                        <div class='timestamp'>Hoy {timestamp}</div>
                    </div>
                    """)
                else:
                    st.session_state.historial_chat.append(f"""
                    <div class='message-bot'>
                        <strong style='color: #000;'>🤖 Bot ECOGAS</strong><br/>
                        <span style='color: #000;'>❌ No se encontró ningún cartel cercano a las coordenadas proporcionadas.</span>
                        <div class='timestamp'>Hoy {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</div>
                    </div>
                    """)
            except Exception as e:
                st.error(f"Error al procesar: {e}")
            
            st.session_state.paso_whatsapp = 3
            st.rerun()
        
        # Paso 4: Conversación completada
        else:
            st.success("✅ Conversación completada")
            
            if st.button("🔄 Iniciar Nueva Conversación"):
                st.session_state.paso_whatsapp = 0
                st.session_state.foto_subida = None
                st.session_state.coordenadas = None
                st.session_state.historial_chat = []
                st.rerun()
        
        # Explicación técnica
        st.markdown("---")
        st.markdown("### 🔧 Proceso Técnico")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **1️⃣ Recepción de Imagen**
            - Twilio recibe mensaje WhatsApp
            - Descarga imagen del cartel
            - Extrae metadatos EXIF (si disponibles)
            
            **2️⃣ Análisis con IA (Gemini)**
            - Identifica tipo de cartel
            - Evalúa estado (deterioro, visibilidad)
            - Determina acción necesaria
            """)
        
        with col2:
            st.markdown("""
            **3️⃣ Geolocalización**
            - Procesa coordenadas GPS
            - Busca cartel más cercano en planilla
            - Calcula distancia euclidiana
            
            **4️⃣ Registro Automático**
            - Actualiza estado en Google Sheets
            - Sube imagen a Google Drive
            - Genera enlace de carpeta del item
            """)
    
    # Tab 2: Registro de trabajos
    with tab2:
        st.subheader("📊 Trabajos Registrados vía WhatsApp")
        
        # Datos de ejemplo basados en la conversación
        trabajos_whatsapp = pd.DataFrame([
            {
                "Fecha": "15/01/2026 14:14",
                "Operario": "María González",
                "Cartel": "#2",
                "Tipo": "Cartel Tipo D",
                "Acción": "Instalación completa",
                "Ramal": "Ramal Rio Cuarto",
                "Ubicación": "-33.16225, -64.38010",
                "Distancia": "0.0 km",
                "Estado": "✅ Registrado",
                "Imagen": "Drive ✓"
            },
            {
                "Fecha": "10/01/2026 10:30",
                "Operario": "Juan Pérez",
                "Cartel": "#4",
                "Tipo": "Cartel Tipo D",
                "Acción": "Instalación completa",
                "Ramal": "Ramal Rio Cuarto",
                "Ubicación": "-33.16254, -64.38082",
                "Distancia": "0.0 km",
                "Estado": "✅ Completado",
                "Imagen": "Drive ✓"
            },
            {
                "Fecha": "10/01/2026 15:00",
                "Operario": "Carlos Rodríguez",
                "Cartel": "#3",
                "Tipo": "Cartel Tipo E",
                "Acción": "Instalación completa",
                "Ramal": "Ramales Rio Cuarto",
                "Ubicación": "-33.16198, -64.38045",
                "Distancia": "0.0 km",
                "Estado": "🔴 En Proceso",
                "Imagen": "Drive ✓"
            }
        ])
        
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Registros", len(trabajos_whatsapp))
        with col2:
            st.metric("Completados", len(trabajos_whatsapp[trabajos_whatsapp["Estado"].str.contains("Completado")]))
        with col3:
            st.metric("En Proceso", len(trabajos_whatsapp[trabajos_whatsapp["Estado"].str.contains("Proceso")]))
        with col4:
            st.metric("Precisión GPS", "100%")
        
        st.markdown("---")
        
        # Tabla de trabajos
        st.dataframe(trabajos_whatsapp, hide_index=True, use_container_width=True)
        
        # Información adicional
        st.markdown("---")
        st.markdown("### 🔗 Integraciones Activas")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **📱 Twilio WhatsApp**
            - Sandbox activo
            - Webhook configurado
            - Número: +1 (415) 523-8886
            """)
        
        with col2:
            st.markdown("""
            **🤖 Gemini AI**
            - Modelo: gemini-1.5-pro
            - Análisis de imágenes
            - Confianza: >90%
            """)
        
        with col3:
            st.markdown("""
            **📊 Google Services**
            - Sheets API activa
            - Drive almacenamiento
            - Actualización en tiempo real
            """)

# ===== MODO GESTIÓN STOCK =====
elif modo == "📦 Gestión Stock":
    st.header("📦 Gestión de Stock")
    
    if sheets_service:
        tab1, tab2, tab3 = st.tabs(["📊 Stock Actual", "📥 Registrar Movimiento", "📈 Historial"])
        
        # Tab 1: Stock actual
        with tab1:
            st.subheader("Inventario Actual")
            
            # Mostrar ejemplos de tipos de carteles con imágenes reales
            st.markdown("### 🖼️ Tipos de Carteles ECOGAS")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.image("data/Cañeria.png", use_container_width=True)
                st.markdown("<h4 style='text-align: center;'>Cañería de Gas</h4>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; font-size: 12px; color: #666;'>Cartel indicador de cañería individual en las cercanías</p>", unsafe_allow_html=True)
            
            with col2:
                st.image("data/Cañerias.png", use_container_width=True)
                st.markdown("<h4 style='text-align: center;'>Cañerías de Gas</h4>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; font-size: 12px; color: #666;'>Cartel para múltiples cañerías en las cercanías</p>", unsafe_allow_html=True)
            
            with col3:
                st.image("data/Gasoducto.png", use_container_width=True)
                st.markdown("<h4 style='text-align: center;'>Gasoducto</h4>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; font-size: 12px; color: #666;'>Cartel de gasoducto individual en las cercanías</p>", unsafe_allow_html=True)
            
            with col4:
                st.image("data/Gasoductos.png", use_container_width=True)
                st.markdown("<h4 style='text-align: center;'>Gasoductos</h4>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; font-size: 12px; color: #666;'>Cartel para red de múltiples gasoductos en las cercanías</p>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            try:
                stock = sheets_service.obtener_stock()
                
                if stock:
                    stock_df = pd.DataFrame([
                        {
                            "Tipo de Cartel": k,
                            "Cantidad": v,
                            "Estado": "🔴 Crítico" if v <= 5 else "⚠️ Bajo" if v <= 10 else "✅ OK"
                        }
                        for k, v in stock.items()
                    ]).sort_values("Cantidad")
                    
                    # Métricas
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Items", len(stock))
                    with col2:
                        criticos = len([v for v in stock.values() if v <= 5])
                        st.metric("Stock Crítico", criticos)
                    with col3:
                        total_unidades = sum(stock.values())
                        st.metric("Total Unidades", total_unidades)
                    
                    st.markdown("---")
                    
                    # Tabla
                    st.dataframe(stock_df, hide_index=True)
                    
                    # Gráfico
                    st.bar_chart(stock_df.set_index("Tipo de Cartel")["Cantidad"])
                else:
                    st.info("No hay datos de stock")
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Tab 2: Registrar movimiento
        with tab2:
            st.subheader("Registrar Movimiento de Stock")
            
            col1, col2 = st.columns(2)
            
            with col1:
                tipo_movimiento = st.selectbox("Tipo de Movimiento", ["entrada", "salida"])
                tipo_cartel = st.text_input("Tipo de Cartel")
                cantidad = st.number_input("Cantidad", min_value=1, value=1)
            
            with col2:
                operario = st.text_input("Operario")
                notas = st.text_area("Notas", height=100)
            
            if st.button("💾 Registrar Movimiento", type="primary"):
                if tipo_cartel and operario:
                    try:
                        datos = {
                            "tipo_movimiento": tipo_movimiento,
                            "tipo_cartel": tipo_cartel,
                            "cantidad": cantidad if tipo_movimiento == "entrada" else -cantidad,
                            "operario": operario,
                            "notas": notas
                        }
                        
                        if sheets_service.registrar_movimiento_stock(datos):
                            st.success("✅ Movimiento registrado exitosamente")
                            
                            # Actualizar stock si es salida
                            if tipo_movimiento == "salida":
                                sheets_service.actualizar_stock(tipo_cartel, cantidad)
                        else:
                            st.error("❌ Error al registrar movimiento")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Completa todos los campos requeridos")
        
        # Tab 3: Historial
        with tab3:
            st.subheader("Historial de Movimientos - Carteles en Trabajo")
            
            # Obtener tipos de cartel reales desde Google Sheets
            try:
                carteles_datos = sheets_service.obtener_carteles_ecogas()
                tipos_carteles = {}
                for cartel in carteles_datos:
                    numero = cartel.get('numero', '')
                    if numero in ['1', '2', '3', '4']:
                        tipos_carteles[numero] = cartel.get('tipo_cartel', 'Cartel Tipo D')
            except:
                # Valores por defecto si falla la consulta
                tipos_carteles = {'1': 'Cartel Tipo D', '2': 'Cartel Tipo D', '3': 'Cartel Tipo E', '4': 'Cartel Tipo D'}
            
            # Crear movimientos de ejemplo para los carteles 1, 2, 3 y 4
            from datetime import datetime, timedelta
            
            movimientos_ejemplo = [
                {
                    "Fecha": "08/01/2026 09:30",
                    "Cartel": "#4",
                    "Tipo": tipos_carteles.get('4', 'Cartel Tipo D'),
                    "Movimiento": "📤 Salida",
                    "Cantidad": 1,
                    "Ramal": "Ramal Rio Cuarto",
                    "Operario": "Juan Pérez",
                    "Estado": "✅ Instalado",
                    "Notas": "Instalación completada en Inicio Cruce RNA005"
                },
                {
                    "Fecha": "10/01/2026 10:15",
                    "Cartel": "#1",
                    "Tipo": tipos_carteles.get('1', 'Cartel Tipo D'),
                    "Movimiento": "📤 Salida",
                    "Cantidad": 1,
                    "Ramal": "Ramal Rio Cuarto",
                    "Operario": "María González",
                    "Estado": "🔴 En Instalación",
                    "Notas": "En proceso de instalación"
                },
                {
                    "Fecha": "10/01/2026 11:00",
                    "Cartel": "#2",
                    "Tipo": tipos_carteles.get('2', 'Cartel Tipo D'),
                    "Movimiento": "📤 Salida",
                    "Cantidad": 1,
                    "Ramal": "Ramal Rio Cuarto",
                    "Operario": "María González",
                    "Estado": "🔴 En Instalación",
                    "Notas": "En proceso de instalación"
                },
                {
                    "Fecha": "10/01/2026 14:30",
                    "Cartel": "#3",
                    "Tipo": tipos_carteles.get('3', 'Cartel Tipo E'),
                    "Movimiento": "📤 Salida",
                    "Cantidad": 1,
                    "Ramal": "Ramales Rio Cuarto",
                    "Operario": "Carlos Rodríguez",
                    "Estado": "🔴 En Instalación",
                    "Notas": "En proceso de instalación"
                },
                {
                    "Fecha": "08/01/2026 08:00",
                    "Cartel": "#4",
                    "Tipo": tipos_carteles.get('4', 'Cartel Tipo D'),
                    "Movimiento": "📥 Entrada",
                    "Cantidad": 1,
                    "Ramal": "Ramal Rio Cuarto",
                    "Operario": "Almacén Central",
                    "Estado": "📦 Stock",
                    "Notas": "Recepción de material nuevo"
                },
                {
                    "Fecha": "09/01/2026 16:00",
                    "Cartel": "#1, #2, #3",
                    "Tipo": "Varios tipos",
                    "Movimiento": "📥 Entrada",
                    "Cantidad": 3,
                    "Ramal": "Ramal Rio Cuarto",
                    "Operario": "Almacén Central",
                    "Estado": "📦 Stock",
                    "Notas": "Recepción de lote para instalación"
                }
            ]
            
            df_movimientos = pd.DataFrame(movimientos_ejemplo)
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                filtro_tipo = st.selectbox("Filtrar por Tipo de Movimiento", 
                                          ["Todos", "📤 Salida", "📥 Entrada"])
            with col2:
                filtro_estado = st.selectbox("Filtrar por Estado",
                                            ["Todos", "✅ Instalado", "🔴 En Instalación", "📦 Stock"])
            
            # Aplicar filtros
            df_filtrado = df_movimientos.copy()
            if filtro_tipo != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Movimiento"] == filtro_tipo]
            if filtro_estado != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Estado"] == filtro_estado]
            
            # Mostrar estadísticas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Movimientos", len(df_filtrado))
            with col2:
                salidas = len(df_filtrado[df_filtrado["Movimiento"] == "📤 Salida"])
                st.metric("Salidas", salidas)
            with col3:
                entradas = len(df_filtrado[df_filtrado["Movimiento"] == "📥 Entrada"])
                st.metric("Entradas", entradas)
            with col4:
                en_instalacion = len(df_filtrado[df_filtrado["Estado"] == "🔴 En Instalación"])
                st.metric("En Instalación", en_instalacion)
            
            st.markdown("---")
            
            # Tabla de movimientos
            st.dataframe(df_filtrado, hide_index=True, use_container_width=True)
            
            # Resumen por operario
            st.markdown("### 👷 Resumen por Operario")
            operarios = df_filtrado.groupby("Operario").agg({
                "Cantidad": "sum",
                "Cartel": "count"
            }).rename(columns={"Cartel": "Movimientos"})
            st.dataframe(operarios, use_container_width=True)
    else:
        st.error("Servicio de Google Sheets no disponible")


# ===== MODO EMPLEADOS =====
elif modo == "👷 Empleados":
    st.header("👷 Gestión de Empleados")
    
    if sheets_service:
        tab1, tab2 = st.tabs(["📋 Lista de Empleados", "➕ Agregar Empleado"])
        
        with tab1:
            try:
                empleados = sheets_service.obtener_empleados()
                
                if empleados:
                    df = pd.DataFrame(empleados)
                    st.dataframe(df, hide_index=True)
                else:
                    st.info("No hay empleados registrados")
            except Exception as e:
                st.error(f"Error: {e}")
        
        with tab2:
            st.subheader("Agregar Nuevo Empleado")
            
            col1, col2 = st.columns(2)
            
            with col1:
                nombre = st.text_input("Nombre Completo")
                telefono = st.text_input("Teléfono")
                cargo = st.selectbox("Cargo", ["Operario", "Supervisor", "Administrador"])
            
            with col2:
                email = st.text_input("Email")
                whatsapp = st.text_input("WhatsApp", "+549")
                estado = st.selectbox("Estado", ["Activo", "Inactivo"])
            
            if st.button("➕ Agregar Empleado", type="primary"):
                if nombre and telefono:
                    try:
                        datos = {
                            "nombre": nombre,
                            "telefono": telefono,
                            "cargo": cargo,
                            "email": email,
                            "whatsapp": whatsapp,
                            "estado": estado
                        }
                        
                        if sheets_service.agregar_empleado(datos):
                            st.success("✅ Empleado agregado exitosamente")
                        else:
                            st.error("❌ Error al agregar empleado")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Completa los campos requeridos")
    else:
        st.error("Servicio no disponible")


# ===== MODO ÓRDENES =====
elif modo == "📋 Órdenes":
    st.header("📋 Gestión de Órdenes de Trabajo")
    
    if sheets_service:
        st.subheader("Órdenes de Trabajo - Carteles ECOGAS")
        
        try:
            # Obtener carteles desde Google Sheets
            carteles = sheets_service.obtener_carteles_ecogas()
            
            # Filtrar solo carteles con trabajos (en proceso o realizados)
            # Para el demo, usamos los carteles 1, 2, 3, 4 como ejemplo
            ordenes_trabajo = []
            
            for cartel in carteles:
                numero = cartel.get('numero', '')
                estado = cartel.get('estado', '')
                
                # Determinar estado del trabajo
                estado_trabajo = None
                if numero in ['1', '2', '3']:
                    estado_trabajo = '🔴 En Proceso'
                    fecha_inicio = '10/01/2026'
                    fecha_fin = '-'
                    operario = 'María González' if numero in ['1', '2'] else 'Carlos Rodríguez'
                    prioridad = '🔴 Alta'
                elif numero == '4':
                    estado_trabajo = '✅ Realizado'
                    fecha_inicio = '08/01/2026'
                    fecha_fin = '14/01/2026'
                    operario = 'Juan Pérez'
                    prioridad = '🟢 Normal'
                elif 'realizado' in estado.lower() or 'completado' in estado.lower():
                    estado_trabajo = '✅ Realizado'
                    fecha_inicio = '05/01/2026'
                    fecha_fin = '12/01/2026'
                    operario = 'Equipo VialP'
                    prioridad = '🟢 Normal'
                elif 'proceso' in estado.lower():
                    estado_trabajo = '🔴 En Proceso'
                    fecha_inicio = '10/01/2026'
                    fecha_fin = '-'
                    operario = 'Equipo VialP'
                    prioridad = '🟠 Media'
                elif 'pendiente' in estado.lower():
                    estado_trabajo = '🟠 Pendiente'
                    fecha_inicio = '-'
                    fecha_fin = '-'
                    operario = 'Sin asignar'
                    prioridad = '🟢 Normal'
                
                if estado_trabajo:
                    orden = {
                        'Cartel': f"#{numero}",
                        'Tipo': cartel.get('tipo_cartel', 'N/A'),
                        'Ramal': cartel.get('gasoducto_ramal', 'N/A'),
                        'Ubicación': cartel.get('ubicacion', 'N/A'),
                        'Estado': estado_trabajo,
                        'Operario': operario,
                        'Fecha Inicio': fecha_inicio,
                        'Fecha Fin': fecha_fin,
                        'Prioridad': prioridad
                    }
                    ordenes_trabajo.append(orden)
            
            if ordenes_trabajo:
                # Métricas superiores
                col1, col2, col3, col4, col5 = st.columns(5)
                
                total = len(ordenes_trabajo)
                en_proceso = len([o for o in ordenes_trabajo if '🔴 En Proceso' in o['Estado']])
                realizados = len([o for o in ordenes_trabajo if '✅ Realizado' in o['Estado']])
                pendientes = len([o for o in ordenes_trabajo if '🟠 Pendiente' in o['Estado']])
                
                # Calcular tiempo promedio (solo para realizados con fechas válidas)
                from datetime import datetime
                tiempos = []
                for orden in ordenes_trabajo:
                    if orden['Fecha Fin'] != '-' and orden['Fecha Inicio'] != '-':
                        try:
                            inicio = datetime.strptime(orden['Fecha Inicio'], '%d/%m/%Y')
                            fin = datetime.strptime(orden['Fecha Fin'], '%d/%m/%Y')
                            dias = (fin - inicio).days
                            if dias >= 0:
                                tiempos.append(dias)
                        except:
                            pass
                
                tiempo_promedio = sum(tiempos) / len(tiempos) if tiempos else 0
                
                with col1:
                    st.metric("Total Órdenes", total)
                with col2:
                    st.metric("En Proceso", en_proceso)
                with col3:
                    st.metric("Realizados", realizados)
                with col4:
                    st.metric("Pendientes", pendientes)
                with col5:
                    st.metric("⏱️ Tiempo Promedio", f"{tiempo_promedio:.1f} días")
                
                st.markdown("---")
                
                # Filtros
                col1, col2 = st.columns(2)
                with col1:
                    filtro_estado = st.selectbox("Filtrar por Estado", 
                                                ["Todos", "🔴 En Proceso", "✅ Realizado", "🟠 Pendiente"])
                with col2:
                    filtro_operario = st.selectbox("Filtrar por Operario",
                                                  ["Todos"] + sorted(list(set([o['Operario'] for o in ordenes_trabajo]))))
                
                # Aplicar filtros
                ordenes_filtradas = ordenes_trabajo.copy()
                if filtro_estado != "Todos":
                    ordenes_filtradas = [o for o in ordenes_filtradas if filtro_estado in o['Estado']]
                if filtro_operario != "Todos":
                    ordenes_filtradas = [o for o in ordenes_filtradas if o['Operario'] == filtro_operario]
                
                # Mostrar tabla
                df_ordenes = pd.DataFrame(ordenes_filtradas)
                st.dataframe(df_ordenes, hide_index=True, use_container_width=True)
                
                st.markdown("---")
                
                # Análisis de Tiempos en la misma página
                st.markdown("### 📊 Análisis de Tiempos de Ejecución")
                
                # Datos de ejemplo para análisis basados en tipos reales
                datos_tiempos = pd.DataFrame([
                    {"Tipo": "D", "Tiempo Promedio (días)": 6, "Completados": 1, "En Proceso": 2},
                    {"Tipo": "E", "Tiempo Promedio (días)": 0, "Completados": 0, "En Proceso": 1},
                    {"Tipo": "A", "Tiempo Promedio (días)": 7, "Completados": 3, "En Proceso": 0},
                    {"Tipo": "B", "Tiempo Promedio (días)": 5, "Completados": 2, "En Proceso": 1},
                    {"Tipo": "C", "Tiempo Promedio (días)": 6, "Completados": 1, "En Proceso": 0},
                ])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### ⏱️ Tiempos por Tipo de Cartel")
                    st.dataframe(datos_tiempos, hide_index=True, use_container_width=True)
                
                with col2:
                    st.markdown("#### 📈 Estadísticas Generales")
                    st.metric("Tiempo Promedio Total", "6.0 días")
                    st.metric("Tiempo Mínimo", "5 días")
                    st.metric("Tiempo Máximo", "7 días")
                    st.metric("Eficiencia", "75%")
                
                st.markdown("---")
                
                # Gráfico de distribución
                st.markdown("#### 📊 Distribución de Trabajos por Estado")
                estados_data = pd.DataFrame({
                    'Estado': ['En Proceso', 'Realizado', 'Pendiente'],
                    'Cantidad': [4, 6, 3]
                })
                
                st.bar_chart(estados_data.set_index('Estado'))
                
            else:
                st.info("No hay órdenes de trabajo registradas")
                
        except Exception as e:
            st.error(f"Error al cargar órdenes: {e}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.error("Servicio no disponible")


# ===== MODO ZONAS Y RAMALES =====
elif modo == "🗺️ Zonas y Ramales":
    st.header("🗺️ Gestión de Zonas y Ramales")
    st.markdown("*Visualización de ramales de gasoductos y zonas de cobertura*")
    
    tab1, tab2, tab3 = st.tabs(["📊 Ramales ECOGAS", "🗺️ Mapa de Ramales", "🏢 Zonas Operativas"])
    
    with tab1:
        if sheets_service:
            try:
                st.info("🔄 Cargando datos de ECOGAS...")
                
                # Obtener carteles desde Google Sheets
                carteles = sheets_service.obtener_carteles_ecogas()
            
                st.success(f"✅ Datos cargados: {len(carteles)} carteles encontrados")
                
                if not carteles:
                    st.warning("⚠️ No se encontraron carteles en Google Sheets")
                else:
                    # Agrupar por ramal
                    ramales_dict = {}
                    for cartel in carteles:
                        ramal_raw = cartel.get('gasoducto_ramal', 'N/A')
                        # Normalizar: quitar saltos de línea y espacios múltiples
                        ramal = ' '.join(ramal_raw.split())
                        ubicacion = cartel.get('ubicacion', '')
                        lat = cartel.get('latitud')
                        lon = cartel.get('longitud')
                        
                        if ramal not in ramales_dict:
                            ramales_dict[ramal] = {
                                'Ramal': ramal,
                                'Ubicaciones': [],
                                'Carteles': 0,
                                'Latitud': lat,
                                'Longitud': lon
                            }
                        
                        ramales_dict[ramal]['Carteles'] += 1
                        if ubicacion:
                            ramales_dict[ramal]['Ubicaciones'].append(ubicacion)
                        
                        # Actualizar coordenadas si no las tenía
                        if not ramales_dict[ramal]['Latitud'] and lat:
                            ramales_dict[ramal]['Latitud'] = lat
                        if not ramales_dict[ramal]['Longitud'] and lon:
                            ramales_dict[ramal]['Longitud'] = lon
                    
                    # Convertir a DataFrame
                    ramales_list = []
                    for ramal, data in ramales_dict.items():
                        ramales_list.append({
                            'Ramal/Gasoducto': ramal,
                            'Total Carteles': data['Carteles'],
                            'Ubicaciones': len(set(data['Ubicaciones'])),
                            'Ejemplo Ubicación': data['Ubicaciones'][0] if data['Ubicaciones'] else 'N/A'
                        })
                    
                    df_ramales = pd.DataFrame(ramales_list).sort_values('Total Carteles', ascending=False)
                    
                    # Estadísticas
                    st.subheader("📊 Estadísticas de Ramales")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Ramales", len(ramales_dict))
                    with col2:
                        st.metric("Total Carteles", len(carteles))
                    with col3:
                        total_ubicaciones = sum([len(set(r['Ubicaciones'])) for r in ramales_dict.values()])
                        st.metric("Ubicaciones Únicas", total_ubicaciones)
                    with col4:
                        zonas_unicas = len(set([c.get('zona', 'N/A') for c in carteles if c.get('zona')]))
                        st.metric("Zonas Operativas", zonas_unicas)
                    
                    st.markdown("---")
                    
                    # Tabla de ramales
                    st.dataframe(df_ramales, hide_index=True)
                    
                    # Detalles por ramal
                    st.subheader("🔍 Detalle por Ramal")
                    ramal_seleccionado = st.selectbox(
                        "Selecciona un ramal para ver detalles",
                        options=["Todos"] + list(ramales_dict.keys())
                    )
                    
                    if ramal_seleccionado != "Todos":
                        # Comparar con nombre normalizado
                        carteles_ramal = [c for c in carteles if ' '.join(c.get('gasoducto_ramal', '').split()) == ramal_seleccionado]
                        if carteles_ramal:
                            # Calcular estadísticas por estado
                            estados_count = {'en_proceso': 0, 'realizado': 0, 'pendiente': 0, 'revisado': 0}
                            
                            for cartel in carteles_ramal:
                                numero_str = str(cartel.get('numero', ''))
                                
                                # Asignar estado según lógica de ejemplo
                                if numero_str in ['1', '2', '3']:
                                    estados_count['en_proceso'] += 1
                                elif numero_str == '4':
                                    estados_count['realizado'] += 1
                                else:
                                    # Usar estado de la planilla
                                    estado_planilla = str(cartel.get('estado', '')).lower().strip()
                                    if 'realiz' in estado_planilla or 'complet' in estado_planilla:
                                        estados_count['realizado'] += 1
                                    elif 'proces' in estado_planilla:
                                        estados_count['en_proceso'] += 1
                                    elif 'revis' in estado_planilla:
                                        estados_count['revisado'] += 1
                                    else:
                                        estados_count['pendiente'] += 1
                            
                            # Mostrar métricas por estado
                            st.markdown(f"### 📊 Resumen del Ramal: **{ramal_seleccionado}**")
                            col1, col2, col3, col4, col5 = st.columns(5)
                            with col1:
                                st.metric("📍 Total", len(carteles_ramal))
                            with col2:
                                st.metric("🔴 En Proceso", estados_count['en_proceso'])
                            with col3:
                                st.metric("✅ Realizado", estados_count['realizado'])
                            with col4:
                                st.metric("🟠 Pendiente", estados_count['pendiente'])
                            with col5:
                                st.metric("🔵 Revisado", estados_count['revisado'])
                            
                            st.markdown("---")
                            
                            # Agregar columna de estado con iconos a cada cartel
                            carteles_con_estado = []
                            for cartel in carteles_ramal:
                                cartel_copia = cartel.copy()
                                numero_str = str(cartel.get('numero', ''))
                                
                                # Asignar estado según lógica de ejemplo
                                if numero_str in ['1', '2', '3']:
                                    cartel_copia['Estado Trabajo'] = '🔴 En Proceso'
                                    # Fechas de ejemplo para items en proceso
                                    cartel_copia['Fecha Inicio'] = '10/01/2026'
                                    cartel_copia['Fecha Fin'] = '-'
                                elif numero_str == '4':
                                    cartel_copia['Estado Trabajo'] = '✅ Realizado'
                                    # Fechas de ejemplo para item realizado
                                    cartel_copia['Fecha Inicio'] = '08/01/2026'
                                    cartel_copia['Fecha Fin'] = '14/01/2026'
                                else:
                                    # Usar estado de la planilla
                                    estado_planilla = str(cartel.get('estado', '')).lower().strip()
                                    if 'realiz' in estado_planilla or 'complet' in estado_planilla:
                                        cartel_copia['Estado Trabajo'] = '✅ Realizado'
                                        cartel_copia['Fecha Inicio'] = cartel.get('fecha_inicio', '-')
                                        cartel_copia['Fecha Fin'] = cartel.get('fecha_fin', '-')
                                    elif 'proces' in estado_planilla:
                                        cartel_copia['Estado Trabajo'] = '🔴 En Proceso'
                                        cartel_copia['Fecha Inicio'] = cartel.get('fecha_inicio', '-')
                                        cartel_copia['Fecha Fin'] = '-'
                                    elif 'revis' in estado_planilla:
                                        cartel_copia['Estado Trabajo'] = '🔵 Revisado'
                                        cartel_copia['Fecha Inicio'] = cartel.get('fecha_inicio', '-')
                                        cartel_copia['Fecha Fin'] = cartel.get('fecha_fin', '-')
                                    else:
                                        cartel_copia['Estado Trabajo'] = '🟠 Pendiente'
                                        cartel_copia['Fecha Inicio'] = '-'
                                        cartel_copia['Fecha Fin'] = '-'
                                
                                carteles_con_estado.append(cartel_copia)
                            
                            # Mostrar tabla de carteles con estado
                            df_carteles = pd.DataFrame(carteles_con_estado)
                            
                            # Reorganizar columnas para que Estado Trabajo, Fecha Inicio y Fecha Fin aparezcan primero
                            cols = df_carteles.columns.tolist()
                            cols_ordenadas = []
                            
                            # Agregar primero las columnas de estado y fechas
                            if 'Estado Trabajo' in cols:
                                cols_ordenadas.append('Estado Trabajo')
                                cols.remove('Estado Trabajo')
                            if 'Fecha Inicio' in cols:
                                cols_ordenadas.append('Fecha Inicio')
                                cols.remove('Fecha Inicio')
                            if 'Fecha Fin' in cols:
                                cols_ordenadas.append('Fecha Fin')
                                cols.remove('Fecha Fin')
                            
                            # Agregar el resto de columnas
                            cols_ordenadas.extend(cols)
                            df_carteles = df_carteles[cols_ordenadas]
                            
                            st.dataframe(df_carteles, hide_index=True)
                        else:
                            st.warning("No se encontraron carteles para este ramal")
                        
            except Exception as e:
                st.error(f"❌ Error al cargar ramales: {str(e)}")
                import traceback
                with st.expander("🔍 Ver detalles del error"):
                    st.code(traceback.format_exc())
        else:
            st.warning("⚠️ Servicio de Google Sheets no disponible")
    
    with tab2:
        st.subheader("🗺️ Mapa Interactivo de Ramales")
        st.markdown("*Visualización geográfica de todos los carteles*")
        
        if sheets_service:
            try:
                # Obtener carteles con coordenadas
                carteles = sheets_service.obtener_carteles_ecogas()
                carteles_con_coords = [c for c in carteles if c.get('latitud') and c.get('longitud')]
                
                if carteles_con_coords:
                    # Calcular centro del mapa (promedio de coordenadas)
                    lats = [c['latitud'] for c in carteles_con_coords]
                    lons = [c['longitud'] for c in carteles_con_coords]
                    centro_lat = sum(lats) / len(lats)
                    centro_lon = sum(lons) / len(lons)
                    
                    st.success(f"🎯 Centro del mapa: Lat {centro_lat:.4f}, Lon {centro_lon:.4f}")
                    
                    # Crear mapa centrado en los datos
                    m = folium.Map(
                        location=[centro_lat, centro_lon],
                        zoom_start=7,
                        tiles="OpenStreetMap"
                    )
                    
                    # Colores por estado de trabajo
                    colores_estado = {
                        'realizado': 'green',
                        'en_proceso': 'red',
                        'pendiente': 'orange',
                        'revisado': 'blue'
                    }
                    
                    # Filtro por ramal - normalizar nombres
                    ramales_unicos = sorted(list(set([' '.join(c.get('gasoducto_ramal', 'N/A').split()) for c in carteles_con_coords])))
                    ramal_filtro = st.selectbox(
                        "Filtrar por Ramal/Gasoducto",
                        options=["Todos"] + ramales_unicos
                    )
                    
                    # Filtrar carteles
                    if ramal_filtro != "Todos":
                        carteles_filtrados = [c for c in carteles_con_coords if ' '.join(c.get('gasoducto_ramal', '').split()) == ramal_filtro]
                    else:
                        carteles_filtrados = carteles_con_coords
                    
                    # Agregar marcadores
                    for cartel in carteles_filtrados:
                        lat = cartel['latitud']
                        lon = cartel['longitud']
                        tipo = cartel.get('tipo_cartel', 'Cartel')
                        ramal = cartel.get('gasoducto_ramal', 'N/A')
                        ubicacion = cartel.get('ubicacion', 'Sin ubicación')
                        numero = cartel.get('numero', 'N/A')
                        observaciones = cartel.get('observaciones', 'Sin observaciones')
                        zona = cartel.get('zona', 'N/A')
                        
                        # Asignar estado y color - Items de ejemplo
                        numero_str = str(numero)
                        if numero_str in ['1', '2', '3']:
                            estado = 'en_proceso'
                            color = colores_estado['en_proceso']
                        elif numero_str == '4':
                            estado = 'realizado'
                            color = colores_estado['realizado']
                        else:
                            # Usar estado de la planilla si existe
                            estado_raw = cartel.get('estado', '').lower()
                            if 'realizado' in estado_raw or 'completado' in estado_raw or 'terminado' in estado_raw:
                                estado = 'realizado'
                                color = colores_estado['realizado']
                            elif 'proceso' in estado_raw or 'trabajando' in estado_raw or 'ejecutando' in estado_raw:
                                estado = 'en_proceso'
                                color = colores_estado['en_proceso']
                            elif 'revisado' in estado_raw or 'verificado' in estado_raw or 'inspeccionado' in estado_raw:
                                estado = 'revisado'
                                color = colores_estado['revisado']
                            elif 'pendiente' in estado_raw or 'por hacer' in estado_raw or 'programado' in estado_raw:
                                estado = 'pendiente'
                                color = colores_estado['pendiente']
                            else:
                                estado = 'pendiente'
                                color = colores_estado.get(estado, 'gray')
                        
                        # Texto del estado para mostrar
                        estados_texto = {
                            'realizado': '✅ Realizado',
                            'en_proceso': '🔴 En Proceso',
                            'pendiente': '🟠 Pendiente',
                            'revisado': '🔵 Revisado'
                        }
                        estado_texto = estados_texto.get(estado, '⚪ Sin Estado')
                        
                        # HTML del popup
                        popup_html = f"""
                        <div style="font-family: Arial; width: 250px; padding: 10px;">
                            <h4 style="margin: 0 0 10px 0; color: {color};">🚧 Cartel #{numero}</h4>
                            <p style="margin: 5px 0; font-size: 14px; font-weight: bold; color: {color};"><b>Estado:</b> {estado_texto}</p>
                            <p style="margin: 5px 0;"><b>Tipo:</b> {tipo}</p>
                            <p style="margin: 5px 0;"><b>Ramal:</b> {ramal}</p>
                            <p style="margin: 5px 0;"><b>📍 Ubicación:</b> {ubicacion}</p>
                            <p style="margin: 5px 0;"><b>🏢 Zona:</b> {zona}</p>
                            <p style="margin: 5px 0;"><b>📝 Observaciones:</b> {observaciones[:50]}...</p>
                        </div>
                        """
                        
                        folium.Marker(
                            location=[lat, lon],
                            popup=folium.Popup(popup_html, max_width=300),
                            tooltip=f"#{numero} - {ramal} - {estado_texto}",
                            icon=folium.Icon(color=color, icon="info-sign")
                        ).add_to(m)
                    
                    # Mostrar mapa
                    st_folium(m, width=1400, height=600)
                    
                    st.info(f"📍 Mostrando {len(carteles_filtrados)} de {len(carteles_con_coords)} carteles georeferenciados")
                    
                    # Leyenda
                    st.markdown("### 📋 Leyenda de Estados de Trabajo")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown("🔴 **En Proceso**")
                    with col2:
                        st.markdown("✅ **Realizado**")
                    with col3:
                        st.markdown("🔵 **Revisado**")
                    with col4:
                        st.markdown("🟠 **Pendiente**")
                else:
                    st.warning("⚠️ No hay carteles con coordenadas disponibles")
            except Exception as e:
                st.error(f"❌ Error al cargar mapa: {str(e)}")
                import traceback
                with st.expander("🔍 Ver detalles del error"):
                    st.code(traceback.format_exc())
        else:
            st.warning("⚠️ Servicio de Google Sheets no disponible")
    
    with tab3:
        st.subheader("🏢 Centros Operativos y Zonas")
        st.markdown("*Distribución de carteles por zona operativa*")
        
        if sheets_service:
            try:
                carteles = sheets_service.obtener_carteles_ecogas()
                
                if carteles:
                    # Agrupar por zona
                    zonas_dict = {}
                    for cartel in carteles:
                        zona = cartel.get('zona', 'Sin zona')
                        if not zona or zona == '':
                            zona = 'Sin zona'
                        
                        if zona not in zonas_dict:
                            zonas_dict[zona] = {
                                'Zona': zona,
                                'Carteles': 0,
                                'Ramales': set(),
                                'Coordenadas': 0
                            }
                        
                        zonas_dict[zona]['Carteles'] += 1
                        if cartel.get('gasoducto_ramal'):
                            ramal_norm = ' '.join(cartel.get('gasoducto_ramal', '').split())
                            zonas_dict[zona]['Ramales'].add(ramal_norm)
                        if cartel.get('latitud') and cartel.get('longitud'):
                            zonas_dict[zona]['Coordenadas'] += 1
                    
                    # Convertir a DataFrame
                    zonas_list = []
                    for zona, data in zonas_dict.items():
                        zonas_list.append({
                            'Zona Operativa': zona,
                            'Total Carteles': data['Carteles'],
                            'Ramales': len(data['Ramales']),
                            'Con Coordenadas': data['Coordenadas'],
                            '% Georreferenciado': f"{(data['Coordenadas']/data['Carteles']*100):.1f}%" if data['Carteles'] > 0 else "0%"
                        })
                    
                    df_zonas = pd.DataFrame(zonas_list).sort_values('Total Carteles', ascending=False)
                    
                    # Estadísticas generales
                    st.markdown("### 📊 Resumen por Zona")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Zonas", len(zonas_dict))
                    with col2:
                        st.metric("Zona Mayor", df_zonas.iloc[0]['Zona Operativa'] if len(df_zonas) > 0 else "N/A")
                    with col3:
                        st.metric("Carteles", df_zonas.iloc[0]['Total Carteles'] if len(df_zonas) > 0 else 0)
                    
                    st.markdown("---")
                    
                    # Tabla de zonas
                    st.dataframe(df_zonas, hide_index=True)
                    
                    # Gráfico de barras
                    st.markdown("### 📈 Distribución de Carteles por Zona")
                    st.bar_chart(df_zonas.set_index('Zona Operativa')['Total Carteles'])
                    
                    # Detalle por zona
                    st.markdown("### 🔍 Detalle por Zona")
                    zona_seleccionada = st.selectbox(
                        "Selecciona una zona para ver detalles",
                        options=["Todas"] + sorted(list(zonas_dict.keys()))
                    )
                    
                    if zona_seleccionada != "Todas":
                        carteles_zona = [c for c in carteles if c.get('zona', 'Sin zona') == zona_seleccionada or (c.get('zona', '') == '' and zona_seleccionada == 'Sin zona')]
                        
                        if carteles_zona:
                            st.info(f"📍 {len(carteles_zona)} carteles en la zona {zona_seleccionada}")
                            
                            # Ramales en esta zona
                            ramales_zona = set([' '.join(c.get('gasoducto_ramal', '').split()) for c in carteles_zona if c.get('gasoducto_ramal')])
                            st.write(f"**Ramales en esta zona ({len(ramales_zona)}):**")
                            for ramal in sorted(ramales_zona):
                                st.write(f"• {ramal}")
                            
                            st.markdown("---")
                            
                            # Mostrar tabla de carteles
                            df_carteles_zona = pd.DataFrame(carteles_zona)
                            st.dataframe(df_carteles_zona, hide_index=True)
                        else:
                            st.warning("No se encontraron carteles en esta zona")
                else:
                    st.info("No hay datos disponibles")
            except Exception as e:
                st.error(f"❌ Error al cargar zonas: {str(e)}")
                import traceback
                with st.expander("🔍 Ver detalles del error"):
                    st.code(traceback.format_exc())
        else:
            st.warning("⚠️ Servicio de Google Sheets no disponible")


# Footer
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)
with col_footer1:
    st.caption("🚦 **Vial Parking**")
    st.caption("Gestión de Cartelería ECOGAS")
with col_footer2:
    st.caption("🌎 Ramales de Gasoductos")
    st.caption("Cobertura Nacional | Argentina")
with col_footer3:
    st.caption("📊 Dashboard Demo v1.0")
    st.caption("Powered by Streamlit")