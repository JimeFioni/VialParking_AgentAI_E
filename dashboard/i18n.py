# -*- coding: utf-8 -*-
"""
Sistema de internacionalización (i18n) compartido para los dashboards de
Vial Parking (app.py, demo.py, production.py).

Uso básico:

    import i18n
    from i18n import t, language_selector, estado_label

    # En el sidebar, lo más arriba posible (después de set_page_config):
    language_selector()           # dibuja el selector ES / EN

    # En cualquier texto visible:
    st.title(t("app_title"))
    st.button(t("btn_update_stock"))
    st.success(t("login_welcome", user=username))   # con variables

Diseño:
- El idioma actual se guarda en st.session_state["lang"] ("es" | "en").
- t(key, **kwargs) busca la clave en TRANSLATIONS y la formatea con kwargs.
- Si una clave no existe, se devuelve la propia clave (fallback seguro: nunca
  rompe la app).
- Para widgets cuyo VALOR de retorno se usa en la lógica (selectbox, radio),
  NO se traduce el valor: se mantiene un código estable y se traduce solo lo
  que se muestra usando `format_func=...` con los helpers de este módulo.
"""

import streamlit as st

DEFAULT_LANG = "es"
SUPPORTED_LANGS = ("es", "en")


# ----------------------------------------------------------------------------
# Estado del idioma
# ----------------------------------------------------------------------------
def get_lang() -> str:
    """Idioma actual ('es' por defecto)."""
    lang = st.session_state.get("lang", DEFAULT_LANG)
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def t(key: str, **kwargs) -> str:
    """
    Traduce una clave al idioma actual.

    - Si la clave no está en el diccionario, devuelve la clave tal cual
      (fallback seguro).
    - kwargs se usan para interpolar variables: t("saludo", nombre="Jime").
    """
    lang = get_lang()
    entry = TRANSLATIONS.get(key)
    if entry is None:
        text = key
    else:
        text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text


def language_selector(container=None, label_visibility: str = "visible"):
    """
    Dibuja el selector de idioma (ES / EN) y deja el idioma elegido en
    st.session_state["lang"]. Llamar lo más arriba posible del sidebar.
    """
    c = container if container is not None else st.sidebar
    labels = {"es": "Español 🇪🇸", "en": "English 🇬🇧"}
    # La clave "lang" hace que Streamlit administre el valor en session_state.
    c.radio(
        t("language_label"),
        options=list(SUPPORTED_LANGS),
        format_func=lambda code: labels[code],
        horizontal=True,
        key="lang",
        label_visibility=label_visibility,
    )
    return get_lang()


# ----------------------------------------------------------------------------
# Helpers para valores con lógica estable (no se traduce el código, sólo la
# etiqueta visible). Pensados para usar como format_func de selectbox/radio.
# ----------------------------------------------------------------------------
def estado_label(code: str) -> str:
    """Etiqueta visible para los estados de cartel (código estable)."""
    mapping = {
        "Todos": t("estado_todos"),
        "para_reemplazar": t("estado_para_reemplazar"),
        "en_proceso": t("estado_en_proceso"),
        "reemplazado": t("estado_reemplazado"),
    }
    return mapping.get(code, code)


