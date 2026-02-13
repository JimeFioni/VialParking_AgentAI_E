#!/usr/bin/env python3
"""
Exporta el token OAuth en formato base64 para producción
"""
import pickle
import base64
import json

# Cargar token actual
with open('token_drive.pickle', 'rb') as f:
    token = pickle.load(f)

# Convertir a diccionario
token_data = {
    'token': token.token,
    'refresh_token': token.refresh_token,
    'token_uri': token.token_uri,
    'client_id': token.client_id,
    'client_secret': token.client_secret,
    'scopes': token.scopes
}

# Codificar en base64
token_json = json.dumps(token_data)
token_base64 = base64.b64encode(token_json.encode()).decode()

print('=' * 70)
print('🔐 TOKEN OAUTH PARA PRODUCCIÓN (DRIVE_OAUTH_TOKEN_BASE64)')
print('=' * 70)
print()
print(token_base64)
print()
print('=' * 70)
print('📋 INSTRUCCIONES:')
print('=' * 70)
print()
print('1. RENDER (https://dashboard.render.com):')
print('   - Selecciona tu servicio web')
print('   - Environment → Environment Variables')
print('   - Busca: DRIVE_OAUTH_TOKEN_BASE64')
print('   - Reemplaza con el valor de arriba')
print('   - Save Changes')
print()
print('2. STREAMLIT CLOUD (https://share.streamlit.io):')
print('   - Abre tu app')
print('   - Settings → Secrets')
print('   - Agrega/actualiza en secrets.toml:')
print('   DRIVE_OAUTH_TOKEN_BASE64 = "[pegar token de arriba]"')
print('   - Save')
print()
print('⚠️  IMPORTANTE: Este token tiene refresh_token incluido')
print('   Se renovará automáticamente por ~7 días (Testing mode)')
print('=' * 70)
