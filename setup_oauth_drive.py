#!/usr/bin/env python3
"""
Script para configurar OAuth 2.0 para Google Drive.
Genera el archivo token_drive.pickle necesario para subir imágenes.
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# SCOPE COMPLETO para acceder a Drive Y Google Sheets
# Necesario para:
# - Leer/escribir en carpetas de Drive (imágenes de muestra 001-287)
# - Leer/escribir en Google Sheets (planillas de acciones, database, etc.)
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

def setup_oauth():
    """Configura OAuth para Drive y guarda el token"""
    creds = None
    
    # Verificar si ya existe un token
    if os.path.exists('token_drive.pickle'):
        print("🔍 Token existente encontrado, verificando...")
        with open('token_drive.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # Si no hay credenciales válidas, iniciar flujo OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Intentando refrescar token expirado...")
            try:
                creds.refresh(Request())
                print("✅ Token refrescado exitosamente")
            except Exception as e:
                print(f"❌ Error al refrescar: {e}")
                print("🔄 Iniciando nuevo flujo OAuth...")
                creds = None
        
        if not creds:
            # Leer credenciales OAuth desde archivo o variable
            credentials_path = 'credentials_oauth.json'
            
            if not os.path.exists(credentials_path):
                print(f"❌ No se encuentra {credentials_path}")
                print("Descarga las credenciales OAuth desde Google Cloud Console")
                return False
            
            print("🔐 Iniciando flujo de autenticación OAuth...")
            print("Se abrirá tu navegador para autorizar el acceso a Drive")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, 
                SCOPES
            )
            # IMPORTANTE: access_type='offline' para obtener refresh_token de larga duración
            # prompt='consent' fuerza a re-aprobar, asegurando un refresh_token nuevo
            creds = flow.run_local_server(
                port=0,
                access_type='offline',
                prompt='consent'
            )
            print("✅ Autenticación completada con refresh_token")
            
            # Verificar que tenemos refresh_token
            if not hasattr(creds, 'refresh_token') or not creds.refresh_token:
                print("⚠️ ADVERTENCIA: No se obtuvo refresh_token")
                print("   El token expirará en 1 hora sin posibilidad de renovación automática")
            else:
                print("✅ Refresh token obtenido - Se renovará automáticamente por ~6 meses")
        
        # Guardar token para futuros usos
        with open('token_drive.pickle', 'wb') as token:
            pickle.dump(creds, token)
        print(f"💾 Token guardado en: token_drive.pickle")
        
        # Mostrar información del token
        if hasattr(creds, 'expiry'):
            print(f"📅 Token válido hasta: {creds.expiry}")
    else:
        print("✅ Token válido encontrado")
        if hasattr(creds, 'expiry'):
            print(f"📅 Válido hasta: {creds.expiry}")
    
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("🔧 Configuración OAuth 2.0 para Google Drive")
    print("=" * 70)
    print()
    
    success = setup_oauth()
    
    if success:
        print()
        print("=" * 70)
        print("✅ Configuración completada exitosamente")
        print("=" * 70)
        print()
        print("📝 Próximos pasos:")
        print("  1. El archivo token_drive.pickle ha sido creado/actualizado")
        print("  2. Puedes usar el dashboard normalmente")
        print("  3. Las imágenes se subirán correctamente a Drive")
        print()
    else:
        print()
        print("=" * 70)
        print("❌ Error en la configuración")
        print("=" * 70)
        print()
        print("Verifica que el archivo credentials_oauth.json existe")