# ----------------------------------------------------------------------------
# Diccionario de traducciones
#   clave: {"es": "...", "en": "..."}
# ----------------------------------------------------------------------------
TRANSLATIONS = {
    # --- genéricas / comunes ---------------------------------------------
    "language_label": {"es": "🌐 Idioma / Language", "en": "🌐 Language / Idioma"},
    "estado_todos": {"es": "Todos", "en": "All"},
    "estado_para_reemplazar": {"es": "Para Reemplazar", "en": "To Replace"},
    "estado_en_proceso": {"es": "En Proceso", "en": "In Progress"},
    "estado_reemplazado": {"es": "Reemplazado", "en": "Replaced"},

    # --- app.py: cabecera / sidebar --------------------------------------
    "page_title": {"es": "Vial Parking - Dashboard", "en": "Vial Parking - Dashboard"},
    "app_title": {
        "es": "🚦 Vial Parking - Sistema de Gestión de Cartelería",
        "en": "🚦 Vial Parking - Road Signage Management System",
    },
    "sb_config": {"es": "⚙️ Configuración", "en": "⚙️ Settings"},
    "sb_filters": {"es": "Filtros", "en": "Filters"},
    "lbl_estado": {"es": "Estado", "en": "Status"},
    "lbl_operario": {"es": "Operario", "en": "Operator"},
    "lbl_desde": {"es": "Desde", "en": "From"},
    "lbl_hasta": {"es": "Hasta", "en": "To"},
    "sb_system_status": {"es": "📊 Estado del Sistema", "en": "📊 System Status"},
    "api_unavailable": {"es": "❌ API no disponible", "en": "❌ API unavailable"},

    # --- app.py: tabs ----------------------------------------------------
    "tab_map": {"es": "📍 Mapa", "en": "📍 Map"},
    "tab_stats": {"es": "📊 Estadísticas", "en": "📊 Statistics"},
    "tab_stock": {"es": "📦 Stock", "en": "📦 Stock"},
    "tab_records": {"es": "📋 Registros", "en": "📋 Records"},

    # --- app.py: mapa ----------------------------------------------------
    "map_header": {"es": "Mapa de Carteles", "en": "Signage Map"},
    "popup_operario": {"es": "Operario", "en": "Operator"},
    "popup_estado": {"es": "Estado", "en": "Status"},
    "popup_fecha": {"es": "Fecha", "en": "Date"},
    "popup_direccion": {"es": "Dirección", "en": "Address"},
    "legend_para_reemplazar": {"es": "🔴 **Para Reemplazar**", "en": "🔴 **To Replace**"},
    "legend_en_proceso": {"es": "🟠 **En Proceso**", "en": "🟠 **In Progress**"},
    "legend_reemplazado": {"es": "🟢 **Reemplazado**", "en": "🟢 **Replaced**"},
    "no_carteles_filtros": {
        "es": "No hay carteles registrados con los filtros seleccionados.",
        "en": "No signage found with the selected filters.",
    },

    # --- app.py: estadísticas -------------------------------------------
    "stats_header": {"es": "Estadísticas y Métricas", "en": "Statistics & Metrics"},
    "metric_total": {"es": "Total de Carteles", "en": "Total Signs"},
    "metric_para_reemplazar": {"es": "Para Reemplazar", "en": "To Replace"},
    "metric_en_proceso": {"es": "En Proceso", "en": "In Progress"},
    "metric_reemplazados": {"es": "Reemplazados", "en": "Replaced"},
    "chart_por_estado": {"es": "Carteles por Estado", "en": "Signs by Status"},
    "chart_por_operario": {"es": "Carteles por Operario", "en": "Signs by Operator"},
    "chart_acciones": {"es": "Acciones Más Frecuentes", "en": "Most Frequent Actions"},
    "no_datos_stats": {
        "es": "No hay datos para mostrar estadísticas.",
        "en": "No data available to show statistics.",
    },

    # --- app.py: stock ---------------------------------------------------
    "stock_header": {"es": "Gestión de Stock", "en": "Stock Management"},
    "stock_alertas": {
        "es": "⚠️ **{n} alertas de stock bajo**",
        "en": "⚠️ **{n} low-stock alerts**",
    },
    "stock_expander": {
        "es": "⚠️ {tipo} - {cant} unidades",
        "en": "⚠️ {tipo} - {cant} units",
    },
    "stock_umbral": {
        "es": "**Umbral configurado:** {n} unidades",
        "en": "**Configured threshold:** {n} units",
    },
    "stock_inventario": {"es": "Inventario Actual", "en": "Current Inventory"},
    "stock_col_tipo": {"es": "Tipo de Cartel", "en": "Sign Type"},
    "stock_col_cantidad": {"es": "Cantidad", "en": "Quantity"},
    "stock_col_estado": {"es": "Estado", "en": "Status"},
    "stock_bajo": {"es": "⚠️ Bajo", "en": "⚠️ Low"},
    "stock_ok": {"es": "✅ OK", "en": "✅ OK"},
    "stock_niveles": {"es": "Niveles de Stock", "en": "Stock Levels"},
    "stock_error_carga": {
        "es": "No se pudo cargar el stock. Verifica la configuración de Google Sheets.",
        "en": "Could not load stock. Check the Google Sheets configuration.",
    },
    "btn_update_stock": {"es": "🔄 Actualizar Stock", "en": "🔄 Refresh Stock"},

    # --- app.py: registros ----------------------------------------------
    "records_header": {"es": "Registros Detallados", "en": "Detailed Records"},
    "record_detail": {"es": "Detalle de Registro", "en": "Record Detail"},
    "col_id": {"es": "ID", "en": "ID"},
    "col_operario": {"es": "Operario", "en": "Operator"},
    "col_accion": {"es": "Acción Vial", "en": "Road Action"},
    "col_estado": {"es": "Estado", "en": "Status"},
    "col_direccion": {"es": "Dirección", "en": "Address"},
    "col_fecha": {"es": "Fecha", "en": "Date"},
    "select_cartel_id": {"es": "Seleccionar ID de cartel", "en": "Select sign ID"},
    "record_fmt_id": {"es": "ID {x} - {op}", "en": "ID {x} - {op}"},
    "fld_id": {"es": "**ID:**", "en": "**ID:**"},
    "fld_operario": {"es": "**Operario:**", "en": "**Operator:**"},
    "fld_accion": {"es": "**Acción:**", "en": "**Action:**"},
    "fld_estado": {"es": "**Estado:**", "en": "**Status:**"},
    "fld_fecha": {"es": "**Fecha:**", "en": "**Date:**"},
    "fld_latitud": {"es": "**Latitud:**", "en": "**Latitude:**"},
    "fld_longitud": {"es": "**Longitud:**", "en": "**Longitude:**"},
    "fld_direccion": {"es": "**Dirección:**", "en": "**Address:**"},
    "fld_whatsapp": {"es": "**WhatsApp:**", "en": "**WhatsApp:**"},
    "fld_notas": {"es": "**Notas:**", "en": "**Notes:**"},
    "select_cambiar_estado": {"es": "Cambiar estado", "en": "Change status"},
    "btn_update_estado": {"es": "Actualizar Estado", "en": "Update Status"},
    "estado_actualizado": {
        "es": "✅ Estado actualizado correctamente",
        "en": "✅ Status updated successfully",
    },
    "error_actualizar_estado": {
        "es": "❌ Error al actualizar el estado",
        "en": "❌ Error updating status",
    },
    "error_conexion_api": {
        "es": "❌ No se pudo conectar con la API",
        "en": "❌ Could not connect to the API",
    },
    "no_registros": {
        "es": "No hay registros para mostrar.",
        "en": "No records to display.",
    },
    "footer": {
        "es": "Vial Parking © 2026 - Sistema de Gestión de Cartelería Vial CABA",
        "en": "Vial Parking © 2026 - CABA Road Signage Management System",
    },

    # --- production.py ---
    "1": {"es": '1', "en": '1'},
    "2": {"es": '2', "en": '2'},
    "3": {"es": '3', "en": '3'},
    "4": {"es": '4', "en": '4'},
    "active": {"es": 'Activo', "en": 'Active'},
    "active_branches": {"es": 'Ramales activos', "en": 'Active branches'},
    "add_new_employee": {"es": 'Agregar nuevo operario', "en": 'Add new employee'},
    "after_loaded": {"es": 'Después cargada', "en": 'After loaded'},
    "alerts_notifications": {"es": 'Alertas y notificaciones', "en": 'Alerts & notifications'},
    "all_f": {"es": 'Todas', "en": 'All'},
    "all_m": {"es": 'Todos', "en": 'All'},
    "alto": {"es": 'Alto', "en": 'Height'},
    "ancho": {"es": 'Ancho', "en": 'Width'},
    "app_subtitle": {"es": 'Sistema de gestión de cartelería', "en": 'Signage management system'},
    "auth_hint_emp": {"es": 'Inicia sesión para gestionar operarios', "en": 'Sign in to manage employees'},
    "auth_hint_pc": {"es": 'Inicia sesión para registrar desde PC', "en": 'Sign in to register from PC'},
    "auth_hint_stock": {"es": 'Inicia sesión para gestionar stock', "en": 'Sign in to manage stock'},
    "auth_required": {"es": 'Autenticación requerida', "en": 'Authentication required'},
    "authenticated": {"es": 'Autenticado', "en": 'Authenticated'},
    "avg_per_zone": {"es": 'Promedio por zona', "en": 'Average per zone'},
    "avg_time": {"es": 'Tiempo promedio', "en": 'Average time'},
    "before_loaded": {"es": 'Antes cargada', "en": 'Before loaded'},
    "branch_row": {"es": 'Ramal {ramal}: {n} carteles ({exec} ejecutados)', "en": 'Branch {ramal}: {n} signs ({exec} executed)'},
    "branch_status": {"es": 'Estado por ramal', "en": 'Status by branch'},
    "branches_in_zone": {"es": 'Ramales en la zona', "en": 'Branches in zone'},
    "btn_add_employee": {"es": 'Agregar operario', "en": 'Add employee'},
    "btn_back_before": {"es": 'Volver al antes', "en": 'Back to before'},
    "btn_cancel": {"es": 'Cancelar', "en": 'Cancel'},
    "btn_cancel_all": {"es": 'Cancelar todo', "en": 'Cancel all'},
    "btn_clear": {"es": 'Limpiar', "en": 'Clear'},
    "btn_continue_after": {"es": 'Continuar al después', "en": 'Continue to after'},
    "btn_query": {"es": 'Consultar', "en": 'Query'},
    "btn_refresh": {"es": 'Actualizar', "en": 'Refresh'},
    "btn_register_another": {"es": 'Registrar otro', "en": 'Register another'},
    "btn_register_complete": {"es": 'Completar registro', "en": 'Complete registration'},
    "btn_register_movement": {"es": 'Registrar movimiento', "en": 'Register movement'},
    "clear_filters": {"es": 'Limpiar filtros', "en": 'Clear filters'},
    "col_active_branches": {"es": 'Ramales activos', "en": 'Active branches'},
    "col_avg_days": {"es": 'Días promedio', "en": 'Avg days'},
    "col_coords": {"es": 'Coordenadas', "en": 'Coordinates'},
    "col_count": {"es": 'Cantidad', "en": 'Count'},
    "col_date": {"es": 'Fecha', "en": 'Date'},
    "col_efficiency": {"es": 'Eficiencia', "en": 'Efficiency'},
    "col_exec_date": {"es": 'Fecha ejecución', "en": 'Exec date'},
    "col_executed": {"es": 'Ejecutados', "en": 'Executed'},
    "col_gasduct": {"es": 'Gasoducto', "en": 'Gasduct'},
    "col_height": {"es": 'Alto', "en": 'Height'},
    "col_item": {"es": 'Item', "en": 'Item'},
    "col_jobs_done": {"es": 'Trabajos realizados', "en": 'Jobs done'},
    "col_location": {"es": 'Ubicación', "en": 'Location'},
    "col_notes": {"es": 'Notas', "en": 'Notes'},
    "col_priority": {"es": 'Prioridad', "en": 'Priority'},
    "col_status": {"es": 'Estado', "en": 'Status'},
    "col_type": {"es": 'Tipo', "en": 'Type'},
    "col_width": {"es": 'Ancho', "en": 'Width'},
    "col_zone": {"es": 'Zona', "en": 'Zone'},
    "complete_required": {"es": 'Completa los campos requeridos', "en": 'Complete required fields'},
    "completed": {"es": 'Completado', "en": 'Completed'},
    "completed_appear_here": {"es": 'Los trabajos completados aparecerán aquí automáticamente.', "en": 'Completed jobs will appear here automatically.'},
    "control_panel": {"es": 'Panel de control', "en": 'Control panel'},
    "current_inventory": {"es": 'Inventario actual', "en": 'Current inventory'},
    "dashboard_check_credentials": {"es": 'Verifica las credenciales', "en": 'Check credentials'},
    "dashboard_exec_header": {"es": 'Ejecución', "en": 'Execution'},
    "dashboard_no_connection": {"es": 'Sin conexión', "en": 'No connection'},
    "data_refresh": {"es": 'Actualización de datos', "en": 'Data refresh'},
    "days": {"es": 'días', "en": 'days'},
    "dist_by_type": {"es": 'Distribución por tipo', "en": 'Distribution by type'},
    "emp_header": {"es": 'Operarios', "en": 'Employees'},
    "emp_tab_add": {"es": 'Agregar', "en": 'Add'},
    "emp_tab_list": {"es": 'Lista', "en": 'List'},
    "employee_added": {"es": 'Operario agregado', "en": 'Employee added'},
    "employee_error": {"es": 'Error al agregar operario', "en": 'Error adding employee'},
    "enter_item_warn": {"es": 'Ingresa un número de item', "en": 'Enter an item number'},
    "environment": {"es": 'Entorno', "en": 'Environment'},
    "error_generic": {"es": 'Error', "en": 'Error'},
    "error_get_employees": {"es": 'Error al obtener operarios', "en": 'Error getting employees'},
    "error_get_executed": {"es": 'Error al obtener ejecutados', "en": 'Error getting executed'},
    "error_get_orders": {"es": 'Error al obtener órdenes', "en": 'Error getting orders'},
    "error_get_signs": {"es": 'Error al obtener carteles', "en": 'Error getting signs'},
    "error_get_stock": {"es": 'Error al obtener stock', "en": 'Error getting stock'},
    "error_loading_data": {"es": 'Error al cargar datos', "en": 'Error loading data'},
    "error_read_output": {"es": 'Error al leer OUTPUT', "en": 'Error reading OUTPUT'},
    "estado": {"es": 'Estado', "en": 'Status'},
    "exec_time_analysis": {"es": 'Análisis de tiempos de ejecución', "en": 'Execution time analysis'},
    "executed": {"es": 'Ejecutados', "en": 'Executed'},
    "executing": {"es": 'Ejecutando', "en": 'Executing'},
    "fecha": {"es": 'Fecha', "en": 'Date'},
    "files": {"es": 'archivos', "en": 'files'},
    "filter_by_branch": {"es": 'Filtrar por ramal', "en": 'Filter by branch'},
    "filter_by_gasduct": {"es": 'Filtrar por gasoducto', "en": 'Filter by gasduct'},
    "filter_by_move_type": {"es": 'Filtrar por tipo de movimiento', "en": 'Filter by movement type'},
    "filter_by_status": {"es": 'Filtrar por estado', "en": 'Filter by status'},
    "filter_by_type": {"es": 'Filtrar por tipo', "en": 'Filter by type'},
    "filter_by_zone": {"es": 'Filtrar por zona', "en": 'Filter by zone'},
    "full_name": {"es": 'Nombre completo', "en": 'Full name'},
    "gasoducto": {"es": 'Gasoducto', "en": 'Gasduct'},
    "gasoducto_ramal": {"es": 'Gasoducto/Ramal', "en": 'Gasduct/Branch'},
    "general_stats": {"es": 'Estadísticas generales', "en": 'General statistics'},
    "high": {"es": 'Alta', "en": 'High'},
    "history_title": {"es": 'Historial', "en": 'History'},
    "immediate_attention": {"es": 'Atención inmediata', "en": 'Immediate attention'},
    "in_installation": {"es": 'En instalación', "en": 'In installation'},
    "in_process": {"es": 'En proceso', "en": 'In process'},
    "in_progress": {"es": 'En progreso', "en": 'In progress'},
    "inactive": {"es": 'Inactivo', "en": 'Inactive'},
    "incoming": {"es": 'Entrada', "en": 'Incoming'},
    "init_credentials_hint": {"es": 'Configura las credenciales', "en": 'Set up credentials'},
    "init_sheets_error": {"es": 'Error al iniciar Sheets', "en": 'Error starting Sheets'},
    "interactive_map": {"es": 'Mapa interactivo', "en": 'Interactive map'},
    "item_found": {"es": 'Item encontrado', "en": 'Item found'},
    "item_not_found": {"es": 'Item no encontrado', "en": 'Item not found'},
    "item_number_input": {"es": 'Número de item', "en": 'Item number'},
    "item_number_ph": {"es": 'Ej: 277', "en": 'E.g.: 277'},
    "items_total_hint": {"es": 'Total de items', "en": 'Total items'},
    "jobs_realtime": {"es": 'Trabajos en tiempo real', "en": 'Real-time jobs'},
    "last_job": {"es": 'Último trabajo', "en": 'Last job'},
    "last_update": {"es": 'Última actualización', "en": 'Last update'},
    "last_update_caption": {"es": 'Última actualización', "en": 'Last update'},
    "last_update_none": {"es": 'Sin actualizaciones', "en": 'No updates'},
    "latitud": {"es": 'Latitud', "en": 'Latitude'},
    "limited_mode": {"es": 'Modo limitado', "en": 'Limited mode'},
    "login_connected_as": {"es": 'Conectado como', "en": 'Connected as'},
    "login_expander": {"es": 'Iniciar sesión', "en": 'Sign in'},
    "login_logout": {"es": 'Cerrar sesión', "en": 'Log out'},
    "login_password": {"es": 'Contraseña', "en": 'Password'},
    "login_public_mode": {"es": 'Modo público', "en": 'Public mode'},
    "login_role": {"es": 'Rol', "en": 'Role'},
    "login_signin": {"es": 'Ingresar', "en": 'Sign in'},
    "login_user": {"es": 'Usuario', "en": 'User'},
    "login_user_not_found": {"es": 'Usuario no encontrado', "en": 'User not found'},
    "login_welcome": {"es": 'Bienvenido {user}', "en": 'Welcome {user}'},
    "login_wrong_password": {"es": 'Contraseña incorrecta', "en": 'Wrong password'},
    "logo_not_found": {"es": 'Logo no encontrado', "en": 'Logo not found'},
    "longitud": {"es": 'Longitud', "en": 'Longitude'},
    "low": {"es": 'Baja', "en": 'Low'},
    "map_executed": {"es": 'Ejecutado', "en": 'Executed'},
    "map_gen_error": {"es": 'Error al generar el mapa', "en": 'Error generating map'},
    "map_in_progress": {"es": 'En progreso', "en": 'In progress'},
    "map_interactive_zone": {"es": 'Zona interactiva', "en": 'Interactive zone'},
    "map_pending": {"es": 'Pendiente', "en": 'Pending'},
    "metric_active_branches": {"es": 'Ramales activos', "en": 'Active branches'},
    "metric_executed": {"es": 'Ejecutados', "en": 'Executed'},
    "metric_operational_zones": {"es": 'Zonas operativas', "en": 'Operational zones'},
    "metric_total_signs": {"es": 'Total de carteles', "en": 'Total signs'},
    "metrics_load_error": {"es": 'Error al cargar métricas', "en": 'Error loading metrics'},
    "mode_": {"es": 'Modo', "en": 'Mode'},
    "mode_dashboard": {"es": "📊 Dashboard Principal", "en": "📊 Main Dashboard"},
    "mode_whatsapp": {"es": "💬 WhatsApp", "en": "💬 WhatsApp"},
    "mode_orders": {"es": "📋 Órdenes de Trabajo", "en": "📋 Work Orders"},
    "mode_zones": {"es": "🗺️ Zonas y Ramales", "en": "🗺️ Zones & Branches"},
    "mode_stock": {"es": "📦 Gestión de Stock", "en": "📦 Stock Management"},
    "mode_employees": {"es": "👷 Gestión de Empleados", "en": "👷 Employee Management"},
    "mode_reports": {"es": "📈 Reportes y Estadísticas", "en": "📈 Reports & Statistics"},
    "most_active_zone": {"es": 'Zona más activa', "en": 'Most active zone'},
    "movement_error": {"es": 'Error en el movimiento', "en": 'Movement error'},
    "movement_registered": {"es": 'Movimiento registrado', "en": 'Movement registered'},
    "movement_type": {"es": 'Tipo de movimiento', "en": 'Movement type'},
    "need_3_photos": {"es": 'Se requieren 3 fotos', "en": '3 photos required'},
    "no_completed_to_analyze": {"es": '📭 No hay trabajos completados para analizar', "en": '📭 No completed jobs to analyze'},
    "no_critical_alerts": {"es": 'Sin alertas críticas', "en": 'No critical alerts'},
    "no_data": {"es": 'Sin datos', "en": 'No data'},
    "no_employees": {"es": 'No hay operarios', "en": 'No employees'},
    "no_low_alerts": {"es": 'Sin alertas de stock bajo', "en": 'No low-stock alerts'},
    "no_sheets_conn": {"es": 'Sin conexión a Sheets', "en": 'No Sheets connection'},
    "no_signs_filtered": {"es": 'No hay carteles con esos filtros', "en": 'No signs with those filters'},
    "no_signs_filters": {"es": 'No hay carteles con esos filtros', "en": 'No signs with those filters'},
    "no_stock_data": {"es": 'Sin datos de stock', "en": 'No stock data'},
    "no_urgent_orders": {"es": 'Sin órdenes urgentes', "en": 'No urgent orders'},
    "normal": {"es": 'Normal', "en": 'Normal'},
    "notes": {"es": 'Notas', "en": 'Notes'},
    "numero": {"es": 'Número', "en": 'Number'},
    "observaciones": {"es": 'Observaciones', "en": 'Notes'},
    "only_3_photos": {"es": 'Solo 3 fotos', "en": 'Only 3 photos'},
    "operative_zones": {"es": 'Zonas operativas', "en": 'Operational zones'},
    "operator": {"es": 'Operario', "en": 'Operator'},
    "orders_header": {"es": 'Órdenes', "en": 'Orders'},
    "orders_ok": {"es": 'Órdenes al día', "en": 'Orders up to date'},
    "orders_tab_done": {"es": 'Realizadas', "en": 'Done'},
    "orders_tab_times": {"es": 'Tiempos', "en": 'Times'},
    "orders_urgent": {"es": 'Urgentes', "en": 'Urgent'},
    "outgoing": {"es": 'Salida', "en": 'Outgoing'},
    "pc_register_header": {"es": 'Registro desde PC', "en": 'PC registration'},
    "pc_register_info": {"es": 'Registra trabajos desde PC', "en": 'Register jobs from PC'},
    "pct_of_total": {"es": '% del total', "en": '% of total'},
    "pct_progress": {"es": '% progreso', "en": '% progress'},
    "pending": {"es": 'Pendiente', "en": 'Pending'},
    "phone": {"es": 'Teléfono', "en": 'Phone'},
    "popup_branch": {"es": 'Ramal', "en": 'Branch'},
    "popup_item": {"es": 'Item', "en": 'Item'},
    "popup_location": {"es": 'Ubicación', "en": 'Location'},
    "popup_status": {"es": 'Estado', "en": 'Status'},
    "popup_type": {"es": 'Tipo', "en": 'Type'},
    "popup_zone": {"es": 'Zona', "en": 'Zone'},
    "prioridad": {"es": 'Prioridad', "en": 'Priority'},
    "processing_register": {"es": 'Procesando registro...', "en": 'Processing registration...'},
    "quantity": {"es": 'Cantidad', "en": 'Quantity'},
    "query_error": {"es": 'Error en la consulta', "en": 'Query error'},
    "querying_item": {"es": 'Consultando item...', "en": 'Querying item...'},
    "refresh_data": {"es": 'Actualizar datos', "en": 'Refresh data'},
    "register_failed": {"es": 'Registro fallido', "en": 'Registration failed'},
    "register_movement": {"es": 'Registrar movimiento', "en": 'Register movement'},
    "role_label": {"es": 'Rol', "en": 'Role'},
    "search_by_location": {"es": 'Buscar por ubicación', "en": 'Search by location'},
    "select_3_after": {"es": 'Selecciona 3 fotos del después', "en": 'Select 3 after photos'},
    "select_3_before": {"es": 'Selecciona 3 fotos del antes', "en": 'Select 3 before photos'},
    "select_branch": {"es": 'Seleccionar ramal', "en": 'Select branch'},
    "select_branch_detail": {"es": 'Selecciona un ramal para ver el detalle', "en": 'Select a branch to see detail'},
    "select_branch_hint": {"es": 'Selecciona un ramal', "en": 'Select a branch'},
    "select_placeholder": {"es": 'Selecciona...', "en": 'Select...'},
    "select_zone": {"es": 'Seleccionar zona', "en": 'Select zone'},
    "service_unavailable": {"es": 'Servicio no disponible', "en": 'Service unavailable'},
    "sheets_connected": {"es": 'Sheets conectado', "en": 'Sheets connected'},
    "sheets_disconnected": {"es": 'Sheets desconectado', "en": 'Sheets disconnected'},
    "sheets_unavailable": {"es": 'Sheets no disponible', "en": 'Sheets unavailable'},
    "showing_jobs": {"es": 'Mostrando {n} trabajos', "en": 'Showing {n} jobs'},
    "sign_gasduct": {"es": 'Cartel de gasoducto', "en": 'Gasduct sign'},
    "sign_gasduct_desc": {"es": 'Cartel de gasoducto', "en": 'Gasduct sign'},
    "sign_gasducts": {"es": 'Carteles de gasoductos', "en": 'Gasduct signs'},
    "sign_gasducts_desc": {"es": 'Carteles de gasoductos', "en": 'Gasduct signs'},
    "sign_pipe": {"es": 'Cartel de cañería', "en": 'Pipe sign'},
    "sign_pipe_desc": {"es": 'Cartel de cañería', "en": 'Pipe sign'},
    "sign_pipes": {"es": 'Carteles de cañerías', "en": 'Pipe signs'},
    "sign_pipes_desc": {"es": 'Carteles de cañerías', "en": 'Pipe signs'},
    "sign_type": {"es": 'Tipo de cartel', "en": 'Sign type'},
    "sign_types": {"es": 'Tipos de cartel', "en": 'Sign types'},
    "sign_types_ecogas": {"es": 'Tipos de cartel Ecogas', "en": 'Ecogas sign types'},
    "sign_types_metric": {"es": 'Tipos de cartel', "en": 'Sign types'},
    "signs_by_zone_dist": {"es": 'Distribución de carteles por zona', "en": 'Signs distribution by zone'},
    "signs_detail": {"es": 'Detalle de carteles', "en": 'Signs detail'},
    "signs_in_db": {"es": 'Carteles en base', "en": 'Signs in DB'},
    "signs_in_top": {"es": 'Carteles en la zona top', "en": 'Signs in top zone'},
    "status_label": {"es": 'Estado', "en": 'Status'},
    "step1_query_item": {"es": 'Paso 1: Consultar item', "en": 'Step 1: Query item'},
    "step2_before": {"es": 'Paso 2: Antes', "en": 'Step 2: Before'},
    "step3_after": {"es": 'Paso 3: Después', "en": 'Step 3: After'},
    "stock_critical": {"es": 'Stock crítico', "en": 'Critical stock'},
    "stock_critical_label": {"es": 'Crítico', "en": 'Critical'},
    "stock_critical_ok": {"es": 'Stock crítico OK', "en": 'Critical stock OK'},
    "stock_low": {"es": 'Stock bajo', "en": 'Low stock'},
    "stock_low_ok": {"es": 'Stock bajo OK', "en": 'Low stock OK'},
    "stock_tab_current": {"es": 'Actual', "en": 'Current'},
    "stock_tab_history": {"es": 'Historial', "en": 'History'},
    "stock_tab_move": {"es": 'Movimientos', "en": 'Movements'},
    "summary": {"es": 'Resumen', "en": 'Summary'},
    "summary_by_operator": {"es": 'Resumen por operario', "en": 'Summary by operator'},
    "system_status": {"es": 'Estado del sistema', "en": 'System status'},
    "tamanio": {"es": 'Tamaño', "en": 'Size'},
    "times_by_gasduct": {"es": 'Tiempos por gasoducto', "en": 'Times by gasduct'},
    "times_by_type": {"es": 'Tiempos por tipo', "en": 'Times by type'},
    "times_by_zone": {"es": 'Tiempos por zona', "en": 'Times by zone'},
    "tipo": {"es": 'Tipo', "en": 'Type'},
    "tipo_cartel": {"es": 'Tipo de cartel', "en": 'Sign type'},
    "tipo_completo": {"es": 'Tipo completo', "en": 'Full type'},
    "tipo_raw": {"es": 'Tipo', "en": 'Type'},
    "today": {"es": 'Hoy', "en": 'Today'},
    "tooltip_item": {"es": 'Item', "en": 'Item'},
    "top10_zones": {"es": 'Top 10 zonas', "en": 'Top 10 zones'},
    "top_zone": {"es": 'Zona top', "en": 'Top zone'},
    "total": {"es": 'Total', "en": 'Total'},
    "total_branches": {"es": 'Total ramales', "en": 'Total branches'},
    "total_employees": {"es": 'Total operarios', "en": 'Total employees'},
    "total_items": {"es": 'Total items', "en": 'Total items'},
    "total_jobs": {"es": 'Total trabajos', "en": 'Total jobs'},
    "total_jobs_2": {"es": 'Total trabajos', "en": 'Total jobs'},
    "total_movements": {"es": 'Total movimientos', "en": 'Total movements'},
    "total_signs": {"es": 'Total carteles', "en": 'Total signs'},
    "total_units": {"es": 'Total unidades', "en": 'Total units'},
    "types": {"es": 'tipos', "en": 'types'},
    "ubicacion": {"es": 'Ubicación', "en": 'Location'},
    "units_line": {"es": '{n} unidades', "en": '{n} units'},
    "user_role": {"es": 'Rol', "en": 'Role'},
    "users": {"es": 'usuarios', "en": 'users'},
    "view_mode": {"es": 'Modo de vista', "en": 'View mode'},
    "wa_active": {"es": 'WhatsApp activo', "en": 'WhatsApp active'},
    "wa_flow_info": {"es": 'Flujo de WhatsApp', "en": 'WhatsApp flow'},
    "wa_flow_title": {"es": 'Flujo', "en": 'Flow'},
    "wa_header": {"es": 'WhatsApp', "en": 'WhatsApp'},
    "wa_mode_multi": {"es": 'Múltiple', "en": 'Multiple'},
    "wa_mode_simple": {"es": 'Simple', "en": 'Simple'},
    "wa_select_mode": {"es": 'Selecciona modo', "en": 'Select mode'},
    "wa_simple_caption": {"es": 'Modo simple', "en": 'Simple mode'},
    "wa_simple_h": {"es": 'Simple', "en": 'Simple'},
    "wa_tab_flow": {"es": 'Flujo', "en": 'Flow'},
    "wa_tab_pc": {"es": 'PC', "en": 'PC'},
    "warn_error": {"es": 'Advertencia', "en": 'Warning'},
    "with_photos": {"es": 'con fotos', "en": 'with photos'},
    "work_registered": {"es": 'Trabajo registrado', "en": 'Work registered'},
    "zona": {"es": 'Zona', "en": 'Zone'},
    "zone_detail": {"es": 'Detalle por zona', "en": 'Zone detail'},
    "zone_summary": {"es": '{zona}: {n} carteles ({exec} ejecutados)', "en": '{zona}: {n} signs ({exec} executed)'},
    "zones_analysis": {"es": 'Análisis por zonas', "en": 'Zones analysis'},
    "zones_label": {"es": 'Zonas', "en": 'Zones'},
    "zones_label_short": {"es": 'Zonas', "en": 'Zones'},
}
