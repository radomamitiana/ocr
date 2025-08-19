"""
Script pour insérer les données de test dans la base de données
"""

import sys
import uuid
from datetime import datetime
sys.path.append('src')

from src.database.connection import get_db
from sqlalchemy import text
from src.utils.logger import app_logger

def insert_company_data():
    """Insère ou met à jour la société SITSE dans la table company"""
    db = next(get_db())
    
    try:
        # Vérifier d'abord la structure de la table company
        check_query = text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'company'
            ORDER BY ordinal_position
        """)
        
        columns = db.execute(check_query).fetchall()
        print("Structure de la table company:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
        
        # Vérifier si SITSE existe déjà
        check_existing = text("SELECT id, erp_code FROM company WHERE erp_code = 'SITSE'")
        existing = db.execute(check_existing).fetchone()
        
        if existing:
            print(f"✅ Société SITSE existe déjà avec l'ID: {existing[0]}")
            return
        
        # Insérer la société SITSE avec le companyErpCode
        company_id = str(uuid.uuid4())
        insert_query = text("""
            INSERT INTO company (
                id, erp_code, name, address, email, phone_number, is_active,
                created_date, last_modified_date, created_by, last_modified_by
            ) VALUES (
                :id, :erp_code, :name, :address, :email, :phone_number, :is_active,
                :created_date, :last_modified_date, :created_by, :last_modified_by
            )
        """)
        
        db.execute(insert_query, {
            'id': company_id,
            'erp_code': 'SITSE',
            'name': 'SITSE Services Industriels de Terre-Sainte et Environs',
            'address': '7 rond point de stockholm, 1260 Nyon, Suisse',
            'email': 'contact@sitse.ch',
            'phone_number': '+41 22 316 40 50',
            'is_active': True,
            'created_date': datetime.now(),
            'last_modified_date': datetime.now(),
            'created_by': 'system',
            'last_modified_by': 'system'
        })
        
        db.commit()
        print(f"✅ Société SITSE insérée avec l'ID: {company_id}")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion de la société: {str(e)}")
        db.rollback()
    finally:
        db.close()

def insert_supplier_data():
    """Insère les fournisseurs dans la table supplier"""
    db = next(get_db())
    
    suppliers = [
        {
            'social_reason': 'YAPI Electromécanique SA',
            'rcs': 'CHE-234.567.890',
            'address': 'Rue de la Gare 12, 1260 Nyon, Suisse',
            'email': 'contact@yapi-electro.ch',
            'phone_number': '+41 22 361 12 34',
            'contact_name': 'Jean Dupont',
            'goals': [1, 2, 3]  # Objectifs exemple
        },
        {
            'social_reason': 'STS Soudure - Tuyauterie - Service',
            'rcs': 'CHE-345.678.901',
            'address': 'Zone Industrielle, Chemin des Plantaz 15, 1260 Nyon, Suisse',
            'email': 'info@sts-nyon.ch',
            'phone_number': '+41 22 361 45 67',
            'contact_name': 'Pierre Martin',
            'goals': [2, 4]
        },
        {
            'social_reason': 'SI NYON',
            'rcs': 'CHE-456.789.012',
            'address': 'Services Industriels de Nyon, Place du Château 3, 1260 Nyon, Suisse',
            'email': 'services@nyon.ch',
            'phone_number': '+41 22 316 40 40',
            'contact_name': 'Marie Leroy',
            'goals': [1, 3, 5]
        },
        {
            'social_reason': 'Romande Energie SA',
            'rcs': 'CHE-567.890.123',
            'address': 'Rue de Lausanne 53, 1110 Morges, Suisse',
            'email': 'contact@romande-energie.ch',
            'phone_number': '+41 21 802 95 95',
            'contact_name': 'Laurent Blanc',
            'goals': [1, 2]
        }
    ]
    
    try:
        # Vérifier d'abord la structure de la table supplier
        check_query = text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'supplier'
            ORDER BY ordinal_position
        """)
        
        columns = db.execute(check_query).fetchall()
        print("\nStructure de la table supplier:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
        
        for supplier in suppliers:
            # Vérifier si le fournisseur existe déjà
            check_existing = text("SELECT id FROM supplier WHERE social_reason = :social_reason")
            existing = db.execute(check_existing, {'social_reason': supplier['social_reason']}).fetchone()
            
            if existing:
                print(f"✅ Fournisseur '{supplier['social_reason']}' existe déjà avec l'ID: {existing[0]}")
                continue
            
            supplier_id = str(uuid.uuid4())
            insert_query = text("""
                INSERT INTO supplier (
                    id, social_reason, rcs, address, email, phone_number,
                    is_active, contact_name, goals,
                    created_date, last_modified_date, created_by, last_modified_by
                ) VALUES (
                    :id, :social_reason, :rcs, :address, :email, :phone_number,
                    :is_active, :contact_name, :goals,
                    :created_date, :last_modified_date, :created_by, :last_modified_by
                )
            """)
            
            db.execute(insert_query, {
                'id': supplier_id,
                'social_reason': supplier['social_reason'],
                'rcs': supplier['rcs'],
                'address': supplier['address'],
                'email': supplier['email'],
                'phone_number': supplier['phone_number'],
                'is_active': True,
                'contact_name': supplier['contact_name'],
                'goals': supplier['goals'],
                'created_date': datetime.now(),
                'last_modified_date': datetime.now(),
                'created_by': 'system',
                'last_modified_by': 'system'
            })
            
            print(f"✅ Fournisseur '{supplier['social_reason']}' inséré avec l'ID: {supplier_id}")
        
        db.commit()
        print("✅ Tous les fournisseurs ont été insérés avec succès")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion des fournisseurs: {str(e)}")
        db.rollback()
    finally:
        db.close()

def verify_data():
    """Vérifie que les données ont été insérées correctement"""
    db = next(get_db())
    
    try:
        # Vérifier les sociétés
        company_query = text("SELECT id, name, erp_code FROM company")
        companies = db.execute(company_query).fetchall()
        
        print("\n=== Sociétés dans la base ===")
        for company in companies:
            print(f"  - {company[1]} (ERP: {company[2]}, ID: {company[0]})")
        
        # Vérifier les fournisseurs
        supplier_query = text("SELECT id, social_reason, email FROM supplier")
        suppliers = db.execute(supplier_query).fetchall()
        
        print("\n=== Fournisseurs dans la base ===")
        for supplier in suppliers:
            print(f"  - {supplier[1]} ({supplier[2]}, ID: {supplier[0]})")
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    print("=== Insertion des données de test ===")
    
    print("\n1. Insertion de la société SITSE...")
    insert_company_data()
    
    print("\n2. Insertion des fournisseurs...")
    insert_supplier_data()
    
    print("\n3. Vérification des données...")
    verify_data()
    
    print("\n✅ Script terminé!")
