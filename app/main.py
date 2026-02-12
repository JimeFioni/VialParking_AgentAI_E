from fastapi import FastAPI, Depends, HTTPException, Form, File, UploadFile, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import os
import time

from app.database import init_db, get_db, RegistroCartel, MovimientoStock
from app.models import CartelCreate, CartelResponse, WhatsAppMessage, StockAlert
from agent.gemini_agent import GeminiAgent
from services.whatsapp import WhatsAppService
from services.google_sheets import GoogleSheetsService
from services.geolocation import GeolocationService

# Configurar ID de planilla OUTPUT
os.environ["OUTPUT_SHEET_ID"] = "1qKQxWRcN1bjbavw2BgYPjh0rA0VaoaDfTHt_8COAVKw"

# Configurar carpetas de Google Drive para imágenes (input y output)
os.environ["IMAGENES_CARTELES_FOLDER_ID"] = "19YQCBODmkk_dCssMBB2GuNPfQs5oaUmV"
os.environ["OUTPUT_IMAGENES_FOLDER_ID"] = "19YQCBODmkk_dCssMBB2GuNPfQs5oaUmV"

app = FastAPI(
    title="ECOGAS - Vial Parking API",
    description="Sistema de gestión de cartelería de gasoductos ECOGAS con agente AI",
    version="1.0.0"
)

# Inicializar servicios
gemini_agent = GeminiAgent()
whatsapp_service = WhatsAppService()
sheets_service = GoogleSheetsService()
geo_service = GeolocationService()

# Sistema de estados de conversación
# Estados: 'esperando_imagenes_antes', 'en_trabajo', 'esperando_imagenes_despues'
conversation_states = {}

# Inicializar BD
init_db()


@app.get("/")
async def root():
    return {
        "message": "ECOGAS Vial Parking API - Sistema de Gestión de Cartelería de Gasoductos",
        "version": "1.0.0",
        "status": "active",
        "distribuidor": "ECOGAS",
        "environment": os.getenv("ENVIRONMENT", "development")
    }


@app.get("/health")
async def health_check():
    """
    Endpoint de salud general del sistema.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {
            "api": "running",
            "database": "connected",
            "whatsapp": "initialized"
        }
    }


@app.get("/health/whatsapp")
async def health_whatsapp():
    """
    Verifica el estado del servicio de WhatsApp.
    """
    health = whatsapp_service.health_check()
    estadisticas = whatsapp_service.obtener_estadisticas()
    
    return {
        "health": health,
        "statistics": estadisticas,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/stats")
async def estadisticas_sistema():
    """
    Retorna estadísticas generales del sistema.
    """
    return {
        "whatsapp": whatsapp_service.obtener_estadisticas(),
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development")
    }


@app.post("/webhook/whatsapp", response_class=PlainTextResponse)
async def webhook_whatsapp(
    background_tasks: BackgroundTasks,
    From: str = Form(...),
    Body: str = Form(""),
    MediaUrl0: Optional[str] = Form(None),
    Latitude: Optional[str] = Form(None),
    Longitude: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Webhook para recibir mensajes de WhatsApp desde Twilio.
    FLUJO PRINCIPAL: Usuario envía número de item para trabajar en ese cartel.
    """
    try:
        # Extraer número del operario
        whatsapp_number = From
        operario = Body.split()[0] if Body else "Operario"
        
        # 📋 LOG: Registrar mensaje recibido
        sheets_service.registrar_log_whatsapp(
            numero_telefono=whatsapp_number,
            tipo_mensaje="recibido",
            contenido=Body if Body else "[Sin texto]",
            tiene_media=bool(MediaUrl0),
            media_url=MediaUrl0 if MediaUrl0 else "",
            item_relacionado="",
            estado_flujo=conversation_states.get(whatsapp_number, {}).get('estado', 'inicial'),
            respuesta_bot=""
        )
        
        # FLUJO PRINCIPAL: Detectar número(s) de ítem en el mensaje
        import re
        if Body and re.search(r'\d+', Body):
            print(f"🔍 Detectado número(s) de ítem en mensaje: {Body}")
            
            # Extraer TODOS los números del mensaje
            numeros = re.findall(r'\d+', Body)
            print(f"📊 Números encontrados: {numeros}")
            
            if numeros:
                # Modo múltiple: si hay más de un número
                if len(numeros) > 1:
                    print(f"🔢 MODO MÚLTIPLE: {len(numeros)} items detectados")
                    
                    # Buscar información de todos los items
                    items_validos = []
                    items_invalidos = []
                    
                    for num in numeros:
                        cartel = sheets_service.buscar_cartel_por_item(num)
                        if cartel:
                            items_validos.append({
                                'numero': cartel.get('numero', num),
                                'info': cartel
                            })
                        else:
                            items_invalidos.append(num)
                    
                    if not items_validos:
                        whatsapp_service.enviar_mensaje(
                            whatsapp_number,
                            f"❌ No se encontró ningún ítem válido en la planilla."
                        )
                        return "OK"
                    
                    # Avisar sobre items inválidos si los hay
                    if items_invalidos:
                        whatsapp_service.enviar_mensaje(
                            whatsapp_number,
                            f"⚠️ Items no encontrados: {', '.join(items_invalidos)}"
                        )
                    
                    # Enviar resumen de items a trabajar
                    resumen = f"✅ *{len(items_validos)} ITEMS PARA TRABAJAR*\n\n"
                    for item in items_validos:
                        info = item['info']
                        tipo_info = info.get('tipo_completo', info.get('tipo_raw', '?'))
                        resumen += f"📋 #{item['numero']} - {info.get('ubicacion', 'Sin ubicación')}\n"
                        resumen += f"   🔴 Tipo: {tipo_info}\n\n"
                    
                    resumen += f"📸 Enviaré la información de cada uno y luego solicitaré las fotos ANTES de todos.\n\n"
                    resumen += f"Una vez que tengas los ANTES, envía *'listo [numero]'* al terminar cada trabajo."
                    
                    whatsapp_service.enviar_mensaje(whatsapp_number, resumen)
                    
                    # Enviar información detallada de cada item
                    for item in items_validos:
                        numero = item['numero']
                        cartel = item['info']
                        tipo_info = cartel.get('tipo_completo', cartel.get('tipo_raw', 'No especificado'))
                        
                        respuesta = f"""
📋 *CARTEL #{numero}*

🛣️ Gasoducto/Ramal: {cartel.get('gasoducto_ramal', 'No especificado')}
📍 Ubicación: {cartel.get('ubicacion', 'No especificada')}
📌 Coordenadas: {cartel.get('coordenadas', 'No disponibles')}

⚠️ *━━━━━━━━━━━━━━━━━━━*
🔴 *TIPO DE CARTEL:*
*{tipo_info}*
⚠️ *━━━━━━━━━━━━━━━━━━━*

📏 Tamaño: {cartel.get('tamanio', 'No especificado')}
"""
                        
                        if cartel.get('tapada_caneria') and cartel.get('tapada_caneria') not in ['-', '']:
                            respuesta += f"🔧 Tapada cañería: {cartel.get('tapada_caneria')}\n"
                        
                        respuesta += f"""📝 Observaciones: {cartel.get('observaciones', 'Sin observaciones')}
📅 Estado: {cartel.get('estado', 'No especificado')}
"""
                        
                        if cartel.get('tipo_trabajo'):
                            respuesta += f"\n🔨 *Tipo de trabajo:*\n{cartel.get('tipo_trabajo')}\n"
                            if cartel.get('detalles_instalacion'):
                                respuesta += "\n📦 *Detalles de instalación:*\n"
                                for detalle in cartel.get('detalles_instalacion', []):
                                    respuesta += f"  • {detalle}\n"
                        
                        respuesta += f"\n🌍 Zona: {cartel.get('zona', 'No especificada')}"
                        
                        whatsapp_service.enviar_mensaje(whatsapp_number, respuesta.strip())
                        time.sleep(1)
                        
                        # Enviar imágenes si están disponibles
                        imagenes = sheets_service.obtener_imagenes_cartel(numero)
                        if imagenes:
                            for idx, imagen in enumerate(imagenes, 1):
                                caption = f"🖼️ Item #{numero} - Imagen {idx}/{len(imagenes)}"
                                success = whatsapp_service.enviar_imagen(
                                    whatsapp_number,
                                    imagen['url'],
                                    caption
                                )
                                if not success:
                                    whatsapp_service.enviar_mensaje(
                                        whatsapp_number,
                                        f"{caption}\n{imagen['web_view']}"
                                    )
                                time.sleep(1)
                    
                    # Inicializar estado múltiple
                    primer_item = items_validos[0]['numero']
                    items_dict = {}
                    for item in items_validos:
                        items_dict[str(item['numero'])] = {
                            'estado': 'pendiente_antes',
                            'cartel_info': item['info'],
                            'imagenes_antes': [],
                            'urls_imagenes_antes': []
                        }
                    
                    conversation_states[whatsapp_number] = {
                        'modo': 'multiple',
                        'items_activos': items_dict,
                        'item_actual_antes': primer_item,
                        'item_actual_despues': None,
                        'imagenes_temp': []
                    }
                    
                    # Pedir fotos ANTES del primer item
                    whatsapp_service.enviar_mensaje(
                        whatsapp_number,
                        f"\n📸 *FOTOS ANTES - ITEM #{primer_item}*\n\n"
                        f"Envía 3 fotos del estado ANTES del cartel #{primer_item}.\n\n"
                        f"📷📷📷 Envía las 3 imágenes ahora."
                    )
                    
                    # Actualizar estado del primer item
                    conversation_states[whatsapp_number]['items_activos'][str(primer_item)]['estado'] = 'recibiendo_antes'
                    
                    return "OK"
                    
                # Modo simple: un solo número
                item_number = numeros[0]
                print(f"📊 Buscando ítem: {item_number}")
                
                # Buscar información en la planilla
                cartel = sheets_service.buscar_cartel_por_item(item_number)
                
                if not cartel:
                    whatsapp_service.enviar_mensaje(
                        whatsapp_number,
                        f"❌ No se encontró el ítem {item_number} en la planilla."
                    )
                    return "OK"
                
                # Obtener imágenes del Drive
                imagenes = sheets_service.obtener_imagenes_cartel(item_number)
                
                # Preparar respuesta con información completa
                tipo_info = cartel.get('tipo_completo', cartel.get('tipo_raw', 'No especificado'))
                
                respuesta = f"""
📋 *INFORMACIÓN DEL CARTEL #{cartel.get('numero', 'N/A')}*

🛣️ Gasoducto/Ramal: {cartel.get('gasoducto_ramal', 'No especificado')}
📍 Ubicación: {cartel.get('ubicacion', 'No especificada')}
📌 Coordenadas: {cartel.get('coordenadas', 'No disponibles')}

⚠️ *━━━━━━━━━━━━━━━━━━━*
🔴 *TIPO DE CARTEL:*
*{tipo_info}*
⚠️ *━━━━━━━━━━━━━━━━━━━*

📏 Tamaño: {cartel.get('tamanio', 'No especificado')}
"""
                
                # Agregar tapada de cañería si existe
                if cartel.get('tapada_caneria') and cartel.get('tapada_caneria') not in ['-', '']:
                    respuesta += f"🔧 Tapada cañería: {cartel.get('tapada_caneria')}\n"
                
                respuesta += f"""📝 Observaciones: {cartel.get('observaciones', 'Sin observaciones')}
📅 Estado: {cartel.get('estado', 'No especificado')}
"""
                
                # Agregar información de tipo de trabajo si existe
                if cartel.get('tipo_trabajo'):
                    respuesta += f"\n🔨 *Tipo de trabajo:*\n{cartel.get('tipo_trabajo')}\n"
                    
                    # Agregar detalles de instalación
                    if cartel.get('detalles_instalacion'):
                        respuesta += "\n📦 *Detalles de instalación:*\n"
                        for detalle in cartel.get('detalles_instalacion', []):
                            respuesta += f"  • {detalle}\n"
                
                respuesta += f"\n🌍 Zona: {cartel.get('zona', 'No especificada')}"
                
                # Enviar información de texto
                whatsapp_service.enviar_mensaje(whatsapp_number, respuesta.strip())
                
                # Enviar imágenes si están disponibles
                if imagenes:
                    whatsapp_service.enviar_mensaje(
                        whatsapp_number,
                        f"📸 Enviando {len(imagenes)} imagen(es) de referencia..."
                    )
                    
                    for idx, imagen in enumerate(imagenes, 1):
                        # Enviar imagen como multimedia con caption
                        caption = f"🖼️ Imagen {idx}/{len(imagenes)}: {imagen['name']}"
                        success = whatsapp_service.enviar_imagen(
                            whatsapp_number,
                            imagen['url'],
                            caption
                        )
                        if not success:
                            # Si falla el envío multimedia, enviar como URL
                            whatsapp_service.enviar_mensaje(
                                whatsapp_number,
                                f"{caption}\n{imagen['web_view']}"
                            )
                        time.sleep(1)  # Pausa entre cada imagen
                    
                    # Pausa adicional para asegurar que todas las imágenes se envíen
                    time.sleep(2)
                else:
                    whatsapp_service.enviar_mensaje(
                        whatsapp_number,
                        "ℹ️ No se encontraron imágenes para este cartel en Drive."
                    )
                
                # Pedir imágenes ANTES de comenzar el trabajo (DESPUÉS de enviar todas las de referencia)
                numero = cartel.get('numero', item_number)
                whatsapp_service.enviar_mensaje(
                    whatsapp_number,
                    f"\n📸 *ANTES DE COMENZAR EL TRABAJO*\n\n"
                    f"Por favor, envía 3 fotos del estado actual del cartel #{numero} ANTES de realizar cualquier trabajo.\n\n"
                    f"Envía las 3 imágenes ahora. 📷📷📷"
                )
                
                # Actualizar estado de conversación
                conversation_states[whatsapp_number] = {
                    'estado': 'esperando_imagenes_antes',
                    'numero_item': numero,
                    'imagenes_antes': [],
                    'cartel_info': cartel
                }
                
                # 📋 LOG: Registrar solicitud exitosa de item
                sheets_service.registrar_log_whatsapp(
                    numero_telefono=whatsapp_number,
                    tipo_mensaje="enviado",
                    contenido=f"Item {numero} solicitado - Información enviada",
                    tiene_media=False,
                    media_url="",
                    item_relacionado=str(numero),
                    estado_flujo="esperando_imagenes_antes",
                    respuesta_bot="Solicitando 3 fotos ANTES del trabajo"
                )
                
                return "OK"
        
        # MANEJO DE IMÁGENES SEGÚN ESTADO DE CONVERSACIÓN
        estado_actual = conversation_states.get(whatsapp_number, {})
        
        # ===== MODO MÚLTIPLE =====
        if estado_actual.get('modo') == 'multiple':
            if MediaUrl0:
                items_activos = estado_actual.get('items_activos', {})
                item_actual_antes = estado_actual.get('item_actual_antes')
                item_actual_despues = estado_actual.get('item_actual_despues')
                
                # Descarga la imagen
                auth = (os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
                image_data = await whatsapp_service.descargar_imagen(MediaUrl0, auth)
                
                if not image_data:
                    whatsapp_service.enviar_mensaje(whatsapp_number, "❌ Error al descargar la imagen. Intenta nuevamente.")
                    return "OK"
                
                # Recibiendo fotos ANTES
                if item_actual_antes and items_activos.get(str(item_actual_antes), {}).get('estado') == 'recibiendo_antes':
                    estado_actual['imagenes_temp'].append(image_data)
                    num_recibidas = len(estado_actual['imagenes_temp'])
                    
                    if num_recibidas < 3:
                        whatsapp_service.enviar_mensaje(
                            whatsapp_number,
                            f"✅ Imagen {num_recibidas}/3 recibida para item #{item_actual_antes}.\n\n📸 Envía la imagen {num_recibidas + 1} de 3."
                        )
                    else:
                        # 3 fotos ANTES completadas
                        whatsapp_service.enviar_mensaje(
                            whatsapp_number,
                            f"✅ 3 imágenes recibidas.\n\n⏳ Guardando en Drive..."
                        )
                        
                        # Subir a Drive
                        urls_guardadas = []
                        item_formateado = str(item_actual_antes).zfill(3)
                        for idx, img_data in enumerate(estado_actual['imagenes_temp'], 1):
                            filename = f"{item_formateado}-{str(idx).zfill(3)}.jpg"
                            url = sheets_service.subir_imagen_antes_despues(
                                img_data, 
                                filename, 
                                item_actual_antes, 
                                'antes'
                            )
                            if url:
                                urls_guardadas.append(url)
                        
                        # Actualizar estado del item
                        items_activos[str(item_actual_antes)]['estado'] = 'en_espera'
                        items_activos[str(item_actual_antes)]['urls_imagenes_antes'] = urls_guardadas
                        items_activos[str(item_actual_antes)]['imagenes_antes'] = estado_actual['imagenes_temp'].copy()
                        estado_actual['imagenes_temp'] = []
                        
                        # Buscar siguiente item pendiente
                        siguiente_item = None
                        for num_item, info in items_activos.items():
                            if info['estado'] == 'pendiente_antes':
                                siguiente_item = num_item
                                break
                        
                        if siguiente_item:
                            # Hay más items para pedir ANTES
                            estado_actual['item_actual_antes'] = siguiente_item
                            items_activos[siguiente_item]['estado'] = 'recibiendo_antes'
                            
                            whatsapp_service.enviar_mensaje(
                                whatsapp_number,
                                f"✅ *IMÁGENES GUARDADAS - Item #{item_actual_antes}*\n\n"
                                f"📸 *FOTOS ANTES - ITEM #{siguiente_item}*\n\n"
                                f"Envía 3 fotos del estado ANTES del cartel #{siguiente_item}.\n\n"
                                f"📷📷📷 Envía las 3 imágenes ahora."
                            )
                        else:
                            # Todos los ANTES completados
                            estado_actual['item_actual_antes'] = None
                            
                            items_en_espera = [num for num, info in items_activos.items() if info['estado'] == 'en_espera']
                            
                            whatsapp_service.enviar_mensaje(
                                whatsapp_number,
                                f"✅ *TODOS LOS ANTES COMPLETADOS*\n\n"
                                f"📋 Items listos para trabajar: {', '.join(items_en_espera)}\n\n"
                                f"🔧 Procede con los trabajos.\n\n"
                                f"Cuando termines un trabajo, envía:\n"
                                f"*'listo [numero]'* o *'finalizado [numero]'*\n\n"
                                f"Ejemplo: 'listo {items_en_espera[0]}'"
                            )
                        
                        conversation_states[whatsapp_number] = estado_actual
                    
                    return "OK"
                
                # Recibiendo fotos DESPUÉS
                if item_actual_despues and items_activos.get(str(item_actual_despues), {}).get('estado') == 'recibiendo_despues':
                    estado_actual['imagenes_temp'].append(image_data)
                    num_recibidas = len(estado_actual['imagenes_temp'])
                    
                    if num_recibidas < 3:
                        whatsapp_service.enviar_mensaje(
                            whatsapp_number,
                            f"✅ Imagen {num_recibidas}/3 recibida para item #{item_actual_despues}.\n\n📸 Envía la imagen {num_recibidas + 1} de 3."
                        )
                    else:
                        # 3 fotos DESPUÉS completadas
                        whatsapp_service.enviar_mensaje(
                            whatsapp_number,
                            f"✅ 3 imágenes recibidas.\n\n⏳ Guardando en Drive..."
                        )
                        
                        # Subir a Drive
                        urls_guardadas = []
                        item_formateado = str(item_actual_despues).zfill(3)
                        for idx, img_data in enumerate(estado_actual['imagenes_temp'], 1):
                            filename = f"{item_formateado}-{str(idx + 3).zfill(3)}.jpg"
                            url = sheets_service.subir_imagen_antes_despues(
                                img_data, 
                                filename, 
                                item_actual_despues, 
                                'despues'
                            )
                            if url:
                                urls_guardadas.append(url)
                        
                        # Registrar en OUTPUT
                        cartel_info = items_activos[str(item_actual_despues)].get('cartel_info', {})
                        registro_exitoso = sheets_service.registrar_trabajo_ecogas({
                            'numero_item': item_actual_despues,
                            'cartel_info': cartel_info
                        })
                        
                        # Actualizar estado del item
                        items_activos[str(item_actual_despues)]['estado'] = 'completado'
                        items_activos[str(item_actual_despues)]['urls_imagenes_despues'] = urls_guardadas
                        estado_actual['imagenes_temp'] = []
                        estado_actual['item_actual_despues'] = None
                        
                        # Contar items pendientes
                        items_pendientes = [num for num, info in items_activos.items() if info['estado'] == 'en_espera']
                        items_completados = [num for num, info in items_activos.items() if info['estado'] == 'completado']
                        
                        mensaje_final = (
                            f"✅ *TRABAJO COMPLETADO - Item #{item_actual_despues}*\n\n"
                            f"📸 Imágenes DESPUÉS guardadas en Drive\n"
                        )
                        
                        if registro_exitoso:
                            mensaje_final += f"📊 Registrado en planilla OUTPUT\n\n"
                        else:
                            mensaje_final += f"⚠️ Error al registrar en OUTPUT\n\n"
                        
                        mensaje_final += f"📊 *ESTADO GENERAL:*\n"
                        mensaje_final += f"   ✅ Completados: {len(items_completados)}\n"
                        mensaje_final += f"   ⏳ Pendientes: {len(items_pendientes)}\n\n"
                        
                        if items_pendientes:
                            mensaje_final += f"💡 Items pendientes: {', '.join(items_pendientes)}\n"
                            mensaje_final += f"Envía 'listo [numero]' al terminar el siguiente."
                        else:
                            mensaje_final += f"🎉 *¡TODOS LOS TRABAJOS COMPLETADOS!*\n\nExcelente trabajo."
                            # Limpiar estado
                            del conversation_states[whatsapp_number]
                        
                        whatsapp_service.enviar_mensaje(whatsapp_number, mensaje_final)
                        
                        # LOG
                        sheets_service.registrar_log_whatsapp(
                            numero_telefono=whatsapp_number,
                            tipo_mensaje="enviado",
                            contenido=f"✅ Trabajo completado - Item #{item_actual_despues}",
                            tiene_media=True,
                            media_url=f"{len(urls_guardadas)} imágenes DESPUÉS",
                            item_relacionado=str(item_actual_despues),
                            estado_flujo="completado" if not items_pendientes else "multiple_en_progreso",
                            respuesta_bot=f"OUTPUT: {'SÍ' if registro_exitoso else 'NO'}"
                        )
                        
                        if whatsapp_number in conversation_states:
                            conversation_states[whatsapp_number] = estado_actual
                    
                    return "OK"
            
            # Detectar comando "listo [numero]" o "finalizado [numero]"
            if Body:
                body_lower = Body.lower().strip()
                numeros_en_mensaje = re.findall(r'\d+', Body)
                
                if numeros_en_mensaje and any(word in body_lower for word in ['listo', 'finalizado', 'terminado', 'complete', 'completado']):
                    numero_solicitado = numeros_en_mensaje[0]
                    items_activos = estado_actual.get('items_activos', {})
                    
                    if str(numero_solicitado) in items_activos:
                        item_info = items_activos[str(numero_solicitado)]
                        
                        if item_info['estado'] == 'en_espera':
                            # Item válido, pedir fotos DESPUÉS
                            estado_actual['item_actual_despues'] = numero_solicitado
                            items_activos[str(numero_solicitado)]['estado'] = 'recibiendo_despues'
                            conversation_states[whatsapp_number] = estado_actual
                            
                            whatsapp_service.enviar_mensaje(
                                whatsapp_number,
                                f"📸 *FOTOS DESPUÉS - ITEM #{numero_solicitado}*\n\n"
                                f"Envía 3 fotos del estado DESPUÉS del cartel #{numero_solicitado}.\n\n"
                                f"📷📷📷 Envía las 3 imágenes ahora."
                            )
                            return "OK"
                        elif item_info['estado'] == 'completado':
                            whatsapp_service.enviar_mensaje(
                                whatsapp_number,
                                f"ℹ️ El item #{numero_solicitado} ya está completado."
                            )
                            return "OK"
                        else:
                            whatsapp_service.enviar_mensaje(
                                whatsapp_number,
                                f"⚠️ El item #{numero_solicitado} aún no tiene fotos ANTES."
                            )
                            return "OK"
                    else:
                        whatsapp_service.enviar_mensaje(
                            whatsapp_number,
                            f"❌ El item #{numero_solicitado} no está en tu lista actual.\n\n"
                            f"Items activos: {', '.join(items_activos.keys())}"
                        )
                        return "OK"
            
            return "OK"
        
        # ===== MODO SIMPLE (LEGACY) =====
        if MediaUrl0 and estado_actual.get('estado') == 'esperando_imagenes_antes':
            # Usuario está enviando imágenes ANTES del trabajo
            print(f"📸 Recibiendo imagen ANTES del trabajo de {whatsapp_number}")
            
            # Descargar imagen
            auth = (os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
            image_data = await whatsapp_service.descargar_imagen(MediaUrl0, auth)
            
            if not image_data:
                whatsapp_service.enviar_mensaje(whatsapp_number, "❌ Error al descargar la imagen. Intenta nuevamente.")
                return "OK"
            
            # Agregar imagen a la lista
            estado_actual['imagenes_antes'].append(image_data)
            num_recibidas = len(estado_actual['imagenes_antes'])
            numero_item = estado_actual['numero_item']
            
            if num_recibidas < 3:
                # Pedir más imágenes
                whatsapp_service.enviar_mensaje(
                    whatsapp_number,
                    f"✅ Imagen {num_recibidas}/3 recibida para item #{numero_item}.\n\n📸 Envía la imagen {num_recibidas + 1} de 3."
                )
            else:
                # Tenemos las 3 imágenes, guardarlas en Drive
                whatsapp_service.enviar_mensaje(
                    whatsapp_number,
                    f"✅ 3 imágenes recibidas.\n\n⏳ Guardando en Drive..."
                )
                
                # Subir imágenes a carpeta Antes
                urls_guardadas = []
                item_formateado = str(numero_item).zfill(3)  # Formatear como 001, 002, etc.
                for idx, img_data in enumerate(estado_actual['imagenes_antes'], 1):
                    # Formato: XXX-001.jpg, XXX-002.jpg, XXX-003.jpg
                    filename = f"{item_formateado}-{str(idx).zfill(3)}.jpg"
                    url = sheets_service.subir_imagen_antes_despues(
                        img_data, 
                        filename, 
                        numero_item, 
                        'antes'
                    )
                    if url:
                        urls_guardadas.append(url)
                
                # Actualizar estado
                estado_actual['estado'] = 'en_trabajo'
                estado_actual['urls_imagenes_antes'] = urls_guardadas
                conversation_states[whatsapp_number] = estado_actual
                
                whatsapp_service.enviar_mensaje(
                    whatsapp_number,
                    f"✅ *IMÁGENES GUARDADAS*\n\n"
                    f"Las 3 imágenes del estado ANTES se han guardado correctamente en Drive.\n\n"
                    f"🔧 Ahora puedes proceder con el trabajo en el cartel #{numero_item}.\n\n"
                    f"Cuando termines, envía el mensaje *'listo'* o *'finalizado'* para registrar las imágenes DESPUÉS del trabajo."
                )
                
                # 📋 LOG: Registrar imágenes ANTES guardadas
                sheets_service.registrar_log_whatsapp(
                    numero_telefono=whatsapp_number,
                    tipo_mensaje="enviado",
                    contenido=f"3 imágenes ANTES guardadas para item #{numero_item}",
                    tiene_media=True,
                    media_url=f"{len(urls_guardadas)} imágenes en Drive",
                    item_relacionado=str(numero_item),
                    estado_flujo="en_trabajo",
                    respuesta_bot="Esperando finalización del trabajo"
                )
            
            return "OK"
        
        if MediaUrl0 and estado_actual.get('estado') == 'esperando_imagenes_despues':
            # Usuario está enviando imágenes DESPUÉS del trabajo
            print(f"📸 Recibiendo imagen DESPUÉS del trabajo de {whatsapp_number}")
            
            # Descargar imagen
            auth = (os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
            image_data = await whatsapp_service.descargar_imagen(MediaUrl0, auth)
            
            if not image_data:
                whatsapp_service.enviar_mensaje(whatsapp_number, "❌ Error al descargar la imagen. Intenta nuevamente.")
                return "OK"
            
            # Agregar imagen a la lista
            if 'imagenes_despues' not in estado_actual:
                estado_actual['imagenes_despues'] = []
            
            estado_actual['imagenes_despues'].append(image_data)
            num_recibidas = len(estado_actual['imagenes_despues'])
            numero_item = estado_actual['numero_item']
            
            if num_recibidas < 3:
                # Pedir más imágenes
                whatsapp_service.enviar_mensaje(
                    whatsapp_number,
                    f"✅ Imagen {num_recibidas}/3 recibida para item #{numero_item}.\n\n📸 Envía la imagen {num_recibidas + 1} de 3."
                )
            else:
                # Tenemos las 3 imágenes, guardarlas en Drive
                whatsapp_service.enviar_mensaje(
                    whatsapp_number,
                    f"✅ 3 imágenes recibidas.\n\n⏳ Guardando en Drive..."
                )
                
                # Subir imágenes a carpeta Despues
                urls_guardadas = []
                item_formateado = str(numero_item).zfill(3)  # Formatear como 001, 002, etc.
                for idx, img_data in enumerate(estado_actual['imagenes_despues'], 1):
                    # Formato: XXX-004.jpg, XXX-005.jpg, XXX-006.jpg (idx+3 porque DESPUÉS es 004-006)
                    filename = f"{item_formateado}-{str(idx + 3).zfill(3)}.jpg"
                    url = sheets_service.subir_imagen_antes_despues(
                        img_data, 
                        filename, 
                        numero_item, 
                        'despues'
                    )
                    if url:
                        urls_guardadas.append(url)
                
                # 🆕 REGISTRAR TRABAJO COMPLETADO EN PLANILLA OUTPUT
                cartel_info = estado_actual.get('cartel_info', {})
                registro_exitoso = sheets_service.registrar_trabajo_ecogas({
                    'numero_item': numero_item,
                    'cartel_info': cartel_info
                })
                
                # Mensaje de confirmación
                mensaje_final = (
                    f"✅ *TRABAJO COMPLETADO*\n\n"
                    f"Las 3 imágenes del estado DESPUÉS se han guardado correctamente en Drive.\n\n"
                )
                
                if registro_exitoso:
                    mensaje_final += f"📊 *Instalación EJECUTADA* registrada en planilla OUTPUT\n\n"
                else:
                    mensaje_final += f"⚠️ Advertencia: Error al registrar en planilla OUTPUT\n\n"
                
                mensaje_final += (
                    f"📋 Cartel #{numero_item} - Trabajo finalizado\n"
                    f"📸 Imágenes antes: {len(estado_actual.get('urls_imagenes_antes', []))}\n"
                    f"📸 Imágenes después: {len(urls_guardadas)}\n"
                    f"\n¡Excelente trabajo! 🎉"
                )
                
                whatsapp_service.enviar_mensaje(whatsapp_number, mensaje_final)
                
                # 📋 LOG: Registrar trabajo completado
                sheets_service.registrar_log_whatsapp(
                    numero_telefono=whatsapp_number,
                    tipo_mensaje="enviado",
                    contenido=f"✅ Trabajo completado - Item #{numero_item}",
                    tiene_media=True,
                    media_url=f"Total: {len(urls_guardadas)} imágenes DESPUÉS guardadas",
                    item_relacionado=str(numero_item),
                    estado_flujo="completado",
                    respuesta_bot=f"Registrado en OUTPUT: {'SÍ' if registro_exitoso else 'NO'}"
                )
                
                # Limpiar estado
                del conversation_states[whatsapp_number]
            
            return "OK"
        
        # Detectar comandos para finalizar trabajo
        if Body and estado_actual.get('estado') == 'en_trabajo':
            body_lower = Body.lower().strip()
            if any(word in body_lower for word in ['listo', 'finalizado', 'terminado', 'termine', 'completado']):
                # Pedir imágenes DESPUÉS del trabajo
                numero_item = estado_actual['numero_item']
                estado_actual['estado'] = 'esperando_imagenes_despues'
                conversation_states[whatsapp_number] = estado_actual
                
                whatsapp_service.enviar_mensaje(
                    whatsapp_number,
                    f"📸 *DESPUÉS DE FINALIZAR EL TRABAJO*\n\n"
                    f"Por favor, envía 3 fotos del estado del cartel #{numero_item} DESPUÉS de realizar el trabajo.\n\n"
                    f"Envía las 3 imágenes ahora. 📷📷📷"
                )
                return "OK"
        
        # Si el mensaje no tiene número de item, dar instrucciones
        if Body and not re.search(r'\d+', Body):
            whatsapp_service.enviar_mensaje(
                whatsapp_number,
                "👋 ¡Hola! Para trabajar en carteles:\n\n"
                "📝 *UN CARTEL:* Envía el número\n"
                "   Ejemplo: '190' o 'item 190'\n\n"
                "📝 *MÚLTIPLES CARTELES:* Envía varios números\n"
                "   Ejemplo: '277, 278, 279, 290'\n\n"
                "Te mostraré la información de cada cartel, pediré las fotos ANTES de todos.\n\n"
                "Cuando termines un trabajo, envía:\n"
                "*'listo [numero]'* o *'finalizado [numero]'*"
            )
        return "OK"
        
    except Exception as e:
        print(f"Error en webhook: {e}")
        return "OK"


async def procesar_solicitud_cartel(
    whatsapp_number: str,
    operario: str,
    mensaje: str,
    image_data: bytes,
    media_url: str,
    latitud: float,
    longitud: float,
    db: Session
):
    """
    Procesa la solicitud de reemplazo de cartel.
    """
    try:
        
        # Obtener todos los carteles primero para encontrar el más cercano
        carteles_ecogas = sheets_service.obtener_carteles_ecogas()
        
        # Buscar el cartel más cercano según la ubicación
        cartel_cercano = geo_service.encontrar_cartel_mas_cercano(
            latitud, 
            longitud, 
            carteles_ecogas,
            radio_max_km=5.0
        )
        
        # Subir imagen a Google Drive en carpeta del item
        drive_url = None
        if cartel_cercano:
            numero_item = cartel_cercano.get('numero', '0')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cartel_{numero_item}_{operario}_{timestamp}.jpg"
            drive_url = sheets_service.subir_imagen_a_drive(image_data, filename, numero_item)
            
            if drive_url:
                print(f"✅ Imagen subida a Drive: {drive_url}")
                # Actualizar enlace de carpeta en sheet
                sheets_service.actualizar_enlace_carpeta_item(numero_item)
            else:
                print("⚠️ No se pudo subir la imagen a Drive")
        
        if not drive_url:
            drive_url = media_url  # Usar URL de Twilio como fallback
        
        if cartel_cercano:
            # Responder con la información del cartel cercano
            distancia = cartel_cercano.get('distancia_km', 0)
            tipo = cartel_cercano.get('tipo_cartel', 'Desconocido')
            observaciones = cartel_cercano.get('observaciones', 'Sin especificar')
            gasoducto = cartel_cercano.get('gasoducto', 'Sin información')
            numero = cartel_cercano.get('numero', 'N/A')
            
            respuesta = (
                f"📍 *CARTEL IDENTIFICADO*\n\n"
                f"📋 Número: {numero}\n"
                f"📏 Distancia: {distancia} km\n"
                f"🏷️ Tipo: {tipo}\n"
                f"🔧 Acción a realizar: {observaciones}\n"
                f"🚰 Gasoducto: {gasoducto}\n\n"
                f"📸 Imagen almacenada en Drive\n\n"
                f"✅ Procede con la acción indicada."
            )
            
            # Enviar respuesta con información del cartel
            whatsapp_service.enviar_mensaje(whatsapp_number, respuesta)
            
            # Obtener y enviar las imágenes del cartel desde Drive
            imagenes = sheets_service.obtener_imagenes_cartel(numero)
            if imagenes:
                whatsapp_service.enviar_mensaje(
                    whatsapp_number,
                    f"📸 *IMÁGENES DE REFERENCIA DEL CARTEL #{numero}*\n\nEnviando {len(imagenes)} imagen(es)..."
                )
                for idx, imagen in enumerate(imagenes, 1):
                    url = imagen.get('url')
                    nombre = imagen.get('nombre', f'imagen_{idx}')
                    if url:
                        whatsapp_service.enviar_imagen(whatsapp_number, url, f"📷 {nombre}")
                        time.sleep(1)  # Pequeña pausa entre imágenes
                
                # Pausa adicional para asegurar que todas las imágenes se envíen
                time.sleep(2)
            else:
                whatsapp_service.enviar_mensaje(
                    whatsapp_number,
                    f"ℹ️ No se encontraron imágenes almacenadas para este cartel."
                )
            
            # Pedir imágenes ANTES de comenzar el trabajo (DESPUÉS de enviar las de referencia)
            whatsapp_service.enviar_mensaje(
                whatsapp_number,
                f"\n📸 *ANTES DE COMENZAR EL TRABAJO*\n\n"
                f"Por favor, envía 3 fotos del estado actual del cartel #{numero} ANTES de realizar cualquier trabajo.\n\n"
                f"Envía las 3 imágenes ahora. 📷📷📷"
            )
            
            # Actualizar estado de conversación
            conversation_states[whatsapp_number] = {
                'estado': 'esperando_imagenes_antes',
                'numero_item': numero,
                'imagenes_antes': [],
                'cartel_info': cartel_cercano
            }
            
            # Registrar en la base de datos
            registro = RegistroCartel(
                operario=operario,
                accion=observaciones,
                tipo_cartel=tipo,
                gasoducto=gasoducto,
                estado="en_proceso",
                latitud=latitud,
                longitud=longitud,
                direccion=geo_service.obtener_direccion(latitud, longitud),
                foto_url=drive_url,
                whatsapp_number=whatsapp_number,
                notas=f"Cartel #{numero}, Distancia: {distancia} km"
            )
            db.add(registro)
            db.commit()
            
            # Registrar en planilla ECOGAS
            sheets_service.registrar_trabajo_ecogas({
                'operario': operario,
                'tipo_cartel': tipo,
                'gasoducto': gasoducto,
                'accion': observaciones,
                'latitud': latitud,
                'longitud': longitud,
                'foto_url': drive_url,
                'whatsapp_number': whatsapp_number,
                'notas': f"Cartel #{numero}, Distancia: {distancia} km"
            })
            
        else:
            # No se encontró ningún cartel cercano
            respuesta = (
                f"⚠️ *NO SE ENCONTRÓ CARTEL CERCANO*\n\n"
                f"No hay carteles registrados en un radio de 5 km de tu ubicación.\n\n"
                f"📸 Imagen almacenada en Drive\n\n"
                f"Por favor, contacta al supervisor para verificar la ubicación."
            )
            
            # Registrar de todos modos para revisión
            registro = RegistroCartel(
                operario=operario,
                accion="Verificación de ubicación",
                tipo_cartel="Sin identificar",
                gasoducto="Sin información",
                estado="requiere_revision",
                latitud=latitud,
                longitud=longitud,
                direccion=geo_service.obtener_direccion(latitud, longitud),
                foto_url=drive_url,
                whatsapp_number=whatsapp_number,
                notas="No se encontró cartel cercano - Requiere revisión manual"
            )
            db.add(registro)
            db.commit()
            
            # Alertar al administrador
            whatsapp_service.enviar_alerta_admin(
                f"⚠️ UBICACIÓN SIN CARTEL REGISTRADO\n\n"
                f"Operario: {operario}\n"
                f"Ubicación: {latitud}, {longitud}\n"
                f"Imagen: {drive_url}"
            )
            
            # Enviar respuesta al operario
            whatsapp_service.enviar_mensaje(whatsapp_number, respuesta)
        
    except Exception as e:
        print(f"Error procesando solicitud: {e}")
        import traceback
        traceback.print_exc()
        whatsapp_service.enviar_mensaje(
            whatsapp_number,
            f"❌ Error al procesar tu solicitud: {str(e)}\n\nPor favor, intenta nuevamente."
        )


@app.get("/carteles", response_model=List[CartelResponse])
async def obtener_carteles(
    estado: Optional[str] = None,
    operario: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de registros de carteles.
    """
    query = db.query(RegistroCartel)
    
    if estado:
        query = query.filter(RegistroCartel.estado == estado)
    
    if operario:
        query = query.filter(RegistroCartel.operario == operario)
    
    return query.order_by(RegistroCartel.fecha_creacion.desc()).all()


@app.put("/carteles/{cartel_id}/estado")
async def actualizar_estado_cartel(
    cartel_id: int,
    nuevo_estado: str,
    db: Session = Depends(get_db)
):
    """
    Actualiza el estado de un cartel.
    """
    cartel = db.query(RegistroCartel).filter(RegistroCartel.id == cartel_id).first()
    
    if not cartel:
        raise HTTPException(status_code=404, detail="Cartel no encontrado")
    
    cartel.estado = nuevo_estado
    db.commit()
    
    return {"message": "Estado actualizado", "cartel_id": cartel_id, "nuevo_estado": nuevo_estado}


@app.get("/stock")
async def obtener_stock():
    """
    Obtiene el stock actual desde Google Sheets.
    """
    stock = sheets_service.obtener_stock()
    return {"stock": stock, "total_items": len(stock)}


@app.get("/stock/alertas", response_model=List[StockAlert])
async def obtener_alertas_stock(threshold: int = 10):
    """
    Obtiene alertas de stock bajo.
    """
    return sheets_service.verificar_stock_bajo(threshold)


@app.get("/acciones-autorizadas")
async def obtener_acciones_autorizadas():
    """
    Obtiene la lista de acciones viales autorizadas.
    """
    acciones = sheets_service.obtener_acciones_autorizadas()
    return {"acciones": acciones, "total": len(acciones)}


@app.get("/health")
async def health_check():
    """
    Verifica el estado de los servicios.
    """
    return {
        "status": "healthy",
        "services": {
            "database": "ok",
            "gemini": "ok" if os.getenv("GEMINI_API_KEY") else "not_configured",
            "whatsapp": "ok" if os.getenv("TWILIO_ACCOUNT_SID") else "not_configured",
            "sheets": "ok" if os.path.exists(os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "credentials.json")) else "not_configured"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000"))
    )
