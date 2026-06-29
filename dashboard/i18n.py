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
}
