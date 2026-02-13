#!/usr/bin/env python3
"""
Script para verificar y renovar automáticamente el token OAuth de Drive.
Útil para ejecutar en cron jobs o antes de iniciar el servidor.
"""

import os
import pickle
from google.auth.transport.requests import Request
from datetime import datetime, timedelta

def check_and_refresh_token():
    """Verifica el token y lo renueva si está por expirar"""
    token_path = 'token_drive.pickle'
    
    if not os.path.exists(token_path):
        print(f"❌ No existe {token_path}")
        print("   Ejecuta: python setup_oauth_drive.py")
        return False
    
    try:
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
        
        print("📝 Estado del token:")
        print(f"   Válido: {creds.valid}")
        print(f"   Expirado: {creds.expired}")
        
        if hasattr(creds, 'expiry'):
            print(f"   Expira: {creds.expiry}")
            
            # Calcular tiempo restante
            now = datetime.utcnow()
            if creds.expiry:
                tiempo_restante = creds.expiry - now
                minutos_restantes = tiempo_restante.total_seconds() / 60
                print(f"   ⏱️  Tiempo restante: {int(minutos_restantes)} minutos")
                
                # Si expira en menos de 5 minutos, renovar
                if minutos_restantes < 5:
                    print("\n⚠️  Token expirará pronto, renovando...")
        
        # Si está expirado o por expirar, renovar
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                print("\n🔄 Renovando token...")
                creds.refresh(Request())
                
                # Guardar token renovado
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                
                print("✅ Token renovado exitosamente")
                if hasattr(creds, 'expiry'):
                    print(f"📅 Nuevo token válido hasta: {creds.expiry}")
                
                return True
            else:
                print("\n❌ Token sin refresh_token o expiró permanentemente")
                print("   Ejecuta: python setup_oauth_drive.py")
                return False
        else:
            print("\n✅ Token válido, no requiere renovación")
            return True
            
    except Exception as e:
        print(f"\n❌ Error al verificar token: {e}")
        print("   Ejecuta: python setup_oauth_drive.py")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("🔍 Verificación de Token OAuth")
    print("=" * 70)
    print()
    
    success = check_and_refresh_token()
    
    print()
    print("=" * 70)
    if success:
        print("✅ Token OK - Puedes usar el sistema")
    else:
        print("❌ Token requiere atención")
    print("=" * 70)
