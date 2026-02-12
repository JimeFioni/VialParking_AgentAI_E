import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
import os
import pickle
from typing import List, Dict, Optional, Any
from datetime import datetime
from dotenv import load_dotenv
import io

load_dotenv()


class GoogleSheetsService:
    def __init__(self):
        credentials_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "credentials.json")
        
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"Archivo de credenciales no encontrado: {credentials_path}\n"
                "Descarga las credenciales desde Google Cloud Console"
            )
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Service account para Sheets (funciona bien)
        creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        self.client = gspread.authorize(creds)
        
        # OAuth para Drive (evita problemas de cuota)
        self.drive_service = self._init_drive_service_oauth()
        
        # Si OAuth falla, usar service account como fallback
        if not self.drive_service:
            print("⚠️  Usando service account para Drive (puede tener limitaciones)")
            self.drive_service = build('drive', 'v3', credentials=creds)
        
        # IDs de las hojas
        self.acciones_sheet_id = os.getenv("ACCIONES_SHEET_ID")
        self.database_sheet_id = os.getenv("DATABASE_SHEET_ID")
        self.stock_folder_id = os.getenv("STOCK_DRIVE_FOLDER_ID")
        self.ecogas_sheet_id = os.getenv("ECOGAS_SHEET_ID")  # Planilla INPUT de ECOGAS
        self.output_sheet_id = os.getenv("OUTPUT_SHEET_ID")  # Planilla OUTPUT para registrar trabajos
        self.whatsapp_log_sheet_id = os.getenv("WHATSAPP_LOG_SHEET_ID", self.output_sheet_id)  # LOG de WhatsApp
        self.imagenes_carteles_folder_id = os.getenv("IMAGENES_CARTELES_FOLDER_ID")
        self.output_imagenes_folder_id = os.getenv("OUTPUT_IMAGENES_FOLDER_ID")
        
        # Cache de las hojas de base de datos
        self._db_sheet = None
        self._ecogas_sheet = None
        self._output_sheet = None
        self._whatsapp_log_sheet = None
    
    def _init_drive_service_oauth(self):
        """Inicializa servicio de Drive con OAuth (evita límites de cuota)."""
        try:
            token_path = 'token_drive.pickle'
            creds = None
            
            # Cargar token existente
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # Verificar si necesita refresh
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Guardar token actualizado
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            # Si hay credenciales válidas, crear servicio
            if creds and creds.valid:
                print("✅ Usando OAuth para Google Drive")
                return build('drive', 'v3', credentials=creds)
            
            return None
            
        except Exception as e:
            print(f"⚠️  No se pudo cargar OAuth para Drive: {e}")
            return None
    
    def _get_database_sheet(self):
        """Obtiene la hoja de base de datos con cache."""
        if self._db_sheet is None:
            self._db_sheet = self.client.open_by_key(self.database_sheet_id)
        return self._db_sheet
    
    def _get_worksheet_by_name(self, name: str):
        """Obtiene una pestaña específica de la base de datos."""
        try:
            db_sheet = self._get_database_sheet()
            return db_sheet.worksheet(name)
        except Exception as e:
            # Silenciar el error si es un archivo no compatible
            if "not supported for this document" not in str(e):
                print(f"Error al obtener pestaña {name}: {e}")
            return None
    
    # ===== ACCIONES AUTORIZADAS =====
    def obtener_acciones_autorizadas(self) -> List[str]:
        """
        Obtiene la lista de acciones viales autorizadas desde la hoja de acciones.
        """
        try:
            sheet = self.client.open_by_key(self.acciones_sheet_id)
            worksheet = sheet.get_worksheet(0)
            records = worksheet.get_all_records()
            
            acciones = []
            for record in records:
                accion = (
                    record.get('Acción') or 
                    record.get('Accion') or 
                    record.get('ACCION') or
                    record.get('accion') or
                    record.get('Descripción') or
                    record.get('Descripcion')
                )
                if accion and accion.strip():
                    acciones.append(accion.strip())
            
            return acciones
            
        except Exception as e:
            print(f"Error al obtener acciones autorizadas: {e}")
            return [
                "Reemplazo de señal de tránsito deteriorada",
                "Instalación de señal de prohibido estacionar",
                "Reemplazo de señal de zona de carga",
                "Instalación de señal de velocidad máxima"
            ]
    
    # ===== EMPLEADOS =====
    def obtener_empleados(self) -> List[Dict[str, Any]]:
        """Obtiene todos los empleados."""
        try:
            worksheet = self._get_worksheet_by_name("empleados")
            if worksheet:
                return worksheet.get_all_records()
            return []
        except Exception as e:
            print(f"Error al obtener empleados: {e}")
            return []
    
    def agregar_empleado(self, datos: Dict[str, Any]) -> bool:
        """Agrega un nuevo empleado."""
        try:
            worksheet = self._get_worksheet_by_name("empleados")
            if worksheet:
                worksheet.append_row(list(datos.values()))
                return True
            return False
        except Exception as e:
            print(f"Error al agregar empleado: {e}")
            return False
    
    # ===== CONVERSACIONES =====
    def obtener_conversaciones(self, whatsapp_number: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene conversaciones, opcionalmente filtradas por número."""
        try:
            worksheet = self._get_worksheet_by_name("conversaciones")
            if not worksheet:
                return []
            
            records = worksheet.get_all_records()
            
            if whatsapp_number:
                return [r for r in records if r.get('whatsapp_number') == whatsapp_number]
            return records
        except Exception as e:
            print(f"Error al obtener conversaciones: {e}")
            return []
    
    def guardar_conversacion(self, whatsapp_number: str, mensaje: str, tipo: str = "user") -> bool:
        """Guarda un mensaje de conversación."""
        try:
            worksheet = self._get_worksheet_by_name("conversaciones")
            if worksheet:
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                worksheet.append_row([fecha, whatsapp_number, tipo, mensaje])
                return True
            return False
        except Exception as e:
            print(f"Error al guardar conversación: {e}")
            return False
    
    # ===== ORDENES =====
    def obtener_ordenes(self, estado: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene órdenes, opcionalmente filtradas por estado."""
        try:
            worksheet = self._get_worksheet_by_name("ordenes")
            if not worksheet:
                return []
            
            records = worksheet.get_all_records()
            
            if estado:
                return [r for r in records if r.get('estado') == estado]
            return records
        except Exception as e:
            print(f"Error al obtener órdenes: {e}")
            return []
    
    def crear_orden(self, datos: Dict[str, Any]) -> bool:
        """Crea una nueva orden de trabajo."""
        try:
            worksheet = self._get_worksheet_by_name("ordenes")
            if worksheet:
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                datos['fecha_creacion'] = fecha
                worksheet.append_row(list(datos.values()))
                return True
            return False
        except Exception as e:
            print(f"Error al crear orden: {e}")
            return False
    
    def actualizar_estado_orden(self, orden_id: str, nuevo_estado: str) -> bool:
        """Actualiza el estado de una orden."""
        try:
            worksheet = self._get_worksheet_by_name("ordenes")
            if not worksheet:
                return False
            
            cell = worksheet.find(orden_id)
            if cell:
                # Buscar la columna de estado (ajustar según tu estructura)
                headers = worksheet.row_values(1)
                estado_col = headers.index('estado') + 1 if 'estado' in headers else None
                if estado_col:
                    worksheet.update_cell(cell.row, estado_col, nuevo_estado)
                    return True
            return False
        except Exception as e:
            print(f"Error al actualizar estado de orden: {e}")
            return False
    
    # ===== STOCK =====
    def obtener_stock(self) -> Dict[str, int]:
        """Obtiene el stock actual desde la planilla ECOGAS (pestaña 2, filas 92+)."""
        try:
            sheet = self._get_ecogas_sheet()
            if not sheet or len(sheet.worksheets()) < 2:
                print("No se encontró planilla de stock")
                return {}
            
            worksheet = sheet.get_worksheet(1)
            all_values = worksheet.get_all_values()
            
            # Headers están en fila 89 (índice 88)
            # Datos empiezan en fila 92 (índice 91)
            if len(all_values) < 92:
                return {}
            
            headers = all_values[88]  # Fila 89
            
            # Mapeo detallado de columnas (índices base-0)
            stock_mapping = {
                # CARTELES
                'Cartel Tipo D Gasoducto': 11,      # Col 12
                'Cartel Tipo D Cañería': 12,         # Col 13
                'Cartel Tipo D Gasoductos (alt)': 13,  # Col 14
                'Cartel Tipo D Cañerías (alt)': 14,    # Col 15
                
                # MOJONES
                'Mojón de Metal': 15,                # Col 16
                'Mojón de Hormigón': 16,             # Col 17
                'Mojón de Polietileno': 17,          # Col 18
                
                # POSTES
                'Poste Alto (Met. 2")': 18,          # Col 19
                'Poste Bajo (Mad. 3")': 19,          # Col 20
            }
            
            # Inicializar stock
            stock = {nombre: 0 for nombre in stock_mapping.keys()}
            
            # Leer datos desde fila 92 hasta encontrar TOTALES
            found_total = False
            for row in all_values[91:]:  # Desde fila 92
                if len(row) < 21:
                    continue
                
                numero = str(row[4]).strip()  # Col 5
                
                # Si encontramos TOTALES, usar esa fila y terminar
                if 'TOTAL' in numero.upper():
                    for nombre, col_idx in stock_mapping.items():
                        if col_idx < len(row):
                            val = str(row[col_idx]).strip()
                            if val and val.isdigit():
                                stock[nombre] = int(val)
                    found_total = True
                    break
                
                # Si no hay TOTALES todavía, sumar fila por fila
                if numero and numero.isdigit():
                    for nombre, col_idx in stock_mapping.items():
                        if col_idx < len(row):
                            val = str(row[col_idx]).strip()
                            if val and val.isdigit():
                                stock[nombre] += int(val)
            
            # Filtrar items con stock > 0
            stock = {k: v for k, v in stock.items() if v > 0}
            
            return stock
            
        except Exception as e:
            print(f"Error al obtener stock: {e}")
            import traceback
            traceback.print_exc()
            return {}
            
            # Fallback: intentar desde la pestaña stock de DATABASE_SHEET
            worksheet = self._get_worksheet_by_name("stock")
            if not worksheet:
                return {}
            
            records = worksheet.get_all_records()
            stock = {}
            
            for record in records:
                tipo = (
                    record.get('Tipo') or 
                    record.get('tipo') or
                    record.get('Cartel') or
                    record.get('cartel')
                )
                cantidad = (
                    record.get('Cantidad') or 
                    record.get('cantidad') or
                    record.get('Stock') or
                    record.get('stock')
                )
                
                if tipo and cantidad is not None:
                    try:
                        stock[str(tipo).strip()] = int(cantidad)
                    except (ValueError, TypeError):
                        continue
            
            return stock
            
        except Exception as e:
            print(f"Error al obtener stock: {e}")
            return {}
    
    def actualizar_stock(self, tipo_cartel: str, cantidad: int) -> bool:
        """Actualiza el stock de un tipo de cartel (resta cantidad)."""
        try:
            # Intentar actualizar en la planilla ECOGAS primero
            sheet = self._get_ecogas_sheet()
            if sheet:
                try:
                    worksheet = None
                    for ws in sheet.worksheets():
                        if 'material' in ws.title.lower() or 'stock' in ws.title.lower():
                            worksheet = ws
                            break
                    
                    if not worksheet:
                        worksheet = sheet.get_worksheet(1) if len(sheet.worksheets()) > 1 else None
                    
                    if worksheet:
                        # Buscar el tipo de cartel a partir de la fila 85
                        cell = worksheet.find(tipo_cartel, in_row=None)
                        
                        if cell and cell.row >= 85:
                            # Buscar columna de cantidad en el header
                            all_values = worksheet.get_all_values()
                            headers = all_values[84]  # fila 85
                            
                            cantidad_col = None
                            for idx, header in enumerate(headers, 1):
                                header_lower = str(header).lower().strip()
                                if any(word in header_lower for word in ['cantidad', 'stock', 'total']):
                                    cantidad_col = idx
                                    break
                            
                            if cantidad_col:
                                stock_actual = int(worksheet.cell(cell.row, cantidad_col).value or 0)
                                nuevo_stock = max(0, stock_actual - cantidad)
                                worksheet.update_cell(cell.row, cantidad_col, nuevo_stock)
                                return True
                except Exception as e:
                    print(f"Error al actualizar stock en ECOGAS: {e}")
            
            # Fallback: intentar en DATABASE_SHEET
            worksheet = self._get_worksheet_by_name("stock")
            if not worksheet:
                return False
            
            cell = worksheet.find(tipo_cartel)
            if cell:
                headers = worksheet.row_values(1)
                cantidad_col = None
                
                for idx, header in enumerate(headers, 1):
                    if header.lower() in ['cantidad', 'stock']:
                        cantidad_col = idx
                        break
                
                if cantidad_col:
                    stock_actual = int(worksheet.cell(cell.row, cantidad_col).value or 0)
                    nuevo_stock = max(0, stock_actual - cantidad)
                    worksheet.update_cell(cell.row, cantidad_col, nuevo_stock)
                    return True
            return False
            
        except Exception as e:
            print(f"Error al actualizar stock: {e}")
            return False
    
    def verificar_stock_bajo(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """Verifica si hay items con stock bajo."""
        stock = self.obtener_stock()
        alertas = []
        
        for tipo, cantidad in stock.items():
            if cantidad <= threshold:
                alertas.append({
                    "tipo_cartel": tipo,
                    "cantidad_actual": cantidad,
                    "threshold": threshold,
                    "mensaje": f"⚠️ Stock bajo: {tipo} - Quedan solo {cantidad} unidades"
                })
        
        return alertas
    
    # ===== MOVIMIENTOS STOCK =====
    def registrar_movimiento_stock(self, datos: Dict[str, Any]) -> bool:
        """Registra un movimiento de stock (entrada/salida)."""
        try:
            worksheet = self._get_worksheet_by_name("movimientos_stock")
            if worksheet:
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                datos['fecha'] = fecha
                worksheet.append_row(list(datos.values()))
                return True
            return False
        except Exception as e:
            print(f"Error al registrar movimiento de stock: {e}")
            return False
    
    def obtener_movimientos_stock(self, tipo_cartel: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene movimientos de stock, opcionalmente filtrados por tipo."""
        try:
            worksheet = self._get_worksheet_by_name("movimientos_stock")
            if not worksheet:
                return []
            
            records = worksheet.get_all_records()
            
            if tipo_cartel:
                return [r for r in records if r.get('tipo_cartel') == tipo_cartel]
            return records
        except Exception as e:
            print(f"Error al obtener movimientos de stock: {e}")
            return []
    
    # ===== POLÍGONOS =====
    def obtener_poligonos(self) -> List[Dict[str, Any]]:
        """Obtiene todos los polígonos definidos."""
        try:
            worksheet = self._get_worksheet_by_name("poligonos")
            if worksheet:
                return worksheet.get_all_records()
            return []
        except Exception as e:
            print(f"Error al obtener polígonos: {e}")
            return []
    
    def agregar_poligono(self, datos: Dict[str, Any]) -> bool:
        """Agrega un nuevo polígono."""
        try:
            worksheet = self._get_worksheet_by_name("poligonos")
            if worksheet:
                worksheet.append_row(list(datos.values()))
                return True
            return False
        except Exception as e:
            print(f"Error al agregar polígono: {e}")
            return False
    
    # ===== ECOGAS - GESTIÓN DE CARTELES DE GASODUCTOS =====
    def _get_ecogas_sheet(self):
        """Obtiene la hoja INPUT de ECOGAS con cache."""
        if self._ecogas_sheet is None and self.ecogas_sheet_id:
            self._ecogas_sheet = self.client.open_by_key(self.ecogas_sheet_id)
        return self._ecogas_sheet
    
    def _get_output_sheet(self):
        """Obtiene la hoja OUTPUT para registrar trabajos completados."""
        if self._output_sheet is None and self.output_sheet_id:
            self._output_sheet = self.client.open_by_key(self.output_sheet_id)
        return self._output_sheet
    
    def obtener_carteles_ecogas(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los carteles de la planilla de ECOGAS.
        Los datos empiezan en la fila 7 (índice 6).
        Columnas: 
        - Col B (índice 1): N°
        - Col C (índice 2): Gasoducto/Ramal
        - Col D (índice 3): Ubicación/Descripción
        - Col E (índice 4): Georreferencias (formato: '-33.16251 -64.38082)
        - Col I (índice 8): Observaciones
        - Col J (índice 9): Estado OK/MAL
        - Col K (índice 10): Tipo (A,B,C,D,E)
        - Col última: CENTRO OPERATIVO / ZONAS
        """
        try:
            sheet = self._get_ecogas_sheet()
            if not sheet:
                print("No se pudo acceder a la planilla de ECOGAS")
                return []
            
            worksheet = sheet.get_worksheet(0)
            all_values = worksheet.get_all_values()
            
            print(f"=== DEBUG ECOGAS ===")
            print(f"Total filas en la hoja: {len(all_values)}")
            if len(all_values) > 0:
                print(f"Columnas en la primera fila: {len(all_values[0])}")
                print(f"Encabezados (fila 1): {all_values[0][:15]}")
            if len(all_values) > 6:
                print(f"Primera fila de datos (fila 7): {all_values[6][:15]}")
            
            if len(all_values) < 7:
                print(f"La hoja tiene menos de 7 filas: {len(all_values)}")
                return []
            
            # Los datos empiezan en la fila 7 (índice 6)
            carteles = []
            for idx, row in enumerate(all_values[6:], start=7):  # Desde fila 7
                if len(row) < 5:  # Necesitamos al menos hasta columna E
                    continue
                
                # Columna B (índice 1): N°
                numero = str(row[1]).strip() if len(row) > 1 else ''
                if not numero or not numero[0].isdigit():
                    continue  # Saltar si no tiene número
                
                # Columna C (índice 2): Gasoducto/Ramal
                gasoducto = str(row[2]).strip() if len(row) > 2 else ''
                if not gasoducto:
                    continue
                
                # Columna D (índice 3): Ubicación/Descripción
                ubicacion = str(row[3]).strip() if len(row) > 3 else ''
                
                # Columna E (índice 4): Georreferencias (formato: '-33.16251 -64.38082 o -33.16251 -64.38082)
                georef = str(row[4]).strip() if len(row) > 4 else ''
                lat, lon = None, None
                georef_str = georef  # Guardar string original para mostrar
                
                # Columna F (índice 5): Ancho
                ancho = str(row[5]).strip() if len(row) > 5 else ''
                
                # Columna G (índice 6): Alto
                alto = str(row[6]).strip() if len(row) > 6 else ''
                
                # Columna H (índice 7): Tapada de cañería
                tapada_caneria = str(row[7]).strip() if len(row) > 7 else ''
                
                if georef and georef != '-' and georef != '':
                    try:
                        # Limpiar el formato: quitar comillas simples, dobles, espacios extras
                        georef_limpio = georef.replace("'", "").replace('"', '').strip()
                        
                        # Separar por espacios múltiples o tabuladores
                        import re
                        parts = re.split(r'\s+', georef_limpio)
                        
                        if len(parts) >= 2:
                            # Primer valor es latitud, segundo es longitud
                            lat_str = parts[0].strip()
                            lon_str = parts[1].strip()
                            
                            try:
                                # Validar que solo tenga un punto decimal
                                if lat_str.count('.') <= 1 and lon_str.count('.') <= 1:
                                    lat = float(lat_str)
                                    lon = float(lon_str)
                                    
                                    # Validar rangos razonables para Argentina
                                    if -55 <= lat <= -21 and -74 <= lon <= -53:
                                        print(f"✓ Fila {idx} - Cartel #{numero}: Lat={lat:.6f}, Lon={lon:.6f}")
                                    else:
                                        print(f"✗ Fila {idx}: Coordenadas fuera de rango Argentina - Lat={lat}, Lon={lon}")
                                        lat, lon = None, None
                                else:
                                    print(f"✗ Fila {idx}: Formato inválido (múltiples puntos) - '{lat_str}', '{lon_str}'")
                            except ValueError as ve:
                                print(f"✗ Fila {idx}: Error convirtiendo a float: '{lat_str}', '{lon_str}' - {ve}")
                        else:
                            print(f"✗ Fila {idx}: No hay suficientes partes en georef: '{georef_limpio}' (partes: {parts})")
                            
                    except Exception as e:
                        print(f"✗ Fila {idx}: Error parseando coordenadas '{georef}': {e}")
                
                # Columna I (índice 8): Observaciones
                observaciones = str(row[8]).strip() if len(row) > 8 else ''
                
                # Columna J (índice 9): Estado
                estado = str(row[9]).strip() if len(row) > 9 else 'pendiente'
                
                # Columna K (índice 10): Tipo (A, B, C, D, E o mojón)
                tipo_raw = str(row[10]).strip() if len(row) > 10 else ''
                # Extraer solo la primera línea si tiene saltos de línea
                tipo = tipo_raw.split('\n')[0] if tipo_raw else ''
                
                # Columnas adicionales de trabajo e instalación
                # Las columnas 11 en adelante contienen info de trabajos 10, 20, 30
                # Cada trabajo tiene varias subcolumnas con valor "1" indicando cuál se usó
                
                # TRABAJO 10 (3 subcolumnas: índices 11, 12, 13)
                poste_alto_met_10 = str(row[11]).strip() if len(row) > 11 else ''
                poste_bajo_met_10 = str(row[12]).strip() if len(row) > 12 else ''
                poste_bajo_mad_10 = str(row[13]).strip() if len(row) > 13 else ''
                
                # TRABAJO 20 (3 subcolumnas: índices 14, 15, 16)
                poste_alto_met_20 = str(row[14]).strip() if len(row) > 14 else ''
                poste_bajo_mad_20 = str(row[15]).strip() if len(row) > 15 else ''
                mojon_met4_20 = str(row[16]).strip() if len(row) > 16 else ''
                
                # TRABAJO 30 (4 subcolumnas: índices 17, 18, 19, 20)
                poste_alto_met_30 = str(row[17]).strip() if len(row) > 17 else ''
                poste_bajo_mad_30 = str(row[18]).strip() if len(row) > 18 else ''
                mojon_met_30 = str(row[19]).strip() if len(row) > 19 else ''
                mojon_horm_30 = str(row[20]).strip() if len(row) > 20 else ''
                
                # Última columna: CENTRO OPERATIVO / ZONAS
                zona = str(row[-1]).strip() if len(row) > 11 else ''
                
                # Agregar el cartel si tiene datos válidos
                if gasoducto and numero:
                    # Normalizar tipo de cartel
                    if tipo.upper() in ['A', 'B', 'C', 'D', 'E']:
                        tipo_cartel = f"Cartel Tipo {tipo.upper()}"
                    elif 'mojon' in tipo.lower():
                        tipo_cartel = "Mojón"
                    elif 'cañeria' in tipo.lower() or 'caneria' in tipo.lower():
                        tipo_cartel = "Cartel de Cañería"
                    elif 'gto' in tipo.lower() or 'gasoducto' in tipo.lower():
                        tipo_cartel = "Cartel de Gasoducto"
                    else:
                        tipo_cartel = tipo if tipo else "Cartel"
                    
                    # Formatear tamaño
                    tamanio_str = ''
                    if ancho and alto and ancho != '-' and alto != '-':
                        tamanio_str = f"{ancho} x {alto}"
                    elif ancho and ancho != '-':
                        tamanio_str = ancho
                    elif alto and alto != '-':
                        tamanio_str = alto
                    
                    # Formatear ubicación completa
                    ubicacion_completa = f"{gasoducto} - {ubicacion}" if ubicacion else gasoducto
                    
                    # Formatear descripción de tipo completa
                    tipo_completo = tipo_raw if tipo_raw else ''
                    
                    # Determinar qué tipo de trabajo se realizó
                    tipo_trabajo = ''
                    detalles_instalacion = []
                    
                    # Verificar si hay algún valor válido (no vacío, no "-", no solo espacios)
                    def es_valor_valido(valor):
                        return valor and str(valor).strip() not in ['', '-', '0']
                    
                    # Verificar TRABAJO 10
                    tiene_trabajo_10 = False
                    if es_valor_valido(poste_alto_met_10):
                        tipo_trabajo = '10 - Colocación o reemplazo de cartel con mantenimiento de Poste'
                        detalles_instalacion.append(f"Poste Alto (Met. 2\"): {poste_alto_met_10}")
                        tiene_trabajo_10 = True
                    if es_valor_valido(poste_bajo_met_10):
                        if not tiene_trabajo_10:
                            tipo_trabajo = '10 - Colocación o reemplazo de cartel con mantenimiento de Poste'
                        detalles_instalacion.append(f"Poste Bajo (Met.): {poste_bajo_met_10}")
                        tiene_trabajo_10 = True
                    if es_valor_valido(poste_bajo_mad_10):
                        if not tiene_trabajo_10:
                            tipo_trabajo = '10 - Colocación o reemplazo de cartel con mantenimiento de Poste'
                        detalles_instalacion.append(f"Poste Bajo (Mad. 3\"): {poste_bajo_mad_10}")
                        tiene_trabajo_10 = True
                    
                    # Verificar TRABAJO 20
                    tiene_trabajo_20 = False
                    if es_valor_valido(poste_alto_met_20):
                        tipo_trabajo = '20 - Colocación de cartel con instalación de Poste o mojón'
                        detalles_instalacion.append(f"Poste Alto (Met. 2\"): {poste_alto_met_20}")
                        tiene_trabajo_20 = True
                    if es_valor_valido(poste_bajo_mad_20):
                        if not tiene_trabajo_20:
                            tipo_trabajo = '20 - Colocación de cartel con instalación de Poste o mojón'
                        detalles_instalacion.append(f"Poste Bajo (Mad. 3\"): {poste_bajo_mad_20}")
                        tiene_trabajo_20 = True
                    if es_valor_valido(mojon_met4_20):
                        if not tiene_trabajo_20:
                            tipo_trabajo = '20 - Colocación de cartel con instalación de Poste o mojón'
                        detalles_instalacion.append(f"Mojón (Met. 4\"): {mojon_met4_20}")
                        tiene_trabajo_20 = True
                    
                    # Verificar TRABAJO 30
                    tiene_trabajo_30 = False
                    if es_valor_valido(poste_alto_met_30):
                        tipo_trabajo = '30 - Remoción y colocación de cartel con instalación de Poste o Mojón'
                        detalles_instalacion.append(f"Poste Alto (Met. 2\"): {poste_alto_met_30}")
                        tiene_trabajo_30 = True
                    if es_valor_valido(poste_bajo_mad_30):
                        if not tiene_trabajo_30:
                            tipo_trabajo = '30 - Remoción y colocación de cartel con instalación de Poste o Mojón'
                        detalles_instalacion.append(f"Poste Bajo (Mad.): {poste_bajo_mad_30}")
                        tiene_trabajo_30 = True
                    if es_valor_valido(mojon_met_30):
                        if not tiene_trabajo_30:
                            tipo_trabajo = '30 - Remoción y colocación de cartel con instalación de Poste o Mojón'
                        detalles_instalacion.append(f"Mojón Met.: {mojon_met_30}")
                        tiene_trabajo_30 = True
                    if es_valor_valido(mojon_horm_30):
                        if not tiene_trabajo_30:
                            tipo_trabajo = '30 - Remoción y colocación de cartel con instalación de Poste o Mojón'
                        detalles_instalacion.append(f"Mojón Horm.: {mojon_horm_30}")
                        tiene_trabajo_30 = True
                    
                    cartel = {
                        'numero': numero,
                        'tipo_cartel': tipo_cartel,
                        'observaciones': observaciones,
                        'gasoducto_ramal': gasoducto,
                        'latitud': lat,
                        'longitud': lon,
                        'ubicacion': ubicacion,
                        'ubicacion_completa': ubicacion_completa,
                        'coordenadas': georef_str,
                        'ancho': ancho,
                        'alto': alto,
                        'tamanio': tamanio_str,
                        'tapada_caneria': tapada_caneria,
                        'estado': estado,
                        'tipo_raw': tipo_raw,
                        'tipo_completo': tipo_completo,
                        'tipo_trabajo': tipo_trabajo,
                        'detalles_instalacion': detalles_instalacion,
                        'zona': zona,
                        # Trabajo 10
                        'poste_alto_met_10': poste_alto_met_10,
                        'poste_bajo_met_10': poste_bajo_met_10,
                        'poste_bajo_mad_10': poste_bajo_mad_10,
                        # Trabajo 20
                        'poste_alto_met_20': poste_alto_met_20,
                        'poste_bajo_mad_20': poste_bajo_mad_20,
                        'mojon_met4_20': mojon_met4_20,
                        # Trabajo 30
                        'poste_alto_met_30': poste_alto_met_30,
                        'poste_bajo_mad_30': poste_bajo_mad_30,
                        'mojon_met_30': mojon_met_30,
                        'mojon_horm_30': mojon_horm_30
                    }
                    carteles.append(cartel)
            
            print(f"Total carteles obtenidos: {len(carteles)}")
            carteles_con_coords = [c for c in carteles if c.get('latitud') and c.get('longitud')]
            print(f"Carteles con coordenadas: {len(carteles_con_coords)}")
            
            return carteles
            
        except Exception as e:
            print(f"Error al obtener carteles de ECOGAS: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_coordenada(self, valor) -> Optional[float]:
        """Parsea una coordenada, manejando diferentes formatos."""
        if not valor:
            return None
        
        try:
            # Si es string, limpiar y convertir
            if isinstance(valor, str):
                valor = valor.strip().replace(',', '.')
            return float(valor)
        except (ValueError, TypeError):
            return None
    
    def obtener_tipos_carteles_ecogas(self) -> List[str]:
        """Obtiene lista única de tipos de carteles de ECOGAS."""
        try:
            carteles = self.obtener_carteles_ecogas()
            tipos = set()
            for cartel in carteles:
                if cartel.get('tipo_cartel'):
                    tipos.add(cartel['tipo_cartel'])
            return sorted(list(tipos))
        except Exception as e:
            print(f"Error al obtener tipos de carteles: {e}")
            return []
    
    def obtener_acciones_ecogas(self) -> List[str]:
        """
        Obtiene lista única de acciones (observaciones) de ECOGAS.
        Estas son las acciones que los operarios pueden realizar.
        """
        try:
            carteles = self.obtener_carteles_ecogas()
            acciones = set()
            for cartel in carteles:
                if cartel.get('observaciones'):
                    acciones.add(cartel['observaciones'])
            return sorted(list(acciones))
        except Exception as e:
            print(f"Error al obtener acciones de ECOGAS: {e}")
            return []
    
    def actualizar_estado_cartel_ecogas(self, row_id: int, nuevo_estado: str) -> bool:
        """Actualiza el estado de un cartel en la planilla de ECOGAS."""
        try:
            sheet = self._get_ecogas_sheet()
            if not sheet:
                return False
            
            worksheet = sheet.get_worksheet(0)
            headers = worksheet.row_values(1)
            estado_col = headers.index('Estado') + 1 if 'Estado' in headers else None
            
            if estado_col:
                worksheet.update_cell(row_id + 2, estado_col, nuevo_estado)  # +2 por header y índice base-0
                return True
            return False
        except Exception as e:
            print(f"Error al actualizar estado: {e}")
            return False
    
    def registrar_trabajo_ecogas(self, datos: Dict[str, Any]) -> bool:
        """
        Registra un trabajo completado en la planilla OUTPUT.
        Copia los datos del item desde la planilla INPUT (ECOGAS) y los escribe en OUTPUT.
        
        Columnas en OUTPUT:
        C: Fecha Ejecucion (fecha actual)
        E: N° (del item)
        F: Gasoducto / Ramal (del INPUT)
        H: Ubicación / Descripción (del INPUT)
        I: Georreferencias (del INPUT)
        J: Dist. LM (distancia calculada)
        L: Observaciones ("Instalación EJECUTADA.-")
        N: Tipo (del INPUT)
        """
        try:
            # Obtener datos del cartel desde cartel_info
            cartel_info = datos.get('cartel_info', {})
            numero_item = datos.get('numero_item', cartel_info.get('numero', ''))
            
            if not numero_item:
                print("❌ No se proporcionó número de item")
                return False
            
            # Abrir planilla OUTPUT
            output_sheet = self._get_output_sheet()
            if not output_sheet:
                print("❌ No se pudo acceder a la planilla OUTPUT")
                return False
            
            # Primera pestaña de OUTPUT
            worksheet = output_sheet.get_worksheet(0)
            
            # Preparar nueva fila con datos del INPUT
            # Formato fecha: D/M/YYYY sin ceros (ejemplo: 4/2/2026, 10/2/2026)
            fecha_ejecucion = datetime.now().strftime("%-d/%-m/%Y")
            
            # Preparar valor de distancia (puede no existir si se buscó por número directamente)
            distancia_valor = cartel_info.get('distancia_km', '')
            if distancia_valor:
                distancia_str = str(distancia_valor).replace('.', ',')  # Formato español
            else:
                distancia_str = '-'  # Guión cuando no hay valor, igual que en ejemplos
            
            # Obtener o crear la estructura de carpetas en Drive y generar enlaces separados
            carpetas = self.crear_estructura_carpetas_output(numero_item)
            enlace_antes_formula = ''
            enlace_despues_formula = ''
            
            if carpetas:
                # Generar fórmulas separadas para ANTES y DESPUÉS
                item_num = str(numero_item).zfill(3)
                
                if carpetas.get('antes'):
                    url_antes = f"https://drive.google.com/drive/folders/{carpetas['antes']}"
                    texto_antes = f"Fotos {item_num}-001 al 003"
                    enlace_antes_formula = f'=HYPERLINK("{url_antes}"; "{texto_antes}")'
                
                if carpetas.get('despues'):
                    url_despues = f"https://drive.google.com/drive/folders/{carpetas['despues']}"
                    texto_despues = f"Fotos {item_num}-004 al 006"
                    enlace_despues_formula = f'=HYPERLINK("{url_despues}"; "{texto_despues}")'
                
                if enlace_antes_formula or enlace_despues_formula:
                    print(f"📁 Fórmulas enlaces generadas:")
                    if enlace_antes_formula:
                        print(f"   - ANTES: Fotos {item_num}-001 al 003")
                    if enlace_despues_formula:
                        print(f"   - DESPUÉS: Fotos {item_num}-004 al 006")
            
            # Extraer solo la letra del tipo de cartel (D, no "Cartel Tipo D")
            tipo_cartel_raw = cartel_info.get('tipo_cartel', '')
            tipo_cartel_letra = tipo_cartel_raw
            if 'Tipo' in tipo_cartel_raw:
                # Extraer la letra después de "Tipo "
                import re
                match = re.search(r'Tipo ([A-E])', tipo_cartel_raw)
                if match:
                    tipo_cartel_letra = match.group(1)
            
            nueva_fila = [
                '',  # A: vacío
                '',  # B: Fecha Certificacion (vacío por ahora)
                '',  # C: N° Certificacion (vacío por ahora)
                fecha_ejecucion,  # D: Fecha Ejecucion
                '',  # E: vacío
                str(numero_item),  # F: N°
                cartel_info.get('gasoducto_ramal', ''),  # G: Gasoducto / Ramal
                '',  # H: Progresiva P.C.O
                cartel_info.get('ubicacion', ''),  # I: Ubicación / Descripción
                cartel_info.get('coordenadas', ''),  # J: Georreferencias (Ubicación Señalización)
                distancia_str,  # K: Dist. LM (número con coma o "-")
                cartel_info.get('alto', '-'),  # L: Dist. Al eje (usar alto del INPUT)
                'Instanción EJECUTADA.-',  # M: Observaciones (con typo igual que planilla)
                '',  # N: vacío
                cartel_info.get('tipo_raw', ''),  # O: Tipo - valor completo del INPUT (ej: "D\ncañeria")
                # TRABAJO 10 - Colocación o remplazo de cartel con mantenimiento de Poste
                cartel_info.get('poste_alto_met_10', ''),  # P: POSTE ALTO (MET. 2")
                cartel_info.get('poste_bajo_met_10', ''),  # Q: POSTE BAJO (MET.)
                cartel_info.get('poste_bajo_mad_10', ''),  # R: POSTE BAJO (MAD.)
                # TRABAJO 20 - Colocación de cartel con instalación de Poste o mojón
                cartel_info.get('poste_alto_met_20', ''),  # S: POSTE ALTO (MET. 2")
                cartel_info.get('poste_bajo_mad_20', ''),  # T: POSTE BAJO (MAD. 3")
                cartel_info.get('mojon_met4_20', ''),  # U: MOJON (Met. 4")
                # TRABAJO 30 - Remoción y colocación con instalación de Poste o Mojón
                cartel_info.get('poste_alto_met_30', ''),  # V: POSTE ALTO (MET. 2")
                cartel_info.get('poste_bajo_mad_30', ''),  # W: POSTE BAJO (MAD. / MET.)
                cartel_info.get('mojon_met_30', ''),  # X: MOJON METALICO
                cartel_info.get('mojon_horm_30', ''),  # Y: MOJON HORMIGON
                enlace_antes_formula,  # Z: FOTOS ANTES
                enlace_despues_formula  # AA: FOTOS DESPUÉS
            ]
            
            # Encontrar la próxima fila disponible
            # La planilla tiene headers en filas 9-10, datos empiezan en fila 11
            # Buscar la última fila con datos en columna F (N° de item)
            col_f_values = worksheet.col_values(6)  # Columna F (índice 6)
            
            # Encontrar última fila con datos (después de fila 10)
            ultima_fila_con_datos = 10  # Mínimo es fila 10 (headers)
            for i, valor in enumerate(col_f_values, start=1):
                if i > 10 and valor.strip():  # Después de headers y con valor
                    ultima_fila_con_datos = i
            
            proxima_fila = ultima_fila_con_datos + 1
            
            print(f"📝 Escribiendo en fila {proxima_fila} de la planilla OUTPUT")
            
            # Escribir en la fila específica usando update (hasta columna AA para incluir FOTOS ANTES y DESPUÉS)
            rango = f"A{proxima_fila}:AA{proxima_fila}"
            worksheet.update(rango, [nueva_fila], value_input_option='USER_ENTERED')
            
            print(f"✅ Trabajo registrado en planilla OUTPUT: Item {numero_item}")
            print(f"   ✓ Fecha Ejecucion: {fecha_ejecucion}")
            print(f"   ✓ Gasoducto/Ramal: {cartel_info.get('gasoducto_ramal', '')}")
            print(f"   ✓ Ubicación: {cartel_info.get('ubicacion', '')}")
            print(f"   ✓ Tipo: {cartel_info.get('tipo_cartel', '')}")
            
            # Mostrar tipo de trabajo si existe
            tipo_trabajo = cartel_info.get('tipo_trabajo', '')
            if tipo_trabajo:
                print(f"   ✓ Tipo de trabajo: {tipo_trabajo}")
            
            if enlace_antes_formula or enlace_despues_formula:
                print(f"   ✓ Enlaces fotos: Fotos {str(numero_item).zfill(3)}-001 al 003 y -004 al 006")
                
            print(f"   ✓ Observaciones: Instalación EJECUTADA.-")
            
            return True
            
        except Exception as e:
            print(f"❌ Error al registrar trabajo en planilla OUTPUT: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def actualizar_enlace_carpeta_item(self, numero_item: str) -> bool:
        """Actualiza la columna W (columna 23) en el sheet con el enlace a la carpeta del item."""
        try:
            sheet = self._get_ecogas_sheet()
            if not sheet:
                return False
            
            worksheet = sheet.get_worksheet(0)
            
            # Crear carpeta si no existe
            folder_id = self.crear_carpeta_item(numero_item)
            if not folder_id:
                return False
            
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
            
            # Buscar fila del item (columna 2, índice 1)
            all_values = worksheet.get_all_values()
            for idx, row in enumerate(all_values[6:], start=7):  # Desde fila 7
                if len(row) > 1 and str(row[1]).strip() == str(numero_item):
                    # Actualizar columna W (columna 23) con el enlace
                    worksheet.update_cell(idx, 23, folder_url)
                    print(f"✅ Actualizado enlace de carpeta en columna W para item {numero_item}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error al actualizar enlace de carpeta: {e}")
            return False
    
    # ===== GOOGLE DRIVE - ALMACENAMIENTO DE IMÁGENES =====
    def crear_carpeta_item(self, numero_item: str) -> Optional[str]:
        """Crea o encuentra carpeta para un item específico (ej: 001, 002)."""
        try:
            parent_folder = self.imagenes_carteles_folder_id
            if not parent_folder:
                print("No se ha configurado IMAGENES_CARTELES_FOLDER_ID")
                return None
            
            folder_name = numero_item.zfill(3)  # 001, 002, etc.
            
            # Buscar si ya existe la carpeta
            query = f"name='{folder_name}' and '{parent_folder}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(q=query, fields='files(id, name)').execute()
            folders = results.get('files', [])
            
            if folders:
                return folders[0]['id']
            
            # Crear carpeta
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder]
            }
            folder = self.drive_service.files().create(body=folder_metadata, fields='id').execute()
            return folder.get('id')
            
        except Exception as e:
            print(f"Error al crear/buscar carpeta: {e}")
            return None
    
    def subir_imagen_a_drive(self, image_data: bytes, filename: str, numero_item: str) -> Optional[str]:
        """
        Sube una imagen a Google Drive en subcarpeta por número de item.
        
        Args:
            image_data: Datos binarios de la imagen
            filename: Nombre del archivo
            numero_item: Número del item/cartel para crear subcarpeta (ej: "1", "25")
        
        Returns:
            URL pública del archivo o None si falla
        """
        try:
            # Crear o encontrar carpeta del item
            item_folder_id = self.crear_carpeta_item(numero_item)
            
            if not item_folder_id:
                print(f"No se pudo crear carpeta para item {numero_item}")
                return None
            
            # Determinar tipo MIME basado en la extensión
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            
            extension = os.path.splitext(filename.lower())[1]
            mime_type = mime_types.get(extension, 'image/jpeg')
            
            # Preparar metadata del archivo
            file_metadata = {
                'name': filename,
                'parents': [item_folder_id]
            }
            
            # Crear media upload desde bytes directamente
            media = MediaInMemoryUpload(
                image_data,  # image_data ya es bytes, no necesita io.BytesIO
                mimetype=mime_type,
                resumable=True
            )
            
            # Subir archivo
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            file_id = file.get('id')
            
            if not file_id:
                print("No se pudo obtener el ID del archivo subido")
                return None
            
            # Hacer el archivo accesible públicamente
            try:
                self.drive_service.permissions().create(
                    fileId=file_id,
                    body={
                        'type': 'anyone',
                        'role': 'reader'
                    }
                ).execute()
            except Exception as perm_error:
                print(f"Advertencia: No se pudo establecer permisos públicos: {perm_error}")
            
            # Devolver URL de vista web
            web_view_link = file.get('webViewLink')
            web_content_link = file.get('webContentLink')
            
            # Preferir webContentLink para descarga directa
            return web_content_link or web_view_link or f"https://drive.google.com/file/d/{file_id}/view"
            
        except Exception as e:
            print(f"Error al subir imagen a Drive: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ===== GESTIÓN DE IMÁGENES ANTES/DESPUÉS =====
    def crear_estructura_carpetas_output(self, numero_item: str) -> Optional[Dict[str, str]]:
        """
        Crea la estructura de carpetas para almacenar imágenes antes/después.
        
        Estructura:
        - OUTPUT_IMAGENES_FOLDER_ID/
          - 001/
            - Antes/
            - Despues/
        
        Args:
            numero_item: Número del item (ej: "1", "25", "145")
        
        Returns:
            Dict con IDs de carpetas {'item': 'id', 'antes': 'id', 'despues': 'id'} o None
        """
        try:
            if not self.output_imagenes_folder_id:
                print("No se ha configurado OUTPUT_IMAGENES_FOLDER_ID")
                return None
            
            folder_name = str(numero_item).zfill(3)  # 001, 002, etc.
            
            # 1. Crear o buscar carpeta del item
            query = f"name='{folder_name}' and '{self.output_imagenes_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(
                q=query, 
                fields='files(id, name)',
                supportsAllDrives=True,  # ✨ Soporte Shared Drives
                includeItemsFromAllDrives=True  # ✨ Incluir items de Shared Drives
            ).execute()
            folders = results.get('files', [])
            
            if folders:
                item_folder_id = folders[0]['id']
                print(f"📁 Carpeta {folder_name} ya existe")
            else:
                # Crear carpeta del item
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [self.output_imagenes_folder_id]
                }
                folder = self.drive_service.files().create(
                    body=folder_metadata, 
                    fields='id',
                    supportsAllDrives=True  # ✨ Soporte Shared Drives
                ).execute()
                item_folder_id = folder.get('id')
                print(f"✅ Carpeta {folder_name} creada")
            
            # 2. Crear o buscar subcarpeta "Antes"
            query_antes = f"name='Antes' and '{item_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results_antes = self.drive_service.files().list(
                q=query_antes, 
                fields='files(id, name)',
                supportsAllDrives=True,  # ✨ Soporte Shared Drives
                includeItemsFromAllDrives=True  # ✨ Incluir items de Shared Drives
            ).execute()
            folders_antes = results_antes.get('files', [])
            
            if folders_antes:
                antes_folder_id = folders_antes[0]['id']
                print(f"📁 Subcarpeta Antes ya existe")
            else:
                folder_metadata_antes = {
                    'name': 'Antes',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [item_folder_id]
                }
                folder_antes = self.drive_service.files().create(
                    body=folder_metadata_antes, 
                    fields='id',
                    supportsAllDrives=True  # ✨ Soporte Shared Drives
                ).execute()
                antes_folder_id = folder_antes.get('id')
                print(f"✅ Subcarpeta Antes creada")
            
            # 3. Crear o buscar subcarpeta "Despues"
            query_despues = f"name='Despues' and '{item_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results_despues = self.drive_service.files().list(
                q=query_despues, 
                fields='files(id, name)',
                supportsAllDrives=True,  # ✨ Soporte Shared Drives
                includeItemsFromAllDrives=True  # ✨ Incluir items de Shared Drives
            ).execute()
            folders_despues = results_despues.get('files', [])
            
            if folders_despues:
                despues_folder_id = folders_despues[0]['id']
                print(f"📁 Subcarpeta Despues ya existe")
            else:
                folder_metadata_despues = {
                    'name': 'Despues',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [item_folder_id]
                }
                folder_despues = self.drive_service.files().create(
                    body=folder_metadata_despues, 
                    fields='id',
                    supportsAllDrives=True  # ✨ Soporte Shared Drives
                ).execute()
                despues_folder_id = folder_despues.get('id')
                print(f"✅ Subcarpeta Despues creada")
            
            return {
                'item': item_folder_id,
                'antes': antes_folder_id,
                'despues': despues_folder_id
            }
            
        except Exception as e:
            print(f"Error al crear estructura de carpetas: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def subir_imagen_antes_despues(
        self, 
        image_data: bytes, 
        filename: str, 
        numero_item: str, 
        momento: str = 'antes'
    ) -> Optional[str]:
        """
        Sube una imagen a la carpeta Antes o Despues de un item.
        
        Args:
            image_data: Datos binarios de la imagen
            filename: Nombre del archivo
            numero_item: Número del item (ej: "1", "25")
            momento: 'antes' o 'despues'
        
        Returns:
            URL pública del archivo o None si falla
        """
        try:
            # Crear estructura de carpetas si no existe
            carpetas = self.crear_estructura_carpetas_output(numero_item)
            
            if not carpetas:
                print(f"No se pudo crear estructura de carpetas para item {numero_item}")
                return None
            
            # Seleccionar carpeta según el momento
            folder_id = carpetas['antes'] if momento.lower() == 'antes' else carpetas['despues']
            
            # Determinar tipo MIME
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            
            extension = os.path.splitext(filename.lower())[1]
            mime_type = mime_types.get(extension, 'image/jpeg')
            
            # Preparar metadata del archivo
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # Crear media upload
            media = MediaInMemoryUpload(
                image_data,
                mimetype=mime_type,
                resumable=True
            )
            
            # Subir archivo con soporte para Shared Drives
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink',
                supportsAllDrives=True  # ✨ Habilitar soporte para Shared Drives
            ).execute()
            
            file_id = file.get('id')
            
            if not file_id:
                print("No se pudo obtener el ID del archivo subido")
                return None
            
            # Hacer el archivo accesible públicamente
            try:
                self.drive_service.permissions().create(
                    fileId=file_id,
                    body={
                        'type': 'anyone',
                        'role': 'reader'
                    },
                    supportsAllDrives=True  # ✨ Habilitar soporte para Shared Drives
                ).execute()
            except Exception as perm_error:
                print(f"Advertencia: No se pudo establecer permisos públicos: {perm_error}")
            
            # Devolver URL
            web_content_link = file.get('webContentLink')
            web_view_link = file.get('webViewLink')
            
            return web_content_link or web_view_link or f"https://drive.google.com/file/d/{file_id}/view"
            
        except Exception as e:
            print(f"Error al subir imagen {momento}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ===== BÚSQUEDA POR NÚMERO DE ITEM =====
    def buscar_cartel_por_item(self, item_number: str) -> Optional[Dict[str, Any]]:
        """
        Busca un cartel por su número de ítem.
        Acepta formatos: "2", "02", "002", "item 2", etc.
        """
        try:
            # Normalizar el número de ítem
            import re
            # Extraer números del texto
            match = re.search(r'\d+', str(item_number))
            if not match:
                return None
            
            item_num = int(match.group())
            
            # Obtener todos los carteles
            carteles = self.obtener_carteles_ecogas()
            
            # Buscar por número de ítem
            for cartel in carteles:
                cartel_num = cartel.get('numero', '')
                if cartel_num and int(cartel_num) == item_num:
                    return cartel
            
            return None
        except Exception as e:
            print(f"Error al buscar cartel por ítem: {e}")
            return None
    
    def obtener_imagenes_cartel(self, item_number: str) -> List[Dict[str, str]]:
        """
        Obtiene las imágenes de un cartel desde Google Drive.
        Busca en la carpeta principal de imágenes usando el número de ítem.
        """
        try:
            if not self.imagenes_carteles_folder_id:
                print("No se configuró la carpeta de imágenes de carteles")
                return []
            
            # Normalizar el número de ítem
            import re
            match = re.search(r'\d+', str(item_number))
            if not match:
                return []
            
            item_num = int(match.group())
            # Formatear con ceros a la izquierda (001, 002, etc.)
            item_formatted = f"{item_num:03d}"
            
            print(f"🔎 Buscando carpeta exacta para ítem: {item_formatted}")
            
            # Buscar carpeta con el nombre del ítem dentro de la carpeta principal
            # Primero buscar todas las carpetas que contengan el número
            query = f"'{self.imagenes_carteles_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1000,  # Aumentar límite para obtener todas las carpetas
                orderBy='name'  # Ordenar por nombre para obtener carpetas numéricas primero
            ).execute()
            
            all_folders = results.get('files', [])
            
            # Filtrar para encontrar coincidencia exacta del número
            folders = []
            print(f"📋 Total carpetas encontradas: {len(all_folders)}")
            for folder in all_folders:
                folder_name = folder['name']
                # Extraer todos los números del nombre de la carpeta
                folder_numbers = re.findall(r'\d+', folder_name)
                
                # Verificar si alguno de los números coincide con el ítem buscado
                for num_str in folder_numbers:
                    if int(num_str) == item_num:
                        folders.append(folder)
                        print(f"  ✓ Carpeta candidata: {folder_name} (ID: {folder['id']})")
                        break
            
            if not folders:
                print(f"❌ No se encontró carpeta para ítem {item_formatted}")
                print(f"📂 Carpetas disponibles: {[f['name'] for f in all_folders[:10]]}")
                return []
            
            # Usar la primera carpeta encontrada
            folder_id = folders[0]['id']
            folder_name = folders[0]['name']
            print(f"📁 Carpeta seleccionada: {folder_name} ({folder_id})")
            
            # Lista para acumular todas las imágenes
            all_images = []
            
            # Función recursiva para buscar en carpetas y subcarpetas
            def buscar_archivos_recursivamente(parent_id, nivel=0):
                indent = "  " * nivel
                print(f"{indent}🔍 Buscando en carpeta ID: {parent_id}")
                
                # Obtener TODOS los archivos (no carpetas) de esta carpeta
                query_files = f"'{parent_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed=false"
                
                results_files = self.drive_service.files().list(
                    q=query_files,
                    spaces='drive',
                    fields='files(id, name, mimeType, webViewLink, webContentLink)',
                    pageSize=500  # Aumentar límite para fotos en carpeta
                ).execute()
                
                files = results_files.get('files', [])
                print(f"{indent}📄 Encontrados {len(files)} archivos en este nivel")
                all_images.extend(files)
                
                # Buscar subcarpetas
                query_folders = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                
                results_folders = self.drive_service.files().list(
                    q=query_folders,
                    spaces='drive',
                    fields='files(id, name)',
                    pageSize=500  # Aumentar límite para subcarpetas
                ).execute()
                
                subfolders = results_folders.get('files', [])
                if subfolders:
                    print(f"{indent}📁 Encontradas {len(subfolders)} subcarpetas")
                    for subfolder in subfolders:
                        print(f"{indent}  ↳ {subfolder['name']} ({subfolder['id']})")
                        buscar_archivos_recursivamente(subfolder['id'], nivel + 1)
            
            # Iniciar búsqueda recursiva
            buscar_archivos_recursivamente(folder_id)
            
            images = all_images
            print(f"📋 Total archivos encontrados (incluyendo subcarpetas): {len(images)}")
            
            if images:
                print(f"📄 Lista completa de archivos:")
                for img in images:
                    print(f"  - {img['name']} ({img.get('mimeType', 'unknown')})")
            
            # Formatear las imágenes
            imagenes_list = []
            for img in images:
                # Hacer la imagen pública si no lo está
                try:
                    self.drive_service.permissions().create(
                        fileId=img['id'],
                        body={'type': 'anyone', 'role': 'reader'}
                    ).execute()
                except:
                    pass
                
                imagenes_list.append({
                    'id': img['id'],
                    'name': img['name'],
                    'url': f"https://drive.google.com/uc?export=view&id={img['id']}",
                    'web_view': img.get('webViewLink', ''),
                })
            
            print(f"🖼️ Encontradas {len(imagenes_list)} imágenes para ítem {item_formatted}")
            return imagenes_list
            
        except Exception as e:
            print(f"Error al obtener imágenes del cartel: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    # ===== LOG DE WHATSAPP =====
    def _get_whatsapp_log_sheet(self):
        """Obtiene la hoja LOG de WhatsApp con cache."""
        if self._whatsapp_log_sheet is None and self.whatsapp_log_sheet_id:
            self._whatsapp_log_sheet = self.client.open_by_key(self.whatsapp_log_sheet_id)
        return self._whatsapp_log_sheet
    
    def registrar_log_whatsapp(
        self,
        numero_telefono: str,
        tipo_mensaje: str,
        contenido: str,
        tiene_media: bool = False,
        media_url: str = "",
        item_relacionado: str = "",
        estado_flujo: str = "",
        respuesta_bot: str = "" 
    ) -> bool:
        """
        Registra cada interacción de WhatsApp en una hoja LOG para trazabilidad.
        
        Args:
            numero_telefono: Número de WhatsApp del usuario
            tipo_mensaje: 'recibido' o 'enviado'
            contenido: Texto del mensaje
            tiene_media: Si el mensaje incluye imagen/archivo
            media_url: URL del media si existe
            item_relacionado: Número de item si aplica
            estado_flujo: Estado actual (esperando_antes, en_trabajo, etc.)
            respuesta_bot: Respuesta automática del bot
            
        Returns:
            True si se registró correctamente
        """
        try:
            log_sheet = self._get_whatsapp_log_sheet()
            if not log_sheet:
                print("No se configuró hoja LOG de WhatsApp")
                return False
            
            # Buscar o crear pestaña LOG
            try:
                worksheet = log_sheet.worksheet("LOG_WhatsApp")
            except:
                # Crear pestaña si no existe
                worksheet = log_sheet.add_worksheet(
                    title="LOG_WhatsApp",
                    rows=1000,
                    cols=10
                )
                # Agregar encabezados
                headers = [
                    "Timestamp",
                    "Fecha",
                    "Hora",
                    "Número",
                    "Tipo",
                    "Mensaje",
                    "Tiene Media",
                    "URL Media",
                    "Item",
                    "Estado Flujo",
                    "Respuesta Bot"
                ]
                worksheet.append_row(headers)
            
            # Preparar datos
            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            fecha = now.strftime("%d/%m/%Y")
            hora = now.strftime("%H:%M:%S")
            
            fila = [
                timestamp,
                fecha,
                hora,
                numero_telefono,
                tipo_mensaje,
                contenido[:500] if contenido else "",  # Limitar a 500 caracteres
                "Sí" if tiene_media else "No",
                media_url[:300] if media_url else "",  # Limitar URL
                str(item_relacionado) if item_relacionado else "",
                estado_flujo,
                respuesta_bot[:500] if respuesta_bot else ""  # Limitar respuesta
            ]
            
            # Agregar fila
            worksheet.append_row(fila)
            print(f"📋 Log WhatsApp registrado: {numero_telefono} - {tipo_mensaje}")
            return True
            
        except Exception as e:
            print(f"Error al registrar log WhatsApp: {e}")
            import traceback
            traceback.print_exc()
            return False
