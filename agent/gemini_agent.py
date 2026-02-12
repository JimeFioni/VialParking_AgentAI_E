import google.generativeai as genai
import os
from typing import Optional, Dict, Any
from PIL import Image
import io
import base64
from dotenv import load_dotenv

load_dotenv()


class GeminiAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
    async def analizar_cartel(
        self, 
        image_data: bytes, 
        texto_mensaje: str,
        acciones_autorizadas: list,
        tipos_carteles: list = None
    ) -> Dict[str, Any]:
        """
        Analiza la imagen de un cartel de señalización de gasoducto y determina la acción.
        
        Args:
            image_data: Bytes de la imagen
            texto_mensaje: Mensaje del operario
            acciones_autorizadas: Lista de acciones autorizadas
            tipos_carteles: Lista de tipos de carteles disponibles
        
        Returns:
            Diccionario con la decisión del agente
        """
        try:
            # Convertir imagen
            image = Image.open(io.BytesIO(image_data))
            
            # Crear lista de acciones para el prompt
            acciones_str = "\n".join([f"- {accion}" for accion in acciones_autorizadas])
            
            tipos_str = ""
            if tipos_carteles:
                tipos_str = "\n\nTIPOS DE CARTELES DISPONIBLES:\n" + "\n".join([f"- {tipo}" for tipo in tipos_carteles])
            
            prompt = f"""Eres un agente experto en señalización de redes de gas natural para el distribuidor ECOGAS. 

Tu tarea es analizar la imagen de un cartel de señalización de gasoducto y determinar:

1. ¿Qué tipo de cartel de señalización se observa en la imagen?
2. ¿El cartel necesita ser reemplazado? (evalúa: deterioro, decoloración, daños, visibilidad, oxidación)
3. ¿La acción corresponde a alguna de las acciones autorizadas?

ACCIONES AUTORIZADAS:
{acciones_str}
{tipos_str}

MENSAJE DEL OPERARIO: {texto_mensaje}

CONTEXTO: Estos carteles señalizan la red de distribución de gas natural de ECOGAS. 
Incluyen señalización de gasoductos, ramales, válvulas, estaciones reguladoras, etc.

INSTRUCCIONES:
- Identifica el tipo exacto de cartel (ej: "Señal de Gasoducto", "Válvula de Corte", "Estación Reguladora", etc.)
- Evalúa si el estado del cartel justifica su reemplazo (deterioro, visibilidad reducida, daños estructurales)
- Verifica si la acción está en la lista de autorizadas
- Sé estricto: solo autoriza si hay certeza y necesidad real de reemplazo

Responde en formato JSON:
{{
    "tipo_cartel": "nombre del cartel identificado",
    "estado_cartel": "descripción del estado actual",
    "requiere_reemplazo": true/false,
    "accion_autorizada": "nombre exacto de la acción autorizada o null",
    "gasoducto": "nombre del gasoducto/ramal mencionado o detectado, o null",
    "autorizado": true/false,
    "confianza": 0.0-1.0,
    "razon": "explicación de la decisión",
    "observaciones": "detalles adicionales sobre el estado del cartel"
}}"""

            # Generar respuesta
            response = self.model.generate_content([prompt, image])
            
            # Parsear respuesta
            response_text = response.text.strip()
            
            # Limpiar la respuesta si viene con markdown
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            import json
            resultado = json.loads(response_text)
            
            return {
                "autorizado": resultado.get("autorizado", False),
                "accion": resultado.get("accion_autorizada"),
                "tipo_cartel": resultado.get("tipo_cartel"),
                "gasoducto": resultado.get("gasoducto"),
                "confianza": resultado.get("confianza", 0.0),
                "razon": resultado.get("razon", ""),
                "requiere_stock": resultado.get("requiere_reemplazo", True),
                "detalles": {
                    "estado_cartel": resultado.get("estado_cartel"),
                    "observaciones": resultado.get("observaciones")
                }
            }
            
        except Exception as e:
            return {
                "autorizado": False,
                "accion": None,
                "tipo_cartel": None,
                "gasoducto": None,
                "confianza": 0.0,
                "razon": f"Error al analizar la imagen: {str(e)}",
                "requiere_stock": False,
                "detalles": {}
            }
    
    async def extraer_ubicacion_texto(self, texto: str) -> Optional[Dict[str, float]]:
        """
        Intenta extraer información de ubicación del texto usando Gemini.
        """
        try:
            prompt = f"""Analiza el siguiente mensaje y extrae información de ubicación (dirección, calle, esquina, etc):

MENSAJE: {texto}

Si encuentras información de ubicación, responde en JSON:
{{
    "direccion": "dirección encontrada",
    "tiene_ubicacion": true
}}

Si NO hay información de ubicación clara, responde:
{{
    "tiene_ubicacion": false
}}"""

            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            import json
            resultado = json.loads(response_text)
            
            return resultado if resultado.get("tiene_ubicacion") else None
            
        except:
            return None

    async def generar_respuesta_whatsapp(
        self, 
        decision: Dict[str, Any],
        operario: str
    ) -> str:
        """
        Genera una respuesta amigable para enviar por WhatsApp.
        """
        if decision["autorizado"]:
            gasoducto_info = f"\n🔧 *Gasoducto:* {decision['gasoducto']}" if decision.get('gasoducto') else ""
            
            return f"""✅ *ACCIÓN AUTORIZADA - ECOGAS*

Hola {operario}, tu solicitud ha sido aprobada.

📋 *Acción:* {decision['accion']}
🚧 *Cartel:* {decision['tipo_cartel']}{gasoducto_info}
✨ *Confianza:* {decision['confianza']*100:.0f}%

📍 Ubicación registrada correctamente.
📦 Se actualizará el stock automáticamente.

Procede con el reemplazo del cartel de señalización. ¡Buen trabajo!"""
        else:
            return f"""⚠️ *ACCIÓN NO AUTORIZADA*

Hola {operario}, tu solicitud no puede ser aprobada.

❌ *Razón:* {decision['razon']}

Por favor, verifica:
- Que el cartel esté en la lista de acciones autorizadas
- Que la imagen sea clara y muestre el cartel completo
- Que realmente requiera reemplazo
- Que corresponda a señalización de red de gas ECOGAS

Contacta al supervisor si necesitas asistencia."""
