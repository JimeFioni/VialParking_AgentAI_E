"""
Script para exportar el token OAuth a formato base64 para Render.
Ejecuta este script DESPUÉS de haber hecho push de los cambios.
"""

import pickle
import base64
import json
import os

token_path = 'token_drive.pickle'

print("🔐 Exportador de Token OAuth para Render")
print("=" * 70)

if not os.path.exists(token_path):
    print(f"❌ ERROR: No existe {token_path}")
    print("   Ejecuta primero: python setup_oauth_drive.py")
    exit(1)

try:
    with open(token_path, 'rb') as f:
        creds = pickle.load(f)
    
    print(f"✅ Token cargado")
    print(f"   - Válido: {creds.valid}")
    print(f"   - Expirado: {creds.expired}")
    
    # Convertir credenciales a dict
    token_data = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
    
    # Serializar a JSON y luego a base64
    json_str = json.dumps(token_data)
    encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    print("\n" + "=" * 70)
    print("✅ TOKEN EXPORTADO")
    print("=" * 70)
    print("\n📋 VARIABLE PARA RENDER:")
    print("   Key: DRIVE_OAUTH_TOKEN_BASE64")
    print("\n   Value (copia todo):")
    print("-" * 70)
    print(encoded)
    print("-" * 70)
    
except Exception as e:
    print(f"❌ Error: {e}")
