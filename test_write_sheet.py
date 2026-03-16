#!/usr/bin/env python3
"""
Script para probar escritura en planilla OUTPUT con OAuth
"""
import os
import sys
sys.path.append(os.path.dirname(__file__))

from services.google_sheets import GoogleSheetsService
from datetime import datetime

def test_write():
    print("=" * 70)
    print("🧪 PRUEBA DE ESCRITURA EN PLANILLA OUTPUT")
    print("=" * 70)
    print()
    
    try:
        # Inicializar servicio
        print("1️⃣  Inicializando GoogleSheetsService...")
        sheets_service = GoogleSheetsService()
        print()
        
        # Verificar ID de planilla
        print(f"2️⃣  Verificando configuración...")
        print(f"   OUTPUT_SHEET_ID: {sheets_service.output_sheet_id}")
        print()
        
        # Intentar abrir la planilla
        print("3️⃣  Intentando abrir planilla OUTPUT...")
        output_sheet = sheets_service._get_output_sheet()
        
        if not output_sheet:
            print("❌ No se pudo abrir la planilla OUTPUT")
            return False
        
        print(f"   ✅ Planilla abierta: {output_sheet.title}")
        worksheet = output_sheet.get_worksheet(0)
        print(f"   ✅ Worksheet: {worksheet.title}")
        print()
        
        # Intentar leer datos (verificar permisos de lectura)
        print("4️⃣  Probando lectura...")
        col_f = worksheet.col_values(6)  # Columna F
        print(f"   ✅ Lectura OK: {len(col_f)} filas leídas en columna F")
        print()
        
        # Intentar escribir datos de prueba
        print("5️⃣  Probando escritura...")
        
        # Encontrar última fila
        ultima_fila = 10
        for i, valor in enumerate(col_f, start=1):
            if i > 10 and str(valor).strip():
                ultima_fila = i
        
        proxima_fila = ultima_fila + 1
        print(f"   Última fila con datos: {ultima_fila}")
        print(f"   Escribiendo en fila: {proxima_fila}")
        
        # Datos de prueba
        fecha_test = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        datos_test = [
            '',  # A
            '',  # B
            '',  # C
            fecha_test,  # D
            '',  # E
            '999-TEST',  # F - Número de item de prueba
            'TEST OAUTH',  # G - Gasoducto
            '',  # H
            'Prueba de escritura OAuth',  # I - Ubicación
            '',  # J
            '',  # K
            '',  # L
            f'PRUEBA AUTOMATICA - {fecha_test}',  # M - Observaciones
        ]
        
        rango = f"A{proxima_fila}:M{proxima_fila}"
        print(f"   Rango: {rango}")
        
        resultado = worksheet.update(rango, [datos_test], value_input_option='USER_ENTERED')
        
        print(f"   ✅ Escritura OK!")
        print(f"   Respuesta: {resultado}")
        print()
        
        # Verificar que se escribió
        print("6️⃣  Verificando escritura...")
        valor_verificacion = worksheet.cell(proxima_fila, 6).value
        print(f"   Valor en F{proxima_fila}: {valor_verificacion}")
        
        if valor_verificacion == '999-TEST':
            print("   ✅ Verificación OK - Dato escrito correctamente")
            print()
            print("=" * 70)
            print("✅ PRUEBA EXITOSA - OAuth puede escribir en la planilla")
            print("=" * 70)
            return True
        else:
            print("   ⚠️  Verificación falló - Dato no encontrado")
            return False
        
    except Exception as e:
        print()
        print("❌ ERROR EN LA PRUEBA")
        print(f"   {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_write()
    sys.exit(0 if success else 1)
