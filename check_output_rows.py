#!/usr/bin/env python3
"""Script para verificar cuántas filas tiene realmente la planilla OUTPUT"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.google_sheets import GoogleSheetsService

def main():
    # Inicializar servicio
    sheets_service = GoogleSheetsService()
    
    # Obtener planilla OUTPUT
    output_sheet = sheets_service.client.open_by_key(sheets_service.output_sheet_id)
    worksheet = output_sheet.get_worksheet(0)
    
    # Leer columna F (números de item)
    print("🔍 Leyendo columna F (N° de item)...")
    col_f = worksheet.col_values(6)
    
    print(f"\n📊 Total de celdas en columna F: {len(col_f)}")
    
    # Contar filas con datos después de fila 10
    items_encontrados = []
    for i, valor in enumerate(col_f, start=1):
        if i > 10 and valor and str(valor).strip():
            items_encontrados.append((i, str(valor).strip()))
    
    print(f"✅ Items encontrados (después de fila 10): {len(items_encontrados)}")
    print(f"\n📋 Lista de items:")
    for fila, item in items_encontrados:
        print(f"  Fila {fila}: Item #{item}")
    
    if items_encontrados:
        print(f"\n🔝 Primer item: #{items_encontrados[0][1]} en fila {items_encontrados[0][0]}")
        print(f"🔚 Último item: #{items_encontrados[-1][1]} en fila {items_encontrados[-1][0]}")

if __name__ == "__main__":
    main()
