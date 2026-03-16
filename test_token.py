#!/usr/bin/env python3
"""
Script para probar acceso a Drive y Google Sheets con el token OAuth
"""

import pickle
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def test_token():
    if not os.path.exists('token_drive.pickle'):
        print("❌ No se encuentra token_drive.pickle")
        return False
    
    with open('token_drive.pickle', 'rb') as token:
        creds = pickle.load(token)
    
    print("=" * 70)
    print("🧪 Prueba de Acceso con Token OAuth")
    print("=" * 70)
    print()
    
    # Test 1: Acceso a Drive
    print("1️⃣  Probando acceso a Google Drive...")
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        results = drive_service.files().list(
            pageSize=5,
            fields="files(id, name)"
        ).execute()
        files = results.get('files', [])
        print(f"   ✅ Drive accesible - {len(files)} archivos encontrados")
        if files:
            print(f"   📁 Ejemplo: {files[0]['name']}")
    except Exception as e:
        print(f"   ❌ Error en Drive: {e}")
        return False
    
    print()
    
    # Test 2: Acceso a Google Sheets
    print("2️⃣  Probando acceso a Google Sheets...")
    try:
        sheets_service = build('sheets', 'v4', credentials=creds)
        # Intentar crear una hoja de prueba temporal
        spreadsheet = {
            'properties': {
                'title': 'Test Token - Temporal'
            }
        }
        response = sheets_service.spreadsheets().create(
            body=spreadsheet
        ).execute()
        
        sheet_id = response['spreadsheetId']
        print(f"   ✅ Sheets accesible - Hoja de prueba creada")
        print(f"   📊 ID: {sheet_id}")
        
        # Eliminar la hoja de prueba
        drive_service = build('drive', 'v3', credentials=creds)
        drive_service.files().delete(fileId=sheet_id).execute()
        print(f"   🗑️  Hoja de prueba eliminada")
        
    except Exception as e:
        print(f"   ❌ Error en Sheets: {e}")
        return False
    
    print()
    print("=" * 70)
    print("✅ Token funcionando correctamente para Drive y Sheets")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    test_token()
