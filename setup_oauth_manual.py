#!/usr/bin/env python3
"""
Script para configurar OAuth 2.0 para Google Drive - Versión Manual
Genera el archivo token_drive.pickle para autorizaciones con problemas de SSL
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive']

def setup_oauth_manual():
    """Configura OAuth para Drive usando flujo manual (sin SSL)"""
    credentials_path = 'credentials_oauth.json'
    
    if not os.path.exists(credentials_path):
        print(f"❌ No se encuentra {credentials_path}")
        return False
    
    print("=" * 70)
    print("🔧 Configuración OAuth 2.0 Manual para Google Drive")
    print("=" * 70)
    print()
    
    flow = InstalledAppFlow.from_client_secrets_file(
        credentials_path,
        SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob'  # Flujo manual
    )
    
    # Generar URL de autorización
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )
    
    print("📋 PASO 1: Abre esta URL en tu navegador:")
    print()
    print(auth_url)
    print()
    print("📋 PASO 2: Autoriza el acceso a Google Drive")
    print()
    print("📋 PASO 3: Copia el código de autorización que aparece")
    print()
    
    code = input("📝 Pega el código de autorización aquí: ").strip()
    
    if not code:
        print("❌ No se proporcionó ningún código")
        return False
    
    print()
    print("🔄 Canjeando código por token...")
    
    try:
        # Deshabilitar verificación SSL temporalmente para el intercambio de tokens
        import urllib3
        urllib3.disable_warnings()
        
        # Importar y configurar requests con verificación deshabilitada
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # Crear sesión personalizada sin verificación SSL
        session = requests.Session()
        session.verify = False
        
        # Sobrescribir la sesión de OAuth
        flow.oauth2session.verify = False
        
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Guardar token
        with open('token_drive.pickle', 'wb') as token:
            pickle.dump(creds, token)
        
        print("✅ Token generado y guardado exitosamente")
        print(f"💾 Archivo: token_drive.pickle")
        
        if hasattr(creds, 'expiry'):
            print(f"📅 Válido hasta: {creds.expiry}")
        
        if hasattr(creds, 'refresh_token') and creds.refresh_token:
            print("✅ Refresh token obtenido - Se renovará automáticamente")
        else:
            print("⚠️  Sin refresh token - Puede requerir reautorización")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al canjear código: {e}")
        return False

if __name__ == "__main__":
    success = setup_oauth_manual()
    
    if success:
        print()
        print("=" * 70)
        print("✅ Configuración completada")
        print("=" * 70)
        print()
        print("📝 Puedes ejecutar: python export_token_production.py")
    else:
        print()
        print("❌ Configuración fallida")
