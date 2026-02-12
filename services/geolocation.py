from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from typing import Optional, Dict
import time


class GeolocationService:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="ecogas_vialparking")
    
    def obtener_direccion(self, latitud: float, longitud: float) -> Optional[str]:
        """
        Convierte coordenadas a dirección.
        
        Args:
            latitud: Latitud en formato decimal
            longitud: Longitud en formato decimal
        
        Returns:
            Dirección como string o None
        """
        try:
            location = self.geolocator.reverse(
                f"{latitud}, {longitud}",
                language="es",
                timeout=10
            )
            
            if location:
                return location.address
            return None
            
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Error de geolocalización: {e}")
            return None
    
    def geocodificar_direccion(self, direccion: str, region: str = "Argentina") -> Optional[Dict[str, float]]:
        """
        Convierte una dirección en coordenadas.
        
        Args:
            direccion: Dirección a geocodificar
            region: Región/país para contexto
        
        Returns:
            Dict con latitud y longitud o None
        """
        try:
            # Agregar contexto regional si no está presente
            if region not in direccion and "Argentina" not in direccion:
                direccion = f"{direccion}, {region}"
            
            location = self.geolocator.geocode(direccion, timeout=10)
            
            if location:
                return {
                    "latitud": location.latitude,
                    "longitud": location.longitude
                }
            return None
            
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Error de geocodificación: {e}")
            return None
    
    def validar_en_argentina(self, latitud: float, longitud: float) -> bool:
        """
        Verifica si las coordenadas están dentro de Argentina.
        
        Argentina aproximadamente:
        Latitud: -55.0 a -21.0 (de Tierra del Fuego a Jujuy)
        Longitud: -73.5 a -53.0 (de Andes a costa atlántica)
        """
        return (
            -55.0 <= latitud <= -21.0 and
            -73.5 <= longitud <= -53.0
        )
    
    def validar_en_region_ecogas(self, latitud: float, longitud: float) -> bool:
        """
        Verifica si las coordenadas están en la zona de cobertura de ECOGAS.
        ECOGAS opera principalmente en Buenos Aires y alrededores.
        
        Zona aproximada de cobertura:
        Latitud: -35.5 a -33.5 (Gran Buenos Aires y zona de influencia)
        Longitud: -59.5 a -57.5
        
        Esta es una validación amplia. Para validación precisa se debería 
        usar polígonos específicos de las zonas de concesión.
        """
        return (
            -35.5 <= latitud <= -33.5 and
            -59.5 <= longitud <= -57.5
        )
    
    def calcular_distancia(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcula la distancia en kilómetros entre dos puntos.
        """
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Radio de la Tierra en km
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        a = sin(delta_lat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c
    
    def encontrar_cartel_mas_cercano(
        self, 
        latitud: float, 
        longitud: float, 
        carteles: list,
        radio_max_km: float = 5.0
    ) -> Optional[Dict]:
        """
        Encuentra el cartel más cercano a una ubicación dada.
        
        Args:
            latitud: Latitud del punto de búsqueda
            longitud: Longitud del punto de búsqueda
            carteles: Lista de carteles con 'latitud' y 'longitud'
            radio_max_km: Radio máximo de búsqueda en kilómetros (default 5 km)
        
        Returns:
            Dict con el cartel más cercano y la distancia, o None si no hay ninguno cerca
        """
        cartel_mas_cercano = None
        distancia_minima = float('inf')
        
        for cartel in carteles:
            # Validar que el cartel tenga coordenadas válidas
            lat_cartel = cartel.get('latitud')
            lon_cartel = cartel.get('longitud')
            
            if lat_cartel is None or lon_cartel is None:
                continue
            
            try:
                # Calcular distancia
                distancia = self.calcular_distancia(
                    latitud, 
                    longitud, 
                    float(lat_cartel), 
                    float(lon_cartel)
                )
                
                # Verificar si está dentro del radio y es más cercano
                if distancia < distancia_minima and distancia <= radio_max_km:
                    distancia_minima = distancia
                    cartel_mas_cercano = cartel.copy()
                    cartel_mas_cercano['distancia_km'] = round(distancia, 2)
                    
            except (ValueError, TypeError) as e:
                print(f"Error calculando distancia para cartel {cartel.get('numero', 'desconocido')}: {e}")
                continue
        
        return cartel_mas_cercano

