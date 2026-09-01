from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Conecto a la base de datos del torneo
engine = create_engine('sqlite:///database/torneo.db', connect_args={"check_same_thread": False})

# Configuro la sesión para poder guardar datos
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()