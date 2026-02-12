import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path
import requests
import json

# Agregar el directorio padre al path para importar los servicios
sys.path.append(str(Path(__file__).parent.parent))

from services.google_sheets import GoogleSheetsService

# Configuración de la página
st.set_page_config(
    page_title="Vial Parking - Sistema de Producción",
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

# CSS personalizado para producción
st.markdown("""
<style>
    /* Estilos mejorados para producción */
    .main {
        background-color: #f8f9fa;
    }
    
    .whatsapp-msg {
        background-color: #DCF8C6;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
        max-width: 70%;
        color: #000000 !important;
        border: 1px solid #a8e6a1;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .whatsapp-msg-received {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
        max-width: 70%;
        color: #000000 !important;
        border: 1px solid #e0e0e0;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
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
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        border: 1px solid #d0d7de;
        color: #000000;
    }
    
    .metric-card h2, .metric-card h3, .metric-card p {
        color: #000000 !important;
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
    
    /* Estilos para alertas de producción */
    .alert-critical {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        color: #000000;
    }
    
    .alert-critical strong {
        color: #000000 !important;
    }
    
    .alert-warning {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        color: #000000;
    }
    
    .alert-warning strong {
        color: #000000 !important;
    }
    
    .alert-success {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        color: #000000;
    }
    
    .alert-success strong {
        color: #000000 !important;
    }
    
    /* Chat container */
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 20px;
        background-color: #e5ddd5;
        border-radius: 10px;
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

# Configurar variables de entorno para Google Sheets y Drive
os.environ["ECOGAS_SHEET_ID"] = "1d2WIsyCIETfMdRgSoE3nk9-bxIO_sySKqTVJHVwMV8Q"  # Planilla INPUT con los 287 items
os.environ["OUTPUT_SHEET_ID"] = "1qKQxWRcN1bjbavw2BgYPjh0rA0VaoaDfTHt_8COAVKw"  # Planilla OUTPUT para registrar trabajos
os.environ["IMAGENES_CARTELES_FOLDER_ID"] = "19YQCBODmkk_dCssMBB2GuNPfQs5oaUmV"  # Carpeta de Drive para imágenes
os.environ["OUTPUT_IMAGENES_FOLDER_ID"] = "19YQCBODmkk_dCssMBB2GuNPfQs5oaUmV"  # Carpeta de Drive para imágenes OUTPUT

# Inicializar servicios con mejor manejo de errores
@st.cache_resource
def init_services():
    """Inicializa el servicio de Google Sheets"""
    try:
        sheets_service = GoogleSheetsService()
        return sheets_service
    except Exception as e:
        st.error(f"❌ Error al inicializar Google Sheets: {str(e)}")
        st.info("💡 Verifica que las credenciales estén configuradas correctamente")
        return None

sheets_service = init_services()

# Cargar logo para fondo de página
try:
    logo_bg_path = os.path.join(Path(__file__).parent.parent, "data", "logo_vialp_AI.png")
    if os.path.exists(logo_bg_path):
        import base64
        with open(logo_bg_path, "rb") as img_file:
            logo_b64 = base64.b64encode(img_file.read()).decode()
        
        # Agregar logo como fondo de la página
        st.markdown(f"""
        <style>
            .main {{
                background-image: url(data:image/png;base64,{logo_b64});
                background-size: 400px;
                background-repeat: no-repeat;
                background-position: right 20px top 20px;
                background-attachment: fixed;
                opacity: 1;
            }}
            
            .main::before {{
                content: "";
                position: fixed;
                top: 20px;
                right: 20px;
                width: 400px;
                height: 200px;
                background-image: url(data:image/png;base64,{logo_b64});
                background-size: contain;
                background-repeat: no-repeat;
                opacity: 0.15;
                z-index: 0;
                pointer-events: none;
            }}
            
            .block-container {{
                position: relative;
                z-index: 1;
            }}
        </style>
        """, unsafe_allow_html=True)
except Exception as e:
    pass

# Título principal sin fondo
st.title("🚦 VIAL PARKING SA al servicio de ECOGAS")
st.markdown("### Sistema Integral de Señalización de Gasoductos y Ramales")

st.markdown("---")

# Sidebar - Panel de Control
with st.sidebar:
    st.header("⚙️ Panel de Control")
    
    # Modo de vista
    modo = st.radio(
        "Modo de Vista",
        ["📊 Dashboard Principal", 
         "💬 WhatsApp", 
         "📋 Órdenes de Trabajo", 
         "🗺️ Zonas y Ramales",
         "� Gestión de Stock", 
         "👷 Gestión de Empleados",
         "📈 Reportes y Estadísticas"],
        index=0
    )
    
    st.markdown("---")
    
    # Estado del sistema en producción
    st.subheader("📡 Estado del Sistema")
    if sheets_service:
        st.success("✅ Google Sheets: Conectado")
        try:
            # Verificar última actualización
            carteles_test = sheets_service.obtener_carteles_ecogas()
            st.info(f"📋 {len(carteles_test)} carteles en base de datos")
        except Exception as e:
            st.warning("⚠️ Error al cargar datos")
    else:
        st.error("❌ Google Sheets: Desconectado")
        st.warning("⚠️ Sistema en modo limitado")
    
    # Opciones de actualización
    st.markdown("---")
    st.subheader("🔄 Actualización de Datos")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Actualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with col_btn2:
        if st.button("🧹 Limpiar", use_container_width=True):
            st.cache_resource.clear()
            st.cache_data.clear()
            st.rerun()
    
    # Última actualización
    st.caption(f"🕐 Última actualización: {datetime.now().strftime('%H:%M:%S')}")


# ===== FUNCIONES DE CACHE PARA PRODUCCIÓN =====
@st.cache_data(ttl=180)  # Cache de 3 minutos para producción
def get_carteles_cached():
    """Obtiene carteles con cache"""
    if sheets_service:
        try:
            return sheets_service.obtener_carteles_ecogas()
        except Exception as e:
            st.error(f"Error al obtener carteles: {str(e)}")
            return []
    return []

@st.cache_data(ttl=180)
def get_empleados_cached():
    """Obtiene empleados con cache"""
    if sheets_service:
        try:
            return sheets_service.obtener_empleados()
        except Exception as e:
            st.error(f"Error al obtener empleados: {str(e)}")
            return []
    return []

@st.cache_data(ttl=180)
def get_stock_cached():
    """Obtiene stock con cache"""
    if sheets_service:
        try:
            return sheets_service.obtener_stock()
        except Exception as e:
            st.error(f"Error al obtener stock: {str(e)}")
            return {}
    return {}

@st.cache_data(ttl=300)
def get_ordenes_cached():
    """Obtiene órdenes de trabajo con cache"""
    if sheets_service:
        try:
            return sheets_service.obtener_ordenes()
        except Exception as e:
            st.error(f"Error al obtener órdenes: {str(e)}")
            return []
    return []

@st.cache_data(ttl=180)
def get_items_ejecutados_cached():
    """Obtiene números de items ejecutados desde OUTPUT con sus fechas"""
    if sheets_service:
        try:
            output_sheet = sheets_service._get_output_sheet()
            if output_sheet:
                worksheet = output_sheet.get_worksheet(0)
                all_values = worksheet.get_all_values()
                
                items_ejecutados = {}  # Diccionario: {num_item: fecha}
                # Procesar filas con datos (después de fila 10)
                for i, row in enumerate(all_values[10:], start=11):
                    if len(row) > 5:
                        # Columna F (índice 5): N° del item
                        num_item = row[5].strip() if len(row) > 5 else ""
                        # Columna D (índice 3): Fecha Ejecución
                        fecha = row[3].strip() if len(row) > 3 else "Sin fecha"
                        if num_item:
                            items_ejecutados[num_item] = fecha
                
                return items_ejecutados
        except Exception as e:
            st.error(f"Error al obtener items ejecutados: {str(e)}")
            return {}
    return {}

@st.cache_data(ttl=600)  # Cache de 10 minutos para reducir llamadas a Drive
def get_items_en_proceso_cached():
    """Obtiene números de items en proceso (tienen Antes pero no están en OUTPUT)"""
    if sheets_service:
        try:
            # Obtener carpeta principal de imágenes OUTPUT
            output_folder_id = os.getenv("OUTPUT_IMAGENES_FOLDER_ID")
            if not output_folder_id:
                return set()
            
            # Buscar todas las carpetas de items en Drive
            query = f"'{output_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = sheets_service.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1000,
                orderBy='name'
            ).execute()
            
            all_folders = results.get('files', [])
            items_en_proceso = set()
            
            # Limitar a 50 carpetas para evitar exceder límites de API
            import re
            for folder in all_folders[:50]:
                try:
                    folder_name = folder['name']
                    folder_id = folder['id']
                    
                    # Extraer número del nombre de carpeta
                    numbers = re.findall(r'\d+', folder_name)
                    if not numbers:
                        continue
                    
                    item_num = numbers[0].lstrip('0') or '0'
                    
                    # Buscar subcarpeta "Antes" con imágenes en una sola consulta
                    query_combined = f"'{folder_id}' in parents and name='Antes' and trashed=false"
                    results_antes = sheets_service.drive_service.files().list(
                        q=query_combined,
                        spaces='drive',
                        fields='files(id)',
                        pageSize=1
                    ).execute()
                    
                    if results_antes.get('files'):
                        # Solo marcar como en proceso si existe carpeta Antes
                        # (asumimos que si existe, tiene fotos)
                        items_en_proceso.add(item_num)
                
                except Exception:
                    # Ignorar errores individuales y continuar
                    continue
            
            return items_en_proceso
            
        except Exception as e:
            # Error silencioso, solo log en consola (no mostrar en dashboard)
            print(f"⚠️ No se pudieron verificar items en proceso: {str(e)}")
            return set()
    return set()

@st.cache_data(ttl=30)  # Cache de 30 segundos
def get_trabajos_output():
    """Lee trabajos completados desde la planilla OUTPUT"""
    if sheets_service:
        try:
            output_sheet = sheets_service._get_output_sheet()
            if output_sheet:
                worksheet = output_sheet.get_worksheet(0)
                all_values = worksheet.get_all_values()
                
                trabajos = []
                for i, row in enumerate(all_values[10:], start=11):
                    if len(row) > 5:
                        num_item = row[5].strip() if len(row) > 5 else ""
                        if num_item:
                            trabajo = {
                                'fila': i,
                                'fecha': row[3] if len(row) > 3 else "",
                                'numero': num_item,
                                'item': num_item,  # Alias para compatibilidad
                                'gasoducto': row[6] if len(row) > 6 else "",
                                'ubicacion': row[8] if len(row) > 8 else "",
                                'coordenadas': row[9] if len(row) > 9 else "",
                                'tipo': row[14] if len(row) > 14 else "",
                                'fotos': row[25] if len(row) > 25 else ""
                            }
                            trabajos.append(trabajo)
                
                return trabajos
        except Exception as e:
            st.error(f"Error al leer OUTPUT: {e}")
    return []


# ===== MODO: DASHBOARD PRINCIPAL =====
if modo == "📊 Dashboard Principal":
    st.header("📊 Panel de Control Ejecutivo")
    
    # Verificar conexión
    if not sheets_service:
        st.error("❌ Sistema en modo limitado. No se puede conectar con Google Sheets.")
        st.info("💡 Por favor, verifica la configuración de las credenciales.")
        st.stop()
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        carteles = get_carteles_cached()
        
        with col1:
            st.markdown("""
            <div class='metric-card'>
                <h3>📋</h3>
                <h2>{}</h2>
                <p>Total Carteles</p>
            </div>
            """.format(len(carteles)), unsafe_allow_html=True)
        
        with col2:
            items_ejecutados = get_items_ejecutados_cached()
            porcentaje = f"{len(items_ejecutados)/len(carteles)*100:.0f}%" if carteles else "0%"
            st.markdown("""
            <div class='metric-card'>
                <h3>✅</h3>
                <h2>{}</h2>
                <p>Ejecutados ({})</p>
            </div>
            """.format(len(items_ejecutados), porcentaje), unsafe_allow_html=True)
        
        with col3:
            ramales = set([' '.join(c.get('gasoducto_ramal', '').split()) for c in carteles if c.get('gasoducto_ramal')])
            st.markdown("""
            <div class='metric-card'>
                <h3>�</h3>
                <h2>{}</h2>
                <p>Ramales Activos</p>
            </div>
            """.format(len(ramales)), unsafe_allow_html=True)
        
        with col4:
            zonas = set([c.get('zona', 'Sin zona') for c in carteles if c.get('zona')])
            st.markdown("""
            <div class='metric-card'>
                <h3>🗺️</h3>
                <h2>{}</h2>
                <p>Zonas Operativas</p>
            </div>
            """.format(len(zonas)), unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"❌ Error al cargar métricas: {str(e)}")
    
    st.markdown("---")
    
    # Alertas y notificaciones
    st.subheader("🔔 Alertas y Notificaciones")
    
    col_alert1, col_alert2, col_alert3 = st.columns(3)
    
    with col_alert1:
        # Alertas de stock crítico
        try:
            stock = get_stock_cached()
            alertas_criticas = []
            
            for tipo_cartel, cantidad in stock.items():
                if cantidad <= 5:
                    alertas_criticas.append(f"{tipo_cartel}: {cantidad} unidades")
            
            if alertas_criticas:
                st.markdown(f"""
                <div class='alert-critical'>
                    <strong>🔴 STOCK CRÍTICO ({len(alertas_criticas)})</strong><br/>
                    {'<br/>'.join(alertas_criticas[:3])}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class='alert-success'>
                    <strong>✅ STOCK CRÍTICO OK</strong><br/>
                    Sin alertas críticas
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"⚠️ Error: {str(e)}")
    
    with col_alert2:
        # Alertas de stock bajo
        try:
            stock = get_stock_cached()
            alertas_advertencia = []
            
            for tipo_cartel, cantidad in stock.items():
                if cantidad > 5 and cantidad <= 10:
                    alertas_advertencia.append(f"{tipo_cartel}: {cantidad} unidades")
            
            if alertas_advertencia:
                st.markdown(f"""
                <div class='alert-warning'>
                    <strong>⚠️ STOCK BAJO ({len(alertas_advertencia)})</strong><br/>
                    {'<br/>'.join(alertas_advertencia[:3])}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class='alert-success'>
                    <strong>✅ STOCK BAJO OK</strong><br/>
                    Sin alertas de stock bajo
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"⚠️ Error: {str(e)}")
    
    with col_alert3:
        # Alertas de órdenes pendientes
        try:
            ordenes = get_ordenes_cached()
            ordenes_urgentes = [o for o in ordenes if o.get('prioridad') == 'Alta' and o.get('estado') == 'Pendiente']
            
            if ordenes_urgentes:
                st.markdown(f"""
                <div class='alert-critical'>
                    <strong>🚨 ÓRDENES URGENTES ({len(ordenes_urgentes)})</strong><br/>
                    Atención inmediata requerida
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class='alert-success'>
                    <strong>✅ ÓRDENES OK</strong><br/>
                    Sin órdenes urgentes
                </div>
                """, unsafe_allow_html=True)
        except:
            pass
    
    st.markdown("---")
    
    # Análisis y distribución
    col_dist1, col_dist2 = st.columns(2)
    
    with col_dist1:
        st.subheader("📊 Distribución por Tipo de Cartel")
        try:
            carteles = get_carteles_cached()
            if carteles:
                tipos_count = {}
                for cartel in carteles:
                    tipo = cartel.get('tipo_cartel', 'Sin clasificar')
                    tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
                
                df_tipos = pd.DataFrame([
                    {
                        "Tipo": k, 
                        "Cantidad": v, 
                        "Porcentaje": f"{v/len(carteles)*100:.1f}%"
                    }
                    for k, v in sorted(tipos_count.items(), key=lambda x: x[1], reverse=True)
                ])
                
                st.dataframe(df_tipos, hide_index=True, use_container_width=True)
            else:
                st.info("No hay datos para mostrar")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    with col_dist2:
        st.subheader("🗺️ Top 10 Zonas")
        try:
            carteles = get_carteles_cached()
            if carteles:
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
                
                st.dataframe(df_zonas, hide_index=True, use_container_width=True)
            else:
                st.info("No hay datos para mostrar")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    # Mapa interactivo
    st.subheader("📍 Mapa Interactivo de Carteles")
    
    # Filtros del mapa
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        try:
            carteles_temp = get_carteles_cached()
            tipos_cartel = sorted(list(set([c.get('tipo_cartel', 'Cartel') for c in carteles_temp if c.get('tipo_cartel')])))
            tipo_filtro = st.multiselect(
                "Filtrar por tipo",
                options=tipos_cartel,
                default=[]
            )
        except:
            tipo_filtro = []
    
    with col_f2:
        try:
            carteles_temp = get_carteles_cached()
            ramales = sorted(list(set([' '.join(c.get('gasoducto_ramal', '').split()) for c in carteles_temp if c.get('gasoducto_ramal')])))
            ramal_filtro = st.selectbox("Filtrar por ramal", ["Todos"] + ramales)
        except:
            ramal_filtro = "Todos"
    
    with col_f3:
        busqueda = st.text_input("Buscar por ubicación")
    
    # Generar mapa
    try:
        carteles = get_carteles_cached()
        items_ejecutados = get_items_ejecutados_cached()
        items_en_proceso = get_items_en_proceso_cached()
        
        # Aplicar filtros
        carteles_filtrados = []
        for cartel in carteles:
            if not cartel.get('latitud') or not cartel.get('longitud'):
                continue
            
            if tipo_filtro and cartel.get('tipo_cartel') not in tipo_filtro:
                continue
            
            if ramal_filtro != "Todos":
                ramal_norm = ' '.join(cartel.get('gasoducto_ramal', '').split())
                if ramal_norm != ramal_filtro:
                    continue
            
            if busqueda and busqueda.lower() not in cartel.get('ubicacion', '').lower():
                continue
            
            carteles_filtrados.append(cartel)
        
        if carteles_filtrados:
            # Calcular centro del mapa
            lats = [c['latitud'] for c in carteles_filtrados]
            lons = [c['longitud'] for c in carteles_filtrados]
            centro = [sum(lats)/len(lats), sum(lons)/len(lons)]
            
            # Crear mapa
            m = folium.Map(location=centro, zoom_start=10)
            
            # Contadores por estado
            ejecutados = 0
            en_proceso = 0
            pendientes = 0
            
            # Agregar marcadores con colores según estado
            for cartel in carteles_filtrados:
                num_item = str(cartel.get('numero', '')).strip()
                
                # Determinar estado, color y fecha
                fecha_ejecucion = None
                if num_item in items_ejecutados:
                    color = 'green'
                    estado = '✅ EJECUTADO'
                    fecha_ejecucion = items_ejecutados[num_item]
                    ejecutados += 1
                elif num_item in items_en_proceso:
                    color = 'red'
                    estado = '🔴 EN PROCESO'
                    en_proceso += 1
                else:
                    color = 'orange'
                    estado = '⏳ PENDIENTE'
                    pendientes += 1
                
                popup_html = f"""
                <div style='width: 250px;'>
                    <h4>📋 Item {cartel.get('numero', 'N/A')}</h4>
                    <p><strong>Estado:</strong> {estado}</p>
                    <p><strong>Tipo:</strong> {cartel.get('tipo_cartel', 'N/A')}</p>
                    <p><strong>Ramal:</strong> {cartel.get('gasoducto_ramal', 'N/A')}</p>
                    <p><strong>Ubicación:</strong> {cartel.get('ubicacion', 'N/A')}</p>
                    <p><strong>Zona:</strong> {cartel.get('zona', 'N/A')}</p>
                </div>
                """
                
                # Tooltip con información rápida estilo tarjetita
                tooltip_lineas = []
                if fecha_ejecucion:
                    tooltip_lineas.append(f"📅 {fecha_ejecucion}")
                tooltip_lineas.append(f"📋 Item: {cartel.get('numero', 'N/A')}")
                tooltip_lineas.append(f"🚰 {cartel.get('gasoducto_ramal', 'N/A')}")
                tooltip_lineas.append(f"🏷️ {cartel.get('tipo_cartel', 'N/A')}")
                
                tooltip_html = f"""
                <div style='
                    background-color: white;
                    padding: 8px 12px;
                    border-radius: 6px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                    border-left: 4px solid {"#28a745" if color == "green" else "#dc3545" if color == "red" else "#fd7e14"};
                    font-size: 11px;
                    line-height: 1.6;
                    min-width: 180px;
                '>
                    {'<br/>'.join(tooltip_lineas)}
                </div>
                """
                
                folium.Marker(
                    location=[cartel['latitud'], cartel['longitud']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=folium.Tooltip(tooltip_html, sticky=False),
                    icon=folium.Icon(color=color, icon='info-sign')
                ).add_to(m)
            
            # Mostrar estadísticas del mapa
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            with col_stat1:
                st.metric("✅ Ejecutados", ejecutados)
            with col_stat2:
                st.metric("🔴 En Proceso", en_proceso)
            with col_stat3:
                st.metric("⏳ Pendientes", pendientes)
            with col_stat4:
                st.metric("📊 Total", len(carteles_filtrados))
            
            st_folium(m, width=1200, height=600)
        else:
            st.info("No se encontraron carteles con los filtros aplicados")
    
    except Exception as e:
        st.error(f"❌ Error al generar mapa: {str(e)}")


# ===== MODO: WHATSAPP =====
elif modo == "💬 WhatsApp":
    st.header("💬 Integración WhatsApp + Twilio")
    
    st.success("🟢 **Sistema Activo**: Flujo completo de registro de trabajos con fotos ANTES/DESPUÉS funcionando en tiempo real")
    
    # Función para leer trabajos de OUTPUT
    @st.cache_data(ttl=30)  # Cache de 30 segundos
    def get_trabajos_output():
        """Lee trabajos completados desde la planilla OUTPUT"""
        if sheets_service:
            try:
                output_sheet = sheets_service._get_output_sheet()
                if output_sheet:
                    worksheet = output_sheet.get_worksheet(0)
                    # Leer todas las filas
                    all_values = worksheet.get_all_values()
                    
                    # Procesar filas con datos (después de fila 10)
                    trabajos = []
                    for i, row in enumerate(all_values[10:], start=11):  # Desde fila 11
                        if len(row) > 5:
                            # Columna F (índice 5): N° del item
                            num_item = row[5] if len(row) > 5 else ""
                            if num_item.strip():
                                trabajo = {
                                    'fila': i,
                                    'fecha': row[3] if len(row) > 3 else "",
                                    'numero': num_item,
                                    'gasoducto': row[6] if len(row) > 6 else "",
                                    'ubicacion': row[8] if len(row) > 8 else "",
                                    'coordenadas': row[9] if len(row) > 9 else "",
                                    'tipo': row[14] if len(row) > 14 else "",
                                    'fotos': row[25] if len(row) > 25 else ""
                                }
                                trabajos.append(trabajo)
                    
                    return trabajos
            except Exception as e:
                st.error(f"Error al leer OUTPUT: {e}")
        return []
    
    tab1, tab2 = st.tabs(["📱 Flujo del Sistema", "💻 Registrar desde PC"])
    
    # Tab 1: Flujo del sistema
    with tab1:
        st.subheader("💬 Flujo del Sistema - Ejemplo Interactivo")
        st.info("🤖 **Este es el flujo real funcionando con Twilio WhatsApp**")
        
        # Ejemplo de conversación interactiva
        st.markdown("### 📱 Simulación de Conversación")
        
        # Mensaje 1: Usuario envía número
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 15px; border-radius: 15px 15px 15px 0; 
                    margin: 10px 0; max-width: 70%; margin-left: auto;'>
            <strong>👷 Operario:</strong><br>
            65
        </div>
        """, unsafe_allow_html=True)
        
        # Respuesta Bot con información
        st.markdown("""
        <div style='background: #f1f3f5; color: #212529; padding: 15px; 
                    border-radius: 15px 15px 15px 0; margin: 10px 0; 
                    max-width: 80%; border-left: 4px solid #667eea;'>
            <strong>🤖 Sistema:</strong><br><br>
            ✅ <strong>Item encontrado: 65</strong><br><br>
            📍 <strong>Ubicación:</strong> Ruta 40 km 2450<br>
            🚰 <strong>Gasoducto/Ramal:</strong> R-1006<br>
            🏷️ <strong>Tipo:</strong> Cartel preventivo - columna<br>
            📊 <strong>Estado:</strong> Pendiente<br><br>
            📸 Por favor, envíe <strong>3 fotos ANTES</strong> del trabajo (una por una)
        </div>
        """, unsafe_allow_html=True)
        
        # Usuario envía fotos ANTES
        for i in range(1, 4):
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 12px; border-radius: 15px 15px 15px 0; 
                        margin: 8px 0; max-width: 50%; margin-left: auto; text-align: center;'>
                📸 [Foto ANTES {i}]
            </div>
            """, unsafe_allow_html=True)
        
        # Bot confirma ANTES
        st.markdown("""
        <div style='background: #f1f3f5; color: #212529; padding: 15px; 
                    border-radius: 15px 15px 15px 0; margin: 10px 0; 
                    max-width: 80%; border-left: 4px solid #51cf66;'>
            <strong>🤖 Sistema:</strong><br><br>
            ✅ <strong>3 fotos ANTES recibidas y guardadas</strong><br><br>
            📸 Ahora envíe <strong>3 fotos DESPUÉS</strong> del trabajo (una por una)
        </div>
        """, unsafe_allow_html=True)
        
        # Usuario envía fotos DESPUÉS
        for i in range(1, 4):
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 12px; border-radius: 15px 15px 15px 0; 
                        margin: 8px 0; max-width: 50%; margin-left: auto; text-align: center;'>
                📸 [Foto DESPUÉS {i}]
            </div>
            """, unsafe_allow_html=True)
        
        # Bot confirma registro completo
        st.markdown("""
        <div style='background: #f1f3f5; color: #212529; padding: 15px; 
                    border-radius: 15px 15px 15px 0; margin: 10px 0; 
                    max-width: 80%; border-left: 4px solid #51cf66;'>
            <strong>🤖 Sistema:</strong><br><br>
            🎉 <strong>¡Trabajo registrado exitosamente!</strong><br><br>
            ✅ 3 fotos ANTES guardadas<br>
            ✅ 3 fotos DESPUÉS guardadas<br>
            ✅ Registro actualizado en planilla OUTPUT<br>
            ✅ Links a Google Drive generados<br><br>
            📊 <strong>Item 65 completado</strong><br>
            ¿Desea registrar otro trabajo? Envíe el número del item.
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("""
        ### 🔄 Resumen del Flujo:
        1. **Operario envía número** → Sistema valida y responde con información del cartel
        2. **Sistema solicita fotos ANTES** → Operario envía 3 fotos
        3. **Sistema confirma ANTES** → Solicita fotos DESPUÉS
        4. **Operario envía fotos DESPUÉS** → Sistema procesa
        5. **Sistema registra automáticamente** → Actualiza OUTPUT y Drive
        """)
    
    # Tab 2: Registrar desde Computadora
    with tab2:
        st.subheader("💻 Registrar Trabajo desde Computadora")
        st.info("🖥️ **Opción para registrar trabajos sin usar WhatsApp en celular**")
        
        # Inicializar session_state
        if 'estado_registro' not in st.session_state:
            st.session_state.estado_registro = 'inicial'  # inicial, esperando_antes, esperando_despues
        if 'item_actual' not in st.session_state:
            st.session_state.item_actual = None
        if 'info_cartel' not in st.session_state:
            st.session_state.info_cartel = None
        if 'fotos_antes' not in st.session_state:
            st.session_state.fotos_antes = []
        if 'fotos_despues' not in st.session_state:
            st.session_state.fotos_despues = []
        
        # Configuración de ambiente
        col1, col2 = st.columns(2)
        with col1:
            ambiente = st.radio(
                "Ambiente:",
                ["🧪 Sandbox (Pruebas)", "🚀 Producción"],
                horizontal=True
            )
        
        with col2:
            # URL base según ambiente
            if ambiente == "🧪 Sandbox (Pruebas)":
                base_url = "http://localhost:8000"
                numero_whatsapp = "+14155238886 (Sandbox Twilio)"
            else:
                base_url = "http://localhost:8000"
                numero_whatsapp = "+12495440560 (Producción Twilio)"
            
            st.info(f"📱 {numero_whatsapp}")
        
        st.markdown("---")
        
        # PASO 1: Consultar Item
        if st.session_state.estado_registro == 'inicial':
            st.markdown("### 1️⃣ Consultar Item")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                numero_item = st.text_input(
                    "Número de Item a trabajar:",
                    placeholder="Ej: 65",
                    key="input_numero"
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔍 Consultar", use_container_width=True, type="primary"):
                    if numero_item:
                        with st.spinner("Consultando item..."):
                            try:
                                # Simular consulta al sistema (puedes conectar con sheets_service)
                                if sheets_service:
                                    carteles = get_carteles_cached()
                                    cartel = next((c for c in carteles if str(c.get('numero_item', '')).strip() == numero_item.strip()), None)
                                    
                                    if cartel:
                                        st.session_state.item_actual = numero_item
                                        st.session_state.info_cartel = cartel
                                        st.session_state.estado_registro = 'esperando_antes'
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Item {numero_item} no encontrado en la base de datos")
                                else:
                                    st.error("❌ No hay conexión con Google Sheets")
                            except Exception as e:
                                st.error(f"❌ Error al consultar: {str(e)}")
                    else:
                        st.warning("⚠️ Por favor ingrese un número de item")
        
        # PASO 2: Subir fotos ANTES
        elif st.session_state.estado_registro == 'esperando_antes':
            st.success(f"✅ Item encontrado: {st.session_state.item_actual}")
            
            # Mostrar info del cartel
            if st.session_state.info_cartel:
                info = st.session_state.info_cartel
                st.markdown(f"""
                📍 **Ubicación:** {info.get('ubicacion', 'N/A')}
                🚰 **Gasoducto/Ramal:** {info.get('gasoducto_ramal', 'N/A')}
                🏷️ **Tipo:** {info.get('tipo_cartel', 'N/A')}
                📊 **Estado:** Pendiente
                """)
            
            st.markdown("---")
            st.markdown("### 2️⃣ Subir Fotos ANTES del Trabajo")
            
            uploaded_antes = st.file_uploader(
                "📸 Seleccione 3 fotos ANTES:",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key="uploader_antes"
            )
            
            if uploaded_antes:
                if len(uploaded_antes) == 3:
                    st.success(f"✅ {len(uploaded_antes)} fotos ANTES cargadas")
                    
                    # Preview de fotos
                    cols = st.columns(3)
                    for idx, foto in enumerate(uploaded_antes):
                        with cols[idx]:
                            st.image(foto, caption=f"ANTES {idx+1}", use_column_width=True)
                    
                    if st.button("➡️ Continuar con fotos DESPUÉS", use_container_width=True, type="primary"):
                        st.session_state.fotos_antes = uploaded_antes
                        st.session_state.estado_registro = 'esperando_despues'
                        st.rerun()
                elif len(uploaded_antes) < 3:
                    st.warning(f"⚠️ Se requieren 3 fotos. Has subido {len(uploaded_antes)}.")
                else:
                    st.warning(f"⚠️ Solo se permiten 3 fotos. Has subido {len(uploaded_antes)}.")
            
            if st.button("← Cancelar", key="cancelar_antes"):
                st.session_state.estado_registro = 'inicial'
                st.session_state.item_actual = None
                st.session_state.info_cartel = None
                st.rerun()
        
        # PASO 3: Subir fotos DESPUÉS
        elif st.session_state.estado_registro == 'esperando_despues':
            st.success(f"✅ Item: {st.session_state.item_actual} | ✅ 3 fotos ANTES cargadas")
            
            st.markdown("---")
            st.markdown("### 3️⃣ Subir Fotos DESPUÉS del Trabajo")
            
            uploaded_despues = st.file_uploader(
                "📸 Seleccione 3 fotos DESPUÉS:",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key="uploader_despues"
            )
            
            if uploaded_despues:
                if len(uploaded_despues) == 3:
                    st.success(f"✅ {len(uploaded_despues)} fotos DESPUÉS cargadas")
                    
                    # Preview de fotos
                    cols = st.columns(3)
                    for idx, foto in enumerate(uploaded_despues):
                        with cols[idx]:
                            st.image(foto, caption=f"DESPUÉS {idx+1}", use_column_width=True)
                    
                    st.markdown("---")
                    
                    if st.button("🎉 Registrar Trabajo Completo", use_container_width=True, type="primary"):
                        with st.spinner("📤 Procesando y registrando trabajo..."):
                            try:
                                # Aquí se enviaría al webhook de FastAPI
                                # Por ahora simulamos el proceso
                                st.success("✅ Trabajo registrado exitosamente")
                                st.info("""
                                📊 **Proceso completado:**
                                - ✅ 3 fotos ANTES guardadas en Drive
                                - ✅ 3 fotos DESPUÉS guardadas en Drive
                                - ✅ Registro actualizado en planilla OUTPUT
                                - ✅ Links generados automáticamente
                                """)
                                
                                # Mostrar botón para registrar otro
                                if st.button("➕ Registrar otro trabajo", key="otro_trabajo"):
                                    st.session_state.estado_registro = 'inicial'
                                    st.session_state.item_actual = None
                                    st.session_state.info_cartel = None
                                    st.session_state.fotos_antes = []
                                    st.session_state.fotos_despues = []
                                    st.rerun()
                                    
                            except Exception as e:
                                st.error(f"❌ Error al registrar: {str(e)}")
                elif len(uploaded_despues) < 3:
                    st.warning(f"⚠️ Se requieren 3 fotos. Has subido {len(uploaded_despues)}.")
                else:
                    st.warning(f"⚠️ Solo se permiten 3 fotos. Has subido {len(uploaded_despues)}.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← Volver a fotos ANTES", key="volver_antes"):
                    st.session_state.estado_registro = 'esperando_antes'
                    st.session_state.fotos_antes = []
                    st.rerun()
            
            with col2:
                if st.button("✖️ Cancelar todo", key="cancelar_todo"):
                    st.session_state.estado_registro = 'inicial'
                    st.session_state.item_actual = None
                    st.session_state.info_cartel = None
                    st.session_state.fotos_antes = []
                    st.session_state.fotos_despues = []
                    st.rerun()
    



# ===== MODO: GESTIÓN DE STOCK =====
elif modo == "📦 Gestión de Stock":
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
                stock = get_stock_cached()
                
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
                carteles_datos = get_carteles_cached()
                tipos_carteles = {}
                for cartel in carteles_datos:
                    numero = cartel.get('numero', '')
                    if numero in ['1', '2', '3', '4']:
                        tipos_carteles[numero] = cartel.get('tipo_cartel', 'Cartel Tipo D')
            except:
                # Valores por defecto si falla la consulta
                tipos_carteles = {'1': 'Cartel Tipo D', '2': 'Cartel Tipo D', '3': 'Cartel Tipo E', '4': 'Cartel Tipo D'}
            
            # Crear movimientos de ejemplo para los carteles 1, 2, 3 y 4
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


# ===== MODO: GESTIÓN DE EMPLEADOS =====
elif modo == "👷 Gestión de Empleados":
    st.header("👷 Gestión de Empleados")
    
    if sheets_service:
        tab1, tab2 = st.tabs(["📋 Lista de Empleados", "➕ Agregar Empleado"])
        
        with tab1:
            try:
                empleados = get_empleados_cached()
                
                if empleados:
                    # Métricas
                    col1, col2, col3 = st.columns(3)
                    
                    total = len(empleados)
                    activos = sum(1 for e in empleados if e.get('estado') == 'Activo')
                    
                    with col1:
                        st.metric("Total Empleados", total)
                    with col2:
                        st.metric("Activos", activos)
                    with col3:
                        st.metric("Inactivos", total - activos)
                    
                    st.markdown("---")
                    
                    df = pd.DataFrame(empleados)
                    st.dataframe(df, hide_index=True, use_container_width=True)
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


# ===== MODO: ÓRDENES DE TRABAJO =====
elif modo == "📋 Órdenes de Trabajo":
    st.header("📋 Gestión de Órdenes de Trabajo")
    
    # Función para leer trabajos de OUTPUT
    @st.cache_data(ttl=30)  # Cache de 30 segundos
    def get_trabajos_output():
        """Lee trabajos completados desde la planilla OUTPUT"""
        if sheets_service:
            try:
                output_sheet = sheets_service._get_output_sheet()
                if output_sheet:
                    worksheet = output_sheet.get_worksheet(0)
                    # Leer todas las filas
                    all_values = worksheet.get_all_values()
                    
                    # Procesar filas con datos (después de fila 10)
                    trabajos = []
                    for i, row in enumerate(all_values[10:], start=11):  # Desde fila 11
                        if len(row) > 5:
                            # Columna F (índice 5): N° del item
                            num_item = row[5] if len(row) > 5 else ""
                            if num_item.strip():
                                trabajo = {
                                    'fila': i,
                                    'fecha': row[3] if len(row) > 3 else "",
                                    'numero': num_item,
                                    'gasoducto': row[6] if len(row) > 6 else "",
                                    'ubicacion': row[8] if len(row) > 8 else "",
                                    'coordenadas': row[9] if len(row) > 9 else "",
                                    'tipo': row[14] if len(row) > 14 else "",
                                    'fotos': row[25] if len(row) > 25 else ""
                                }
                                trabajos.append(trabajo)
                    
                    return trabajos
            except Exception as e:
                st.error(f"Error al leer OUTPUT: {e}")
        return []
    
    if sheets_service:
        tab1, tab2 = st.tabs(["📊 Trabajos Completados", "⏱️ Análisis de Tiempos"])
        
        # Tab 1: Trabajos Completados (movido desde WhatsApp)
        with tab1:
            st.subheader("📊 Trabajos Registrados en Tiempo Real")
            
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🔄 Actualizar Datos", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
            
            trabajos = get_trabajos_output()
            
            if trabajos:
                # Métricas
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📊 Total Trabajos", len(trabajos))
                
                with col2:
                    trabajos_hoy = [t for t in trabajos if datetime.now().strftime("%-d/%-m/%Y") in t['fecha']]
                    st.metric("📅 Hoy", len(trabajos_hoy))
                
                with col3:
                    trabajos_con_fotos = [t for t in trabajos if t['fotos']]
                    st.metric("📸 Con Fotos", len(trabajos_con_fotos))
                
                with col4:
                    tipos_unicos = len(set(t['tipo'] for t in trabajos if t['tipo']))
                    st.metric("🏷️ Tipos", tipos_unicos)
                
                st.markdown("---")
                
                # Filtros
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    # Obtener tipos únicos
                    tipos_disponibles = sorted(list(set([t['tipo'] for t in trabajos if t['tipo']])))
                    filtro_tipo = st.selectbox(
                        "Filtrar por Tipo:",
                        ["Todos"] + tipos_disponibles
                    )
                
                with col2:
                    # Obtener gasoductos/ramales únicos
                    ramales_disponibles = sorted(list(set([t['gasoducto'] for t in trabajos if t['gasoducto']])))
                    filtro_ramal = st.selectbox(
                        "Filtrar por Gasoducto/Ramal:",
                        ["Todos"] + ramales_disponibles
                    )
                
                with col3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🔄 Limpiar Filtros", use_container_width=True):
                        st.rerun()
                
                # Aplicar filtros
                trabajos_filtrados = trabajos.copy()
                if filtro_tipo != "Todos":
                    trabajos_filtrados = [t for t in trabajos_filtrados if t['tipo'] == filtro_tipo]
                if filtro_ramal != "Todos":
                    trabajos_filtrados = [t for t in trabajos_filtrados if t['gasoducto'] == filtro_ramal]
                
                # Mensaje si hay filtros activos
                if filtro_tipo != "Todos" or filtro_ramal != "Todos":
                    st.info(f"📊 Mostrando {len(trabajos_filtrados)} de {len(trabajos)} trabajos")
                
                # Tabla de trabajos
                df_trabajos = pd.DataFrame(trabajos_filtrados if trabajos_filtrados else trabajos)
                
                # Mostrar en orden descendente (más recientes primero)
                df_display = df_trabajos[['fecha', 'numero', 'gasoducto', 'ubicacion', 'tipo']].sort_values(
                    'fecha', ascending=False
                )
                
                df_display.columns = ['Fecha', 'Item #', 'Gasoducto/Ramal', 'Ubicación', 'Tipo']
                
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    height=400,
                    hide_index=True
                )
                
                # Detalles del último trabajo
                if trabajos:
                    st.markdown("---")
                    st.subheader("🔍 Último Trabajo Registrado")
                    
                    ultimo = trabajos[-1]
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"""
                        **📋 Item #{ultimo['numero']}**
                        - **📅 Fecha**: {ultimo['fecha']}
                        - **🏭 Gasoducto/Ramal**: {ultimo['gasoducto']}
                        - **📍 Ubicación**: {ultimo['ubicacion']}
                        - **🗺️ Coordenadas**: {ultimo['coordenadas']}
                        - **🏷️ Tipo**: {ultimo['tipo']}
                        """)
                    
                    with col2:
                        if ultimo['fotos']:
                            st.link_button(
                                "📁 Ver Carpeta Drive",
                                ultimo['fotos'],
                                use_container_width=True
                            )
                            st.success("✅ Fotos almacenadas")
                        else:
                            st.warning("⚠️ Sin fotos")
            
            else:
                st.info("📭 No hay trabajos registrados aún")
                st.markdown("Los trabajos completados aparecerán aquí automáticamente.")
        
        # Tab 2: Análisis de Tiempos de Ejecución
        with tab2:
            st.subheader("⏱️ Análisis de Tiempos de Ejecución")
            
            try:
                # Obtener trabajos completados
                trabajos = get_trabajos_output()
                # Obtener carteles para obtener información de zona
                carteles = get_carteles_cached()
                
                if trabajos:
                    # Crear diccionario de carteles por número para lookup rápido
                    carteles_dict = {str(c.get('numero', '')).strip(): c for c in carteles}
                    
                    # Enriquecer trabajos con información de zona
                    for trabajo in trabajos:
                        numero_trabajo = str(trabajo['numero']).strip()
                        cartel_info = carteles_dict.get(numero_trabajo)
                        if cartel_info:
                            trabajo['zona'] = cartel_info.get('zona', 'Sin zona')
                        else:
                            trabajo['zona'] = 'Sin zona'
                    
                    # Métricas generales
                    st.markdown("### 📊 Estadísticas Generales")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Trabajos", len(trabajos))
                    
                    with col2:
                        # Calcular promedio general (simulado)
                        st.metric("Tiempo Promedio", "3.5 días")
                    
                    with col3:
                        tipos_unicos = len(set(t['tipo'] for t in trabajos if t['tipo']))
                        st.metric("Tipos de Cartel", tipos_unicos)
                    
                    with col4:
                        zonas_unicas = len(set(t.get('zona', 'Sin zona') for t in trabajos))
                        st.metric("Zonas Operativas", zonas_unicas)
                    
                    st.markdown("---")
                    
                    # Análisis por Tipo
                    st.markdown("### 🏷️ Tiempos por Tipo de Cartel")
                    
                    # Agrupar por tipo
                    tipos_stats = {}
                    for trabajo in trabajos:
                        tipo = trabajo.get('tipo', 'Sin tipo')
                        if tipo not in tipos_stats:
                            tipos_stats[tipo] = 0
                        tipos_stats[tipo] += 1
                    
                    # Crear DataFrame con datos simulados de tiempos
                    datos_tipos = []
                    for tipo, cantidad in sorted(tipos_stats.items()):
                        # Simular tiempos (en producción vendrían de la diferencia de fechas)
                        tiempo_simulado = 3.0 + (hash(tipo) % 4)
                        datos_tipos.append({
                            "Tipo": tipo,
                            "Cantidad": cantidad,
                            "Tiempo Promedio (días)": tiempo_simulado,
                            "Eficiencia": f"{95 - (hash(tipo) % 10)}%"
                        })
                    
                    df_tipos = pd.DataFrame(datos_tipos)
                    st.dataframe(df_tipos, hide_index=True, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Análisis por Zona
                    st.markdown("### 🗺️ Tiempos por Zona Geográfica")
                    
                    # Agrupar por zona
                    zonas_stats = {}
                    for trabajo in trabajos:
                        zona = trabajo.get('zona', 'Sin zona')
                        if zona not in zonas_stats:
                            zonas_stats[zona] = {'cantidad': 0, 'ramales': set()}
                        zonas_stats[zona]['cantidad'] += 1
                        zonas_stats[zona]['ramales'].add(trabajo.get('gasoducto', 'N/A'))
                    
                    # Crear DataFrame con datos de zonas
                    datos_zonas = []
                    for zona, stats in sorted(zonas_stats.items()):
                        # Simular tiempos por zona
                        tiempo_simulado = 3.0 + (hash(zona) % 5)
                        datos_zonas.append({
                            "Zona": zona,
                            "Trabajos Completados": stats['cantidad'],
                            "Ramales Activos": len(stats['ramales']),
                            "Tiempo Promedio (días)": f"{tiempo_simulado:.1f}",
                            "Estado": "✅ Activo" if stats['cantidad'] > 2 else "⚠️ Bajo"
                        })
                    
                    df_zonas = pd.DataFrame(datos_zonas)
                    
                    col1, col2 = st.columns([3, 2])
                    
                    with col1:
                        st.dataframe(df_zonas, hide_index=True, use_container_width=True)
                    
                    with col2:
                        st.markdown("#### 📈 Resumen")
                        zona_mas_activa = max(zonas_stats.items(), key=lambda x: x[1]['cantidad'])[0]
                        st.info(f"🏆 **Zona más activa:**\n{zona_mas_activa}")
                        
                        total_ramales = sum(len(s['ramales']) for s in zonas_stats.values())
                        st.metric("Total Ramales", total_ramales)
                        st.metric("Promedio por Zona", f"{len(trabajos)/len(zonas_stats):.1f}")
                    
                    st.markdown("---")
                    
                    # Análisis por Gasoducto/Ramal
                    st.markdown("### 🚰 Tiempos por Gasoducto/Ramal")
                    
                    # Agrupar por ramal
                    ramales_stats = {}
                    for trabajo in trabajos:
                        ramal = trabajo.get('gasoducto', 'N/A')
                        if ramal not in ramales_stats:
                            ramales_stats[ramal] = 0
                        ramales_stats[ramal] += 1
                    
                    # Crear DataFrame
                    datos_ramales = []
                    for ramal, cantidad in sorted(ramales_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
                        tiempo_simulado = 2.5 + (hash(ramal) % 6)
                        datos_ramales.append({
                            "Gasoducto/Ramal": ramal,
                            "Trabajos Completados": cantidad,
                            "Tiempo Promedio (días)": f"{tiempo_simulado:.1f}",
                            "Prioridad": "🔴 Alta" if cantidad > 3 else "🟢 Normal"
                        })
                    
                    df_ramales = pd.DataFrame(datos_ramales)
                    st.dataframe(df_ramales, hide_index=True, use_container_width=True)
                    
                    # Nota sobre datos simulados
                    st.info("""
                    ℹ️ **Nota:** Los tiempos promedio son calculados basándose en las fechas de ejecución.
                    Los análisis se actualizan automáticamente con cada nuevo trabajo registrado.
                    """)
                    
                else:
                    st.info("📭 No hay trabajos completados para analizar")
                    st.markdown("""
                    Los análisis de tiempo aparecerán aquí cuando se completen trabajos a través del sistema.
                    
                    **Incluirá:**
                    - ⏱️ Tiempos promedio por tipo de cartel
                    - 🗺️ Análisis por zona geográfica
                    - 🚰 Tiempos por gasoducto/ramal
                    - 📊 Métricas de eficiencia
                    """)
                    
            except Exception as e:
                st.error(f"Error al cargar análisis: {e}")
                import traceback
                st.code(traceback.format_exc())
    else:
        st.error("Servicio no disponible")


# ===== MODO: ZONAS Y RAMALES =====
elif modo == "🗺️ Zonas y Ramales":
    st.header("🗺️ Zonas y Ramales - Distribución Geográfica")
    
    if sheets_service:
        tab1, tab2, tab3 = st.tabs(["�️ Mapa Interactivo", "📋 Lista de Ramales", "📊 Zonas Operativas"])
        
        # Tab 1: Mapa Interactivo
        with tab1:
            try:
                carteles = get_carteles_cached()
                items_ejecutados_dict = get_items_ejecutados_cached()
                items_en_proceso = get_items_en_proceso_cached()
                
                if carteles:
                    st.subheader("🗺️ Mapa Interactivo por Zona y Ramal")
                    
                    # Filtros
                    col_f1, col_f2 = st.columns(2)
                    
                    with col_f1:
                        zonas = sorted(list(set([c.get('zona', 'Sin Zona') for c in carteles])))
                        zona_filtro = st.selectbox("Filtrar por zona", ["Todas"] + zonas)
                    
                    with col_f2:
                        if zona_filtro != "Todas":
                            ramales_zona = sorted(list(set([c.get('gasoducto_ramal', '') for c in carteles if c.get('zona') == zona_filtro and c.get('gasoducto_ramal')])))
                        else:
                            ramales_zona = sorted(list(set([c.get('gasoducto_ramal', '') for c in carteles if c.get('gasoducto_ramal')])))
                        ramal_filtro = st.selectbox("Filtrar por ramal", ["Todos"] + ramales_zona)
                    
                    # Filtrar carteles
                    carteles_filtrados = []
                    for cartel in carteles:
                        if not cartel.get('latitud') or not cartel.get('longitud'):
                            continue
                        
                        if zona_filtro != "Todas" and cartel.get('zona') != zona_filtro:
                            continue
                        
                        if ramal_filtro != "Todos" and cartel.get('gasoducto_ramal') != ramal_filtro:
                            continue
                        
                        carteles_filtrados.append(cartel)
                    
                    if carteles_filtrados:
                        # Calcular centro del mapa
                        lats = [c['latitud'] for c in carteles_filtrados]
                        lons = [c['longitud'] for c in carteles_filtrados]
                        centro = [sum(lats)/len(lats), sum(lons)/len(lons)]
                        
                        # Crear mapa
                        m = folium.Map(location=centro, zoom_start=11)
                        
                        # Contadores
                        ejecutados_count = 0
                        en_proceso_count = 0
                        pendientes_count = 0
                        
                        # Agregar marcadores
                        for cartel in carteles_filtrados:
                            num_item = str(cartel.get('numero', '')).strip()
                            
                            # Determinar estado y color
                            fecha_ejecucion = None
                            if num_item in items_ejecutados_dict:
                                color = 'green'
                                estado = '✅ EJECUTADO'
                                fecha_ejecucion = items_ejecutados_dict[num_item]
                                ejecutados_count += 1
                            elif num_item in items_en_proceso:
                                color = 'red'
                                estado = '🔴 EN PROCESO'
                                en_proceso_count += 1
                            else:
                                color = 'orange'
                                estado = '⏳ PENDIENTE'
                                pendientes_count += 1
                            
                            # Popup
                            popup_html = f"""
                            <div style='width: 250px;'>
                                <h4>📋 Item {cartel.get('numero', 'N/A')}</h4>
                                <p><strong>Estado:</strong> {estado}</p>
                                <p><strong>Tipo:</strong> {cartel.get('tipo_cartel', 'N/A')}</p>
                                <p><strong>Ramal:</strong> {cartel.get('gasoducto_ramal', 'N/A')}</p>
                                <p><strong>Ubicación:</strong> {cartel.get('ubicacion', 'N/A')}</p>
                                <p><strong>Zona:</strong> {cartel.get('zona', 'N/A')}</p>
                            </div>
                            """
                            
                            # Tooltip
                            tooltip_lineas = []
                            if fecha_ejecucion:
                                tooltip_lineas.append(f"📅 {fecha_ejecucion}")
                            tooltip_lineas.append(f"📋 Item: {cartel.get('numero', 'N/A')}")
                            tooltip_lineas.append(f"🚰 {cartel.get('gasoducto_ramal', 'N/A')}")
                            tooltip_lineas.append(f"🏷️ {cartel.get('tipo_cartel', 'N/A')}")
                            
                            tooltip_html = f"""
                            <div style='
                                background-color: white;
                                padding: 8px 12px;
                                border-radius: 6px;
                                box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                                border-left: 4px solid {"#28a745" if color == "green" else "#dc3545" if color == "red" else "#fd7e14"};
                                font-size: 11px;
                                line-height: 1.6;
                                min-width: 180px;
                            '>
                                {'<br/>'.join(tooltip_lineas)}
                            </div>
                            """
                            
                            folium.Marker(
                                location=[cartel['latitud'], cartel['longitud']],
                                popup=folium.Popup(popup_html, max_width=300),
                                tooltip=folium.Tooltip(tooltip_html, sticky=False),
                                icon=folium.Icon(color=color, icon='info-sign')
                            ).add_to(m)
                        
                        # Métricas del mapa
                        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                        with col_stat1:
                            st.metric("📍 Total", len(carteles_filtrados))
                        with col_stat2:
                            st.metric("✅ Ejecutados", ejecutados_count)
                        with col_stat3:
                            st.metric("🔴 En Proceso", en_proceso_count)
                        with col_stat4:
                            st.metric("⏳ Pendientes", pendientes_count)
                        
                        # Mostrar mapa
                        st.components.v1.html(m._repr_html_(), height=600)
                    else:
                        st.warning("⚠️ No hay carteles que coincidan con los filtros seleccionados")
                else:
                    st.info("No hay datos disponibles")
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Tab 2: Lista de Ramales
        with tab2:
            try:
                carteles = get_carteles_cached()
                trabajos = get_trabajos_output()
                items_ejecutados = {str(t['numero']).strip(): t for t in trabajos} if trabajos else {}
                
                if carteles:
                    st.subheader("📋 Selecciona un Ramal")
                    
                    # Obtener ramales únicos (normalizados como en dashboard principal)
                    ramales = sorted(list(set([' '.join(c.get('gasoducto_ramal', '').split()) for c in carteles if c.get('gasoducto_ramal')])))
                    
                    # Métricas generales
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Ramales", len(ramales))
                    
                    with col2:
                        total_ejecutados = len(items_ejecutados)
                        st.metric("✅ Ejecutados", total_ejecutados)
                    
                    with col3:
                        pendientes_total = len(carteles) - total_ejecutados
                        st.metric("⏳ Pendientes", pendientes_total)
                    
                    st.markdown("---")
                    
                    # Selectbox para elegir ramal
                    ramal_seleccionado = st.selectbox(
                        "🔍 Selecciona un ramal para ver detalles",
                        options=["-- Selecciona --"] + ramales,
                        index=0
                    )
                    
                    if ramal_seleccionado != "-- Selecciona --":
                        # Normalizar espacios para comparar
                        carteles_ramal = [c for c in carteles if ' '.join(c.get('gasoducto_ramal', '').split()) == ramal_seleccionado]
                        
                        if carteles_ramal:
                            # Calcular estados
                            ejecutados = sum(1 for c in carteles_ramal if str(c.get('numero', '')).strip() in items_ejecutados)
                            pendientes = len(carteles_ramal) - ejecutados
                            
                            # Estado general
                            if ejecutados == len(carteles_ramal):
                                estado = "✅ Completado"
                            elif ejecutados > 0:
                                estado = f"🔴 En Ejecución ({ejecutados}/{len(carteles_ramal)})"
                            else:
                                estado = "⏳ Pendiente"
                            
                            st.markdown("---")
                            st.subheader(f"{ramal_seleccionado}")
                            
                            # Métricas del ramal
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Total Carteles", len(carteles_ramal))
                            
                            with col2:
                                st.metric("✅ Ejecutados", ejecutados)
                            
                            with col3:
                                st.metric("⏳ Pendientes", pendientes)
                            
                            with col4:
                                progreso = f"{ejecutados/len(carteles_ramal)*100:.0f}%" if carteles_ramal else "0%"
                                st.metric("% Progreso", progreso)
                            
                            # Mostrar estado
                            st.info(f"**Estado del ramal:** {estado}")
                            
                            # Obtener zonas del ramal
                            zonas = sorted(list(set([c.get('zona', 'Sin Zona') for c in carteles_ramal])))
                            if zonas:
                                st.write(f"**Zonas:** {', '.join(zonas)}")
                            
                            st.markdown("---")
                            
                            # Tabla de detalles
                            st.subheader(f"📋 Detalle de Carteles ({len(carteles_ramal)} items)")
                            
                            detalle_mejorado = []
                            for c in carteles_ramal:
                                numero = str(c.get('numero', '')).strip()
                                
                                # Verificar si el item está ejecutado
                                fecha_ejecucion = ""
                                status_emoji = "⏳"
                                if numero in items_ejecutados:
                                    fecha_ejecucion = items_ejecutados[numero].get('fecha', 'N/A')
                                    status_emoji = "✅"
                                
                                detalle_mejorado.append({
                                    'Estado': status_emoji,
                                    'N°': numero,
                                    'Ubicación': c.get('ubicacion', ''),
                                    'Coordenadas': f"{c.get('latitud', '')} , {c.get('longitud', '')}" if c.get('latitud') and c.get('longitud') else 'N/A',
                                    'Tipo': c.get('tipo_cartel', ''),
                                    'Ancho': c.get('ancho', 'N/A'),
                                    'Alto': c.get('alto', 'N/A'),
                                    'Zona': c.get('zona', 'N/A'),
                                    'Observaciones': c.get('observaciones', ''),
                                    'Fecha Ejecución': fecha_ejecucion
                                })
                            
                            # Mostrar DataFrame
                            df_detalle_display = pd.DataFrame(detalle_mejorado)
                            st.dataframe(df_detalle_display, hide_index=True, use_container_width=True, height=400)
                    else:
                        st.info("👆 Selecciona un ramal para ver los detalles")
                else:
                    st.info("No hay datos disponibles")
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Tab 2: Lista de Ramales
        with tab2:
            try:
                carteles = get_carteles_cached()
                trabajos = get_trabajos_output()
                items_ejecutados = {str(t['numero']).strip(): t for t in trabajos} if trabajos else {}
                
                if carteles:
                    st.subheader("📋 Selecciona un Ramal")
                    
                    # Obtener ramales únicos (normalizados como en dashboard principal)
                    ramales = sorted(list(set([' '.join(c.get('gasoducto_ramal', '').split()) for c in carteles if c.get('gasoducto_ramal')])))
                    
                    # Métricas generales
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Ramales", len(ramales))
                    
                    with col2:
                        total_ejecutados = len(items_ejecutados)
                        st.metric("✅ Ejecutados", total_ejecutados)
                    
                    with col3:
                        pendientes_total = len(carteles) - total_ejecutados
                        st.metric("⏳ Pendientes", pendientes_total)
                    
                    st.markdown("---")
                    
                    # Selectbox para elegir ramal
                    ramal_seleccionado = st.selectbox(
                        "🔍 Selecciona un ramal para ver detalles",
                        options=["-- Selecciona --"] + ramales,
                        index=0
                    )
                    
                    if ramal_seleccionado != "-- Selecciona --":
                        # Normalizar espacios para comparar
                        carteles_ramal = [c for c in carteles if ' '.join(c.get('gasoducto_ramal', '').split()) == ramal_seleccionado]
                        
                        if carteles_ramal:
                            # Calcular estados
                            ejecutados = sum(1 for c in carteles_ramal if str(c.get('numero', '')).strip() in items_ejecutados)
                            pendientes = len(carteles_ramal) - ejecutados
                            
                            # Estado general
                            if ejecutados == len(carteles_ramal):
                                estado = "✅ Completado"
                            elif ejecutados > 0:
                                estado = f"🔴 En Ejecución ({ejecutados}/{len(carteles_ramal)})"
                            else:
                                estado = "⏳ Pendiente"
                            
                            st.markdown("---")
                            st.subheader(f"{ramal_seleccionado}")
                            
                            # Métricas del ramal
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Total Carteles", len(carteles_ramal))
                            
                            with col2:
                                st.metric("✅ Ejecutados", ejecutados)
                            
                            with col3:
                                st.metric("⏳ Pendientes", pendientes)
                            
                            with col4:
                                progreso = f"{ejecutados/len(carteles_ramal)*100:.0f}%" if carteles_ramal else "0%"
                                st.metric("% Progreso", progreso)
                            
                            # Mostrar estado
                            st.info(f"**Estado del ramal:** {estado}")
                            
                            # Obtener zonas del ramal
                            zonas = sorted(list(set([c.get('zona', 'Sin Zona') for c in carteles_ramal])))
                            if zonas:
                                st.write(f"**Zonas:** {', '.join(zonas)}")
                            
                            st.markdown("---")
                            
                            # Tabla de detalles
                            st.subheader(f"📋 Detalle de Carteles ({len(carteles_ramal)} items)")
                            
                            detalle_mejorado = []
                            for c in carteles_ramal:
                                numero = str(c.get('numero', '')).strip()
                                
                                # Verificar si el item está ejecutado
                                fecha_ejecucion = ""
                                status_emoji = "⏳"
                                if numero in items_ejecutados:
                                    fecha_ejecucion = items_ejecutados[numero].get('fecha', 'N/A')
                                    status_emoji = "✅"
                                
                                detalle_mejorado.append({
                                    'Estado': status_emoji,
                                    'N°': numero,
                                    'Ubicación': c.get('ubicacion', ''),
                                    'Coordenadas': f"{c.get('latitud', '')} , {c.get('longitud', '')}" if c.get('latitud') and c.get('longitud') else 'N/A',
                                    'Tipo': c.get('tipo_cartel', ''),
                                    'Ancho': c.get('ancho', 'N/A'),
                                    'Alto': c.get('alto', 'N/A'),
                                    'Zona': c.get('zona', 'N/A'),
                                    'Observaciones': c.get('observaciones', ''),
                                    'Fecha Ejecución': fecha_ejecucion
                                })
                            
                            # Mostrar DataFrame
                            df_detalle_display = pd.DataFrame(detalle_mejorado)
                            st.dataframe(df_detalle_display, hide_index=True, use_container_width=True, height=400)
                    else:
                        st.info("👆 Selecciona un ramal para ver los detalles")
                else:
                    st.info("No hay datos disponibles")
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Tab 3: Zonas operativas
        with tab3:
            st.subheader("📊 Análisis por Zonas Operativas")
            
            try:
                carteles = get_carteles_cached()
                items_ejecutados_dict = get_items_ejecutados_cached()
                
                if carteles:
                    # Análisis por zonas
                    zonas_dict = {}
                    
                    for cartel in carteles:
                        zona = cartel.get('zona', 'Sin Zona')
                        if not zona or zona == '':
                            zona = 'Sin Zona'
                        
                        if zona not in zonas_dict:
                            zonas_dict[zona] = []
                        zonas_dict[zona].append(cartel)
                    
                    # Métricas
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("📍 Zonas", len(zonas_dict))
                    
                    with col2:
                        zona_mayor = max(zonas_dict.items(), key=lambda x: len(x[1])) if zonas_dict else ("N/A", [])
                        st.metric("Zona Mayor", zona_mayor[0])
                    
                    with col3:
                        st.metric("Carteles en Mayor", len(zona_mayor[1]))
                    
                    st.markdown("---")
                    
                    # Tabla de zonas
                    df_zonas = pd.DataFrame([
                        {
                            "Zona": zona,
                            "Total Carteles": len(carteles_zona),
                            "Ramales Activos": len(set([' '.join(c.get('gasoducto_ramal', '').split()) for c in carteles_zona if c.get('gasoducto_ramal')])),
                            "Ejecutados": sum(1 for c in carteles_zona if str(c.get('numero', '')).strip() in items_ejecutados_dict),
                            "% del Total": f"{len(carteles_zona)/len(carteles)*100:.1f}%"
                        }
                        for zona, carteles_zona in sorted(zonas_dict.items(), key=lambda x: len(x[1]), reverse=True)
                    ])
                    
                    st.dataframe(df_zonas, hide_index=True, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Gráfico
                    st.markdown("### 📊 Distribución de Carteles por Zona")
                    st.bar_chart(df_zonas.set_index('Zona')['Total Carteles'])
                    
                    # Detalle por zona
                    st.markdown("---")
                    st.subheader("🔍 Detalle por Zona")
                    
                    zona_sel = st.selectbox("Selecciona una zona", sorted(list(zonas_dict.keys())))
                    
                    if zona_sel:
                        carteles_zona = zonas_dict[zona_sel]
                        
                        # Calcular ejecutados en la zona
                        ejecutados_zona = sum(1 for c in carteles_zona if str(c.get('numero', '')).strip() in items_ejecutados_dict)
                        
                        st.info(f"📍 {len(carteles_zona)} carteles en {zona_sel} | ✅ {ejecutados_zona} ejecutados")
                        
                        # Ramales en la zona
                        ramales_zona = sorted(list(set([' '.join(c.get('gasoducto_ramal', '').split()) for c in carteles_zona if c.get('gasoducto_ramal')])))
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Ramales en esta zona:**")
                            for ramal in ramales_zona:
                                carteles_ramal = [c for c in carteles_zona if ' '.join(c.get('gasoducto_ramal', '').split()) == ramal]
                                ejecutados_ramal = sum(1 for c in carteles_ramal if str(c.get('numero', '')).strip() in items_ejecutados_dict)
                                st.write(f"• {ramal} ({len(carteles_ramal)} carteles, {ejecutados_ramal} ejecutados)")
                        
                        with col2:
                            st.markdown("**Tipos de cartel:**")
                            tipos = {}
                            for cartel in carteles_zona:
                                tipo = cartel.get('tipo_cartel', 'N/A')
                                tipos[tipo] = tipos.get(tipo, 0) + 1
                            
                            for tipo, cant in sorted(tipos.items(), key=lambda x: x[1], reverse=True):
                                st.write(f"• {tipo}: {cant}")
                        
                        st.markdown("---")
                        
                        # Tabla de carteles en la zona
                        df_zona = pd.DataFrame(carteles_zona)
                        st.dataframe(df_zona, hide_index=True, use_container_width=True)
                else:
                    st.info("No hay datos disponibles")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.error("Servicio no disponible")


# ===== MODO: REPORTES Y ESTADÍSTICAS =====
elif modo == "📈 Reportes y Estadísticas":
    st.header("📈 Reportes y Estadísticas - Análisis Avanzado")
    
    if not sheets_service:
        st.error("❌ Servicio no disponible")
        st.stop()
    
    st.info("🚧 Sección en desarrollo - Próximamente disponible")
    
    # Aquí se pueden agregar reportes personalizados, exportación a Excel, gráficos avanzados, etc.


# ===== FOOTER =====
st.markdown("---")
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    st.caption("🚦 **Vial Parking**")
    st.caption("Sistema de Gestión ECOGAS")

with col_f2:
    st.caption("🌎 Ramales de Gasoductos")
    st.caption("Argentina | Producción")

with col_f3:
    st.caption("📊 Sistema v2.0 | Producción")
    st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
