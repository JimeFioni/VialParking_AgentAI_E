from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EstadoCartel(str, Enum):
    PARA_REEMPLAZAR = "para_reemplazar"
    EN_PROCESO = "en_proceso"
    REEMPLAZADO = "reemplazado"


class WhatsAppMessage(BaseModel):
    From: str
    Body: str
    MediaUrl0: Optional[str] = None
    Latitude: Optional[float] = None
    Longitude: Optional[float] = None


class CartelCreate(BaseModel):
    operario: str
    accion: str  # Observaciones de la planilla
    tipo_cartel: str  # Tipo de cartel de la planilla
    gasoducto: Optional[str] = None  # Nombre del gasoducto/ramal
    estado: EstadoCartel
    latitud: float
    longitud: float
    direccion: Optional[str] = None
    foto_url: Optional[str] = None
    whatsapp_number: Optional[str] = None
    notas: Optional[str] = None


class CartelResponse(BaseModel):
    id: int
    operario: str
    accion: str
    tipo_cartel: str
    gasoducto: Optional[str]
    estado: str
    latitud: float
    longitud: float
    direccion: Optional[str]
    foto_url: Optional[str]
    fecha_trabajo: datetime
    fecha_creacion: datetime
    whatsapp_number: Optional[str]
    notas: Optional[str]

    class Config:
        from_attributes = True


class StockItem(BaseModel):
    tipo_cartel: str
    cantidad: int
    ubicacion: Optional[str] = None


class StockAlert(BaseModel):
    tipo_cartel: str
    cantidad_actual: int
    threshold: int
    mensaje: str


class AgentDecision(BaseModel):
    autorizado: bool
    accion: Optional[str]
    tipo_cartel: Optional[str]
    gasoducto: Optional[str]
    confianza: float
    razon: str
    requiere_stock: bool = True


class PlanillaEcogas(BaseModel):
    """Modelo para datos de la planilla de ECOGAS"""
    tipo_cartel: str  # Columna "Tipo"
    observaciones: str  # Columna "Observaciones"
    gasoducto: Optional[str] = None  # Nombre del gasoducto/ramal
    latitud: Optional[float] = None  # Georeferencia
    longitud: Optional[float] = None  # Georeferencia
    estado: str = "pendiente"
