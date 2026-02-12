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
        
        # FLUJO PRINCIPAL: Detectar número de ítem en el mensaje
        import re
        if Body and re.search(r'\d+', Body):
            print(f"🔍 Detectado número de ítem en mensaje: {Body}")
            
            # Extraer el número
            match = re.search(r'\d+', Body)
            if match:
                item_number = match.group()
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
🏷️ Tipo: {tipo_info}
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
                
                return "OK"
        
        # MANEJO DE IMÁGENES SEGÚN ESTADO DE CONVERSACIÓN
        estado_actual = conversation_states.get(whatsapp_number, {})
        
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
                "👋 ¡Hola! Para trabajar en un cartel:\n\n"
                "📝 Envía el *número de item* del cartel\n"
                "Ejemplo: 'item 5' o solo '5'\n\n"
                "Te mostraré la información del cartel y te pediré las fotos ANTES y DESPUÉS del trabajo."
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
