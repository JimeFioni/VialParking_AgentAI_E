#!/usr/bin/env python3
"""
Script para verificar permisos del token actual
"""

import pickle
import os

if os.path.exists('token_drive.pickle'):
    with open('token_drive.pickle', 'rb') as token:
        creds = pickle.load(token)
    
    print("=" * 70)
    print("🔍 Información del Token Actual")
    print("=" * 70)
    print()
    
    if hasattr(creds, 'scopes'):
        print("📋 Permisos (Scopes):")
        for scope in creds.scopes:
            print(f"  ✓ {scope}")
    else:
        print("⚠️  No se pueden leer los scopes del token")
    
    print()
    if hasattr(creds, 'expiry'):
        print(f"📅 Válido hasta: {creds.expiry}")
    
    if hasattr(creds, 'valid'):
        print(f"✅ Estado: {'Válido' if creds.valid else 'Inválido/Expirado'}")
    
    print()
    print("=" * 70)
    print("📝 Permisos Requeridos:")
    print("  • https://www.googleapis.com/auth/drive")
    print("  • https://www.googleapis.com/auth/spreadsheets")
    print("=" * 70)
else:
    print("❌ No se encuentra token_drive.pickle")
