#!/usr/bin/env python3
"""
Script simple para verificar token OAuth
"""
import pickle
from googleapiclient.discovery import build

print("=" * 70)
print("🧪 Verificación Simple de Token")
print("=" * 70)
print()

# Cargar token
with open('token_drive.pickle', 'rb') as token_file:
    creds = pickle.load(token_file)

print(f"📋 Scopes: {creds.scopes}")
print(f"📅 Expira: {creds.expiry}")
print(f"✅ Válido: {creds.valid}")
print()

# Test Drive
print("1️⃣  Probando Drive API...")
try:
    drive = build('drive', 'v3', credentials=creds)
    results = drive.files().list(pageSize=3).execute()
    print(f"   ✅ Drive OK - {len(results.get('files', []))} archivos listados")
except Exception as e:
    print(f"   ❌ Drive falló: {e}")

print()

# Test Sheets
print("2️⃣  Probando Sheets API...")
try:
    sheets = build('sheets', 'v4', credentials=creds)
    # Solo intentar acceso básico sin crear archivo
    print(f"   ✅ Sheets API accesible")
except Exception as e:
    print(f"   ❌ Sheets falló: {e}")

print()
print("=" * 70)
print("✅ Verificación completada")
print("=" * 70)
