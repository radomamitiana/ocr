"""
Configuration et connexion à la base de données PostgreSQL
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import Generator
import os
from src.utils.logger import app_logger

# Configuration de la base de données
DATABASE_URL = "postgresql://localhost:5432/ged"

# Création de l'engine SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # Mettre à True pour voir les requêtes SQL
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base pour les modèles
Base = declarative_base()


def get_db() -> Generator:
    """
    Générateur de session de base de données pour FastAPI
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """
    Test de la connexion à la base de données
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            app_logger.info("Connexion à la base de données réussie")
            return True
    except SQLAlchemyError as e:
        app_logger.error(f"Erreur de connexion à la base de données: {str(e)}")
        return False


def get_table_structure(table_name: str):
    """
    Récupère la structure d'une table
    """
    try:
        with engine.connect() as connection:
            # Récupération des colonnes
            columns_query = text("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = :table_name 
                ORDER BY ordinal_position
            """)
            
            columns_result = connection.execute(columns_query, {"table_name": table_name})
            columns = columns_result.fetchall()
            
            # Récupération des contraintes
            constraints_query = text("""
                SELECT 
                    tc.constraint_name,
                    tc.constraint_type,
                    kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = :table_name
            """)
            
            constraints_result = connection.execute(constraints_query, {"table_name": table_name})
            constraints = constraints_result.fetchall()
            
            return {
                "columns": [dict(row._mapping) for row in columns],
                "constraints": [dict(row._mapping) for row in constraints]
            }
            
    except SQLAlchemyError as e:
        app_logger.error(f"Erreur lors de la récupération de la structure de {table_name}: {str(e)}")
        return None


def analyze_database_schema():
    """
    Analyse complète du schéma de la base de données
    """
    tables_to_analyze = ['invoice', 'invoice_goal', 'company', 'supplier']
    schema_info = {}
    
    for table_name in tables_to_analyze:
        app_logger.info(f"Analyse de la table {table_name}")
        structure = get_table_structure(table_name)
        if structure:
            schema_info[table_name] = structure
        else:
            app_logger.warning(f"Impossible d'analyser la table {table_name}")
    
    return schema_info


def get_all_tables():
    """
    Récupère la liste de toutes les tables dans la base de données
    """
    try:
        with engine.connect() as connection:
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
            result = connection.execute(tables_query)
            tables = [row[0] for row in result.fetchall()]
            return tables
            
    except SQLAlchemyError as e:
        app_logger.error(f"Erreur lors de la récupération des tables: {str(e)}")
        return []
