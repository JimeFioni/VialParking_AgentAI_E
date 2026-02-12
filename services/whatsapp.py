import os
from dotenv import load_dotenv
from typing import Optional, Dict
import httpx
import json
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging
import time
from datetime import datetime
from functools import wraps

load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('whatsapp_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def retry_on_failure(max_retries=3, delay=2):
    """Decorador para reintentar operaciones fallidas"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"❌ Falló después de {max_retries} intentos: {e}")
                        raise
                    logger.warning(f"⚠️ Intento {attempt + 1} falló, reintentando en {delay}s...")
                    time.sleep(delay * (attempt + 1))
            return None
        return wrapper
    return decorator


class WhatsAppService:
    def __init__(self):
        # Configuración Twilio
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        
        if not self.account_sid or not self.auth_token:
            logger.error("❌ Credenciales de Twilio no configuradas")
            raise ValueError("Credenciales de Twilio no configuradas (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)")
        
        self.client = Client(self.account_sid, self.auth_token)
        
        # Métricas de uso
        self.mensajes_enviados = 0
        self.mensajes_fallidos = 0
        self.ultima_actividad = datetime.now()
        
        logger.info(f"✅ WhatsAppService inicializado correctamente con número: {self.twilio_number}")
    
    def _normalizar_numero(self, numero: str) -> str:
        """
        Normaliza un número de teléfono al formato de Twilio.
        
        Args:
            numero: Número en cualquier formato
            
        Returns:
            Número en formato whatsapp:+549XXXXXXXXXX
        """
        if not numero:
            raise ValueError("Número de teléfono vacío")
        
        # Limpiar el número
        clean_number = numero.replace("whatsapp:", "").replace("+", "").replace(" ", "").replace("-", "")
        
        # Asegurar formato correcto
        if not clean_number.startswith("whatsapp:"):
            numero_formateado = f"whatsapp:+{clean_number}"
        else:
            numero_formateado = numero
        
        logger.debug(f"📱 Número normalizado: {numero} -> {numero_formateado}")
        return numero_formateado
    
    @retry_on_failure(max_retries=3, delay=2)
    def enviar_mensaje(self, to_number: str, mensaje: str) -> bool:
        """
        Envía un mensaje de WhatsApp usando Twilio.
        
        Args:
            to_number: Número de destino en formato +549XXXXXXXXXX o whatsapp:+549XXXXXXXXXX
            mensaje: Texto del mensaje
        
        Returns:
            True si se envió correctamente
        """
        try:
            # Validar mensaje
            if not mensaje or len(mensaje.strip()) == 0:
                logger.warning("⚠️ Intento de enviar mensaje vacío")
                return False
            
            if len(mensaje) > 1600:
                logger.warning(f"⚠️ Mensaje muy largo ({len(mensaje)} caracteres), será truncado")
                mensaje = mensaje[:1600]
            
            # Normalizar número
            to_number = self._normalizar_numero(to_number)
            
            # Enviar mensaje con Twilio
            logger.info(f"📤 Enviando mensaje a {to_number}: {mensaje[:50]}...")
            
            message = self.client.messages.create(
                from_=self.twilio_number,
                body=mensaje,
                to=to_number
            )
            
            self.mensajes_enviados += 1
            self.ultima_actividad = datetime.now()
            
            logger.info(f"✅ Mensaje enviado exitosamente - SID: {message.sid} - Status: {message.status}")
            return True
            
        except TwilioRestException as e:
            self.mensajes_fallidos += 1
            logger.error(f"❌ Error de Twilio al enviar mensaje: {e.code} - {e.msg}")
            return False
        except Exception as e:
            self.mensajes_fallidos += 1
            logger.error(f"❌ Error inesperado al enviar mensaje: {type(e).__name__}: {e}")
            return False
    
    def enviar_alerta_admin(self, mensaje: str) -> bool:
        """
        Envía una alerta al administrador.
        """
        admin_number = os.getenv("ADMIN_WHATSAPP_NUMBER")
        if not admin_number:
            logger.warning("⚠️ Número de admin no configurado, no se puede enviar alerta")
            return False
        
        mensaje_formateado = f"🔔 *ALERTA SISTEMA ECOGAS*\n\n{mensaje}\n\n_Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}_"
        
        logger.info(f"🚨 Enviando alerta a admin: {mensaje[:50]}...")
        return self.enviar_mensaje(admin_number, mensaje_formateado)
    
    async def descargar_imagen(self, media_url: str, auth: tuple = None) -> Optional[bytes]:
        """
        Descarga una imagen desde Twilio.
        
        Args:
            media_url: URL del media de Twilio
            auth: Tupla (account_sid, auth_token) para autenticación
        
        Returns:
            Bytes de la imagen o None
        """
        # Intentar método 1: httpx directo
        try:
            if auth is None:
                auth = (self.account_sid, self.auth_token)
            
            logger.info(f"📥 Descargando imagen desde: {media_url[:80]}...")
            
            # Configurar límites más amplios para conexiones
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            
            # Timeout más amplio para redes lentas y redirects
            timeout = httpx.Timeout(30.0, connect=15.0, read=30.0)
            
            async with httpx.AsyncClient(
                follow_redirects=True, 
                timeout=timeout,
                limits=limits,
                verify=True  # Verificar SSL
            ) as client:
                try:
                    # Primera petición con auth para obtener la URL real
                    response = await client.get(
                        media_url,
                        auth=auth
                    )
                    
                    logger.info(f"📍 Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        image_size = len(response.content)
                        logger.info(f"✅ Imagen descargada exitosamente: {image_size / 1024:.2f} KB")
                        return response.content
                    else:
                        logger.error(f"❌ Error al descargar imagen: Status {response.status_code}")
                        # Intentar leer respuesta de error
                        try:
                            error_body = response.text[:200]
                            logger.error(f"   Respuesta: {error_body}")
                        except:
                            pass
                        return None
                        
                except httpx.ConnectError as ce:
                    logger.warning(f"⚠️ Error de conexión con httpx, intentando método alternativo...")
                    logger.error(f"   Error: {ce}")
                    # Intentar método alternativo
                    return await self._descargar_imagen_alternativa(media_url)
                
        except httpx.TimeoutException as te:
            logger.error(f"❌ Timeout al descargar imagen: {te}")
            # Intentar método alternativo
            logger.warning(f"⚠️ Intentando método alternativo después de timeout...")
            return await self._descargar_imagen_alternativa(media_url)
        except Exception as e:
            logger.error(f"❌ Excepción al descargar imagen: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            # Intentar método alternativo
            return await self._descargar_imagen_alternativa(media_url)
    
    async def _descargar_imagen_alternativa(self, media_url: str) -> Optional[bytes]:
        """
        Método alternativo de descarga usando requests síncrono.
        Se usa como fallback cuando httpx falla.
        """
        try:
            import requests
            logger.info("🔄 Intentando descarga con método alternativo (requests)...")
            
            # Usar requests que a veces maneja mejor los redirects de Twilio
            response = requests.get(
                media_url,
                auth=(self.account_sid, self.auth_token),
                timeout=30,
                allow_redirects=True,
                verify=True
            )
            
            if response.status_code == 200:
                image_size = len(response.content)
                logger.info(f"✅ Imagen descargada con método alternativo: {image_size / 1024:.2f} KB")
                return response.content
            else:
                logger.error(f"❌ Método alternativo también falló: Status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Método alternativo falló: {type(e).__name__}: {e}")
            return None
    
    @retry_on_failure(max_retries=2, delay=3)
    def enviar_imagen(self, to_number: str, media_url: str, caption: str = "") -> bool:
        """
        Envía una imagen de WhatsApp usando Twilio.
        
        Args:
            to_number: Número de destino en formato +549XXXXXXXXXX o whatsapp:+549XXXXXXXXXX
            media_url: URL pública de la imagen (debe ser accesible por Twilio)
            caption: Texto opcional que acompaña la imagen
        
        Returns:
            True si se envió correctamente
        """
        try:
            # Normalizar número
            to_number = self._normalizar_numero(to_number)
            
            logger.info(f"📤 Enviando imagen a {to_number} - URL: {media_url[:50]}...")
            
            # Enviar imagen con Twilio
            message = self.client.messages.create(
                from_=self.twilio_number,
                media_url=[media_url],
                body=caption,
                to=to_number
            )
            
            self.mensajes_enviados += 1
            self.ultima_actividad = datetime.now()
            
            logger.info(f"✅ Imagen enviada exitosamente - SID: {message.sid}")
            return True
            
        except TwilioRestException as e:
            self.mensajes_fallidos += 1
            logger.error(f"❌ Error de Twilio al enviar imagen: {e.code} - {e.msg}")
            return False
        except Exception as e:
            self.mensajes_fallidos += 1
            logger.error(f"❌ Error inesperado al enviar imagen: {type(e).__name__}: {e}")
            return False
    
    def obtener_estadisticas(self) -> Dict:
        """
        Obtiene estadísticas de uso del servicio.
        
        Returns:
            Diccionario con métricas
        """
        tasa_exito = (self.mensajes_enviados / (self.mensajes_enviados + self.mensajes_fallidos) * 100) if (self.mensajes_enviados + self.mensajes_fallidos) > 0 else 0
        
        return {
            "mensajes_enviados": self.mensajes_enviados,
            "mensajes_fallidos": self.mensajes_fallidos,
            "tasa_exito": f"{tasa_exito:.2f}%",
            "ultima_actividad": self.ultima_actividad.strftime('%d/%m/%Y %H:%M:%S'),
            "numero_twilio": self.twilio_number
        }
    
    def health_check(self) -> Dict:
        """
        Verifica el estado del servicio.
        
        Returns:
            Estado del servicio
        """
        try:
            # Intentar obtener información de la cuenta
            account = self.client.api.accounts(self.account_sid).fetch()
            
            return {
                "status": "healthy",
                "account_status": account.status,
                "mensaje": "Servicio WhatsApp funcionando correctamente"
            }
        except Exception as e:
            logger.error(f"❌ Health check falló: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "mensaje": "Error al conectar con Twilio"
            }

