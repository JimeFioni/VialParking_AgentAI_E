from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vialparking.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class EstadoCartel(str, enum.Enum):
    PARA_REEMPLAZAR = "para_reemplazar"
    EN_PROCESO = "en_proceso"
    REEMPLAZADO = "reemplazado"


class RegistroCartel(Base):
    __tablename__ = "registros_carteles"

    id = Column(Integer, primary_key=True, index=True)
    operario = Column(String, nullable=False)
    accion = Column(String, nullable=False)  # Observaciones/acciones a realizar
    tipo_cartel = Column(String, nullable=False)  # Tipo de cartel
    gasoducto = Column(String)  # Nombre del gasoducto/ramal
    estado = Column(String, nullable=False, default=EstadoCartel.PARA_REEMPLAZAR.value)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    direccion = Column(String)
    foto_url = Column(String)
    fecha_trabajo = Column(DateTime, default=datetime.utcnow)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    whatsapp_number = Column(String)
    notas = Column(String)


class MovimientoStock(Base):
    __tablename__ = "movimientos_stock"

    id = Column(Integer, primary_key=True, index=True)
    tipo_cartel = Column(String, nullable=False)
    cantidad = Column(Integer, nullable=False)
    tipo_movimiento = Column(String, nullable=False)  # entrada, salida
    operario = Column(String)
    registro_cartel_id = Column(Integer)
    fecha = Column(DateTime, default=datetime.utcnow)
    notas = Column(String)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
