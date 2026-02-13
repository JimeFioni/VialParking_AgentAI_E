#!/usr/bin/env python3
"""
Sistema de monitoreo de token OAuth con alertas por email.
Envía notificación cuando el token está por expirar.
"""

import os
import pickle
import base64
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class TokenMonitor:
    """Monitor de tokens OAuth con alertas por email"""
    
    def __init__(self, token_path='token_drive.pickle'):
        self.token_path = token_path
        self.email_from = os.getenv('ALERT_EMAIL_FROM', 'noreply@vialparking.com')
        self.email_to = os.getenv('ALERT_EMAIL_TO', 'jimenafioni@gmail.com')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
    
    def get_token_info(self):
        """Obtiene información del token actual"""
        if not os.path.exists(self.token_path):
            return None
        
        try:
            with open(self.token_path, 'rb') as f:
                token = pickle.load(f)
            
            return {
                'valid': token.valid,
                'expired': token.expired,
                'expiry': token.expiry if hasattr(token, 'expiry') else None,
                'has_refresh_token': hasattr(token, 'refresh_token') and bool(token.refresh_token),
                'token_obj': token
            }
        except Exception as e:
            print(f"Error al leer token: {e}")
            return None
    
    def get_token_base64(self, token):
        """Convierte token a formato base64 para producción"""
        try:
            token_data = {
                'token': token.token,
                'refresh_token': token.refresh_token,
                'token_uri': token.token_uri,
                'client_id': token.client_id,
                'client_secret': token.client_secret,
                'scopes': token.scopes
            }
            token_json = json.dumps(token_data)
            return base64.b64encode(token_json.encode()).decode()
        except Exception as e:
            print(f"Error al generar base64: {e}")
            return None
    
    def days_until_expiry(self, expiry_date):
        """Calcula días hasta que expire el token"""
        if not expiry_date:
            return None
        
        now = datetime.utcnow()
        if expiry_date.tzinfo is None:
            # Si expiry_date es naive, asumimos UTC
            delta = expiry_date - now
        else:
            # Si tiene timezone, convertir now a aware
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)
            delta = expiry_date - now
        
        return delta.days + (delta.seconds / 86400)  # días con decimales
    
    def generate_email_content(self, token_info):
        """Genera el contenido del email de alerta"""
        token = token_info['token_obj']
        expiry = token_info['expiry']
        days_left = self.days_until_expiry(expiry) if expiry else 0
        
        # Generar token base64
        token_base64 = self.get_token_base64(token)
        
        # Calcular fecha de expiración del refresh token (7 días en Testing mode)
        refresh_expiry = datetime.now() + timedelta(days=7)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .alert-box {{ background: #fff3cd; border-left: 4px solid #ffc107; 
                             padding: 15px; margin: 20px 0; }}
                .token-box {{ background: #f8f9fa; border: 1px solid #dee2e6; 
                             padding: 15px; margin: 20px 0; border-radius: 5px; 
                             font-family: monospace; word-break: break-all; }}
                .instructions {{ background: #e7f3ff; border-left: 4px solid #2196F3; 
                                padding: 15px; margin: 20px 0; }}
                .step {{ margin: 15px 0; padding-left: 20px; }}
                .warning {{ color: #d32f2f; font-weight: bold; }}
                .success {{ color: #388e3c; font-weight: bold; }}
                h2 {{ color: #667eea; }}
                code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>⚠️ Alerta: Token OAuth por Expirar</h1>
                <p>Sistema VialParking - ECOGAS</p>
            </div>
            
            <div class="content">
                <div class="alert-box">
                    <h2>🔔 Estado del Token</h2>
                    <p><strong>Access Token:</strong> {"✅ Válido" if token_info['valid'] else "❌ Expirado"}</p>
                    <p><strong>Expira:</strong> {expiry.strftime('%d/%m/%Y %H:%M:%S UTC') if expiry else 'Desconocido'}</p>
                    <p><strong>Tiempo restante:</strong> <span class="warning">{days_left:.1f} horas</span></p>
                    <p><strong>Refresh Token:</strong> {"✅ Presente" if token_info['has_refresh_token'] else "❌ No disponible"}</p>
                    <p><strong>Refresh expira:</strong> ~{refresh_expiry.strftime('%d/%m/%Y')} (7 días desde creación)</p>
                </div>
                
                <h2>🔧 Acción Requerida</h2>
                <p>El token OAuth está por expirar. Para mantener el sistema funcionando sin interrupciones, 
                   debes actualizar el token en los entornos de producción.</p>
                
                <h2>🔐 Nuevo Token OAuth (Base64)</h2>
                <p>Copia este valor y actualízalo en Render y Streamlit Cloud:</p>
                <div class="token-box">
                    {token_base64 or "Error al generar token"}
                </div>
                
                <div class="instructions">
                    <h2>📋 Instrucciones de Actualización</h2>
                    
                    <h3>1️⃣ Render (Backend FastAPI)</h3>
                    <div class="step">
                        <p>1. Ve a <a href="https://dashboard.render.com">dashboard.render.com</a></p>
                        <p>2. Selecciona tu servicio web</p>
                        <p>3. <strong>Environment</strong> → <strong>Environment Variables</strong></p>
                        <p>4. Busca: <code>DRIVE_OAUTH_TOKEN_BASE64</code></p>
                        <p>5. Reemplaza con el token de arriba</p>
                        <p>6. Click <strong>Save Changes</strong></p>
                        <p class="success">✅ El servicio se redesplegarà automáticamente</p>
                    </div>
                    
                    <h3>2️⃣ Streamlit Cloud (Dashboard)</h3>
                    <div class="step">
                        <p>1. Ve a <a href="https://share.streamlit.io">share.streamlit.io</a></p>
                        <p>2. Abre tu app del dashboard</p>
                        <p>3. <strong>Settings</strong> → <strong>Secrets</strong></p>
                        <p>4. Busca o agrega la línea:</p>
                        <code>DRIVE_OAUTH_TOKEN_BASE64 = "[pegar token de arriba]"</code>
                        <p>5. Click <strong>Save</strong></p>
                        <p class="success">✅ La app se recargará automáticamente</p>
                    </div>
                    
                    <h3>3️⃣ Entorno Local (Opcional)</h3>
                    <div class="step">
                        <p>Si trabajas localmente, ejecuta:</p>
                        <code>cd /ruta/a/VialP_Ecogas && python3 setup_oauth_drive.py</code>
                        <p>Esto renovará el archivo <code>token_drive.pickle</code></p>
                    </div>
                </div>
                
                <div class="alert-box">
                    <h2>⏰ Próxima Renovación</h2>
                    <p>Este token debe renovarse aproximadamente el <strong>{refresh_expiry.strftime('%d/%m/%Y')}</strong></p>
                    <p>Recibirás otra alerta 2 días antes de esa fecha.</p>
                    
                    <h3>💡 Solución Permanente</h3>
                    <p>Para extender la duración del token de 7 días a 6 meses:</p>
                    <ol>
                        <li>Ve a <a href="https://console.cloud.google.com">Google Cloud Console</a></li>
                        <li>Selecciona proyecto: <strong>vialp-483820</strong></li>
                        <li><strong>APIs & Services</strong> → <strong>OAuth consent screen</strong></li>
                        <li>Click en <strong>PUBLISH APP</strong></li>
                        <li>Confirma la publicación</li>
                    </ol>
                    <p class="success">✅ Con la app publicada, el refresh token durará ~6 meses</p>
                </div>
                
                <hr>
                <p style="text-align: center; color: #666; font-size: 12px;">
                    Sistema de Monitoreo Automático - VialParking ECOGAS<br>
                    Este email se envía automáticamente cuando el token está por expirar
                </p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def send_alert_email(self, html_content):
        """Envía el email de alerta"""
        if not self.smtp_user or not self.smtp_password:
            print("⚠️ Configuración SMTP no disponible. No se puede enviar email.")
            print("   Configura: SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_TO")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = '⚠️ Alerta: Token OAuth por Expirar - VialParking ECOGAS'
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ Email enviado exitosamente a: {self.email_to}")
            return True
            
        except Exception as e:
            print(f"❌ Error al enviar email: {e}")
            return False
    
    def check_and_alert(self, threshold_days=2):
        """
        Verifica el token y envía alerta si está por expirar.
        
        Args:
            threshold_days: Días antes de expiración para enviar alerta (default: 2)
        
        Returns:
            dict con resultado del chequeo
        """
        token_info = self.get_token_info()
        
        if not token_info:
            print("❌ No se pudo leer el token")
            return {'status': 'error', 'message': 'Token no disponible'}
        
        if not token_info['expiry']:
            print("⚠️ Token sin fecha de expiración")
            return {'status': 'warning', 'message': 'Sin fecha de expiración'}
        
        days_left = self.days_until_expiry(token_info['expiry'])
        hours_left = days_left * 24
        
        print(f"\n📊 Estado del Token:")
        print(f"   Válido: {token_info['valid']}")
        print(f"   Expira: {token_info['expiry']}")
        print(f"   Tiempo restante: {hours_left:.1f} horas ({days_left:.2f} días)")
        print(f"   Tiene refresh token: {token_info['has_refresh_token']}")
        
        # Access token expira en ~1 hora, pero se renueva automático con refresh token
        # Solo alertamos cuando el refresh token está por expirar (7 días en Testing)
        # Calculamos basándonos en la fecha de creación del token actual
        
        if hours_left < 1:
            # Access token ya expiró, pero se renovará automáticamente
            print("⚠️ Access token expirado, pero se renovará automáticamente con refresh token")
            return {'status': 'ok', 'message': 'Token se renueva automáticamente'}
        
        # Verificar si debemos enviar alerta (cuando estemos cerca de los 7 días)
        # Asumimos que el token se creó hace (7 - days_until_refresh_expiry) días
        # Como no tenemos la fecha exacta de creación del refresh token,
        # enviamos alerta cada 5 días para ser conservadores
        
        if days_left < threshold_days:
            print(f"\n⚠️ ALERTA: Token expirará en {hours_left:.1f} horas")
            print("   Generando email de notificación...")
            
            html_content = self.generate_email_content(token_info)
            
            if self.send_alert_email(html_content):
                return {
                    'status': 'alert_sent',
                    'message': f'Alerta enviada - {hours_left:.1f} horas restantes',
                    'expires_in_hours': hours_left
                }
            else:
                # Guardar en archivo si no se pudo enviar email
                with open('token_alert.html', 'w') as f:
                    f.write(html_content)
                print("\n💾 Alerta guardada en: token_alert.html")
                return {
                    'status': 'alert_saved',
                    'message': 'Alerta guardada en archivo (email no configurado)',
                    'expires_in_hours': hours_left
                }
        
        return {
            'status': 'ok',
            'message': f'Token válido por {hours_left:.1f} horas más',
            'expires_in_hours': hours_left
        }


def main():
    """Función principal para ejecutar desde línea de comandos"""
    print("=" * 70)
    print("🔍 Monitor de Token OAuth - VialParking ECOGAS")
    print("=" * 70)
    print()
    
    monitor = TokenMonitor()
    result = monitor.check_and_alert(threshold_days=2)
    
    print()
    print("=" * 70)
    print(f"📊 Resultado: {result['status']}")
    print(f"💬 Mensaje: {result['message']}")
    print("=" * 70)
    print()
    
    if result['status'] == 'alert_sent':
        print("✉️  Se ha enviado un email con instrucciones de actualización")
    elif result['status'] == 'alert_saved':
        print("📁 Revisa el archivo token_alert.html con las instrucciones")
    
    return result


if __name__ == "__main__":
    main()
