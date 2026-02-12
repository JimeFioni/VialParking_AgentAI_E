"""
Helper para manejar credenciales de Google en producción.
Permite cargar credentials.json desde variable de entorno base64.
"""

import os
import json
import base64
import tempfile
from pathlib import Path


def get_google_credentials_path():
    """
    Obtiene el path a credentials.json, creándolo desde variable de entorno si es necesario.
    
    En desarrollo: usa el archivo credentials.json local
    En producción: crea el archivo desde GOOGLE_CREDENTIALS_BASE64
    
    Returns:
        str: Path al archivo credentials.json
    """
    # Path configurado en .env
    credentials_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "credentials.json")
    
    # Si el archivo existe localmente, úsalo (desarrollo)
    if os.path.exists(credentials_path):
        print(f"✅ Usando credentials.json local: {credentials_path}")
        return credentials_path
    
    # Si no existe, intentar crear desde variable de entorno (producción)
    credentials_base64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    
    if not credentials_base64:
        raise ValueError(
            "❌ No se encontró credentials.json ni GOOGLE_CREDENTIALS_BASE64.\n"
            "Para producción, configura GOOGLE_CREDENTIALS_BASE64 con el contenido de credentials.json en base64."
        )
    
    try:
        # Decodificar base64
        credentials_json = base64.b64decode(credentials_base64).decode('utf-8')
        credentials_dict = json.loads(credentials_json)
        
        # Crear archivo temporal o permanente
        if os.getenv("ENVIRONMENT") == "production":
            # En producción, crear en /tmp (persiste durante la vida del container)
            temp_path = "/tmp/credentials.json"
        else:
            # En desarrollo, crear archivo temporal
            temp_path = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False).name
        
        # Escribir credenciales
        with open(temp_path, 'w') as f:
            json.dump(credentials_dict, f, indent=2)
        
        print(f"✅ Credentials.json creado desde variable de entorno: {temp_path}")
        return temp_path
        
    except Exception as e:
        raise ValueError(f"❌ Error al decodificar GOOGLE_CREDENTIALS_BASE64: {e}")


def get_credentials_base64_command():
    """
    Retorna el comando para generar GOOGLE_CREDENTIALS_BASE64.
    
    Returns:
        str: Comando para ejecutar en terminal
    """
    return """
# Para generar GOOGLE_CREDENTIALS_BASE64 en tu terminal:

# macOS/Linux:
cat credentials.json | base64

# Windows PowerShell:
[Convert]::ToBase64String([IO.File]::ReadAllBytes("credentials.json"))

# Luego copia el output y configúralo como variable de entorno en tu plataforma de hosting.
    """.strip()


if __name__ == "__main__":
    """
    Ejecuta este script para probar la configuración de credenciales.
    """
    print("🔍 Verificando configuración de credenciales de Google...")
    print("=" * 60)
    
    try:
        path = get_google_credentials_path()
        print(f"\n✅ Path de credenciales: {path}")
        
        # Validar que el archivo tenga contenido válido
        with open(path, 'r') as f:
            creds = json.load(f)
        
        print(f"✅ Archivo válido - Tipo: {creds.get('type', 'unknown')}")
        print(f"✅ Project ID: {creds.get('project_id', 'unknown')}")
        print(f"✅ Client Email: {creds.get('client_email', 'unknown')}")
        
        print("\n" + "=" * 60)
        print("✅ Configuración de credenciales correcta!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n" + "=" * 60)
        print("📝 Instrucciones para configurar:")
        print(get_credentials_base64_command())
