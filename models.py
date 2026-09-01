from db import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
from flask_login import UserMixin


# 1. Tabla de Usuarios (Participantes y Administradores)
class Usuario(Base, UserMixin):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)

    # Campo para permisos
    es_admin = Column(Boolean, default=False)

    # Datos de competición
    # Guardamos el nombre para que tu código actual no se rompa
    juego_seleccionado = Column(String(100), nullable=True)

    # Relación con la tabla juegos para cumplir el requisito de gestión
    juego_id = Column(Integer, ForeignKey('juegos.id'), nullable=True)

    nivel = Column(String(50), nullable=True)  # Amateur, Normal, Expert
    rol = Column(String(50), nullable=True)

    # Puntos para las gráficas y rankings
    puntos = Column(Integer, default=0)

    # Campo para la foto de perfil
    foto_perfil = Column(String(150), nullable=True, default="default_avatar.png")


# 2. Tabla de Juegos (Lo que el administrador gestionará)
class Juego(Base):
    __tablename__ = "juegos"
    id = Column(Integer, primary_key=True)
    titulo = Column(String(100), nullable=False)
    descripcion = Column(Text)
    es_default = Column(Boolean, default=False)