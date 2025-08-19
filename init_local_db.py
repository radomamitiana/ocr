"""
Script d'initialisation de la base de données locale
"""

import sys
from pathlib import Path

# Ajout du chemin src au PYTHONPATH
sys.path.append(str(Path(__file__).parent / "src"))

from src.database.connection import engine, test_connection
from src.database.models import Base, Company, Supplier, Invoice, InvoiceGoal, InvoiceLineItem, InvoiceMLData, Goal, Post, PrincipalAccount
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime
from decimal import Decimal
import uuid

def create_tables():
    """Crée toutes les tables"""
    print("Création des tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées avec succès")

def insert_sample_data():
    """Insère des données d'exemple"""
    print("Insertion des données d'exemple...")
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Création de la société SITSE (exemple fourni)
        company_sitse = Company(
            company_erp_code="SITSE001",
            company_name="SITSE Services Industriels de Terre Sainte et Environs",
            company_address="Chemin Ballessert 5, 1297 Founex",
            created_by="system"
        )
        db.add(company_sitse)
        
        # Création d'une société supplémentaire
        company = Company(
            company_erp_code="COMP001",
            company_name="Ma Société SARL",
            company_address="123 Rue de la Paix, 75001 Paris, France",
            created_by="system"
        )
        db.add(company)
        
        # Création d'un fournisseur (qui envoie la facture)
        supplier = Supplier(
            social_reason="Fournisseur Services SARL",
            rcs="98765432109876",
            address="456 Avenue des Champs, 69000 Lyon, France",
            email="contact@fournisseur.fr",
            phone_number="04.12.34.56.78",
            is_active=True,
            contact_name="Jean Dupont",
            goals=[1001, 1002],
            created_by="system"
        )
        db.add(supplier)
        
        # Création d'un autre fournisseur
        supplier2 = Supplier(
            social_reason="TechnoServices Pro",
            rcs="11223344556677",
            address="789 Boulevard Tech, 13000 Marseille, France",
            email="info@technoservices.fr",
            phone_number="04.91.23.45.67",
            is_active=True,
            contact_name="Marie Martin",
            goals=[2001, 2002],
            created_by="system"
        )
        db.add(supplier2)
        
        db.flush()  # Pour obtenir les IDs
        
        # Création d'une facture d'exemple
        invoice = Invoice(
            invoice_number="FAC-2025-001",
            invoice_date=date(2025, 1, 15),
            company_erp_code=company.company_erp_code,
            supplier_name=supplier.social_reason,
            excluding_taxes=Decimal("1000.00"),
            vat=Decimal("200.00"),
            including_taxes=Decimal("1200.00"),
            payment_state="PENDING",
            currency_code="EUR",
            is_complete=True,
            is_draft=False,
            document_url="documents/facture_exemple.pdf",
            supplier_id=supplier.id,
            created_by="system"
        )
        db.add(invoice)
        db.flush()
        
        # Création d'un invoice_goal pour cette facture
        invoice_goal = InvoiceGoal(
            invoice_id=invoice.id,
            goal_id=uuid.uuid4(),
            post_id=uuid.uuid4(),
            amount=Decimal("1200.00"),
            goal_account_number=1001,
            post_account_number=2001,
            created_by="system"
        )
        db.add(invoice_goal)
        
        # Création d'une deuxième facture
        invoice2 = Invoice(
            invoice_number="FAC-2025-002",
            invoice_date=date(2025, 1, 20),
            company_erp_code=company.company_erp_code,
            supplier_name=supplier2.social_reason,
            excluding_taxes=Decimal("500.00"),
            vat=Decimal("100.00"),
            including_taxes=Decimal("600.00"),
            payment_state="DRAFT",
            currency_code="EUR",
            is_complete=False,
            is_draft=True,
            document_url="documents/facture_techno.pdf",
            supplier_id=supplier2.id,
            created_by="system"
        )
        db.add(invoice2)
        db.flush()
        
        # Invoice goal pour la deuxième facture
        invoice_goal2 = InvoiceGoal(
            invoice_id=invoice2.id,
            goal_id=uuid.uuid4(),
            post_id=uuid.uuid4(),
            amount=Decimal("600.00"),
            goal_account_number=2001,
            post_account_number=3001,
            created_by="system"
        )
        db.add(invoice_goal2)
        
        db.commit()
        print("✅ Données d'exemple insérées avec succès")
        
        # Affichage des statistiques
        print(f"\nStatistiques:")
        print(f"- Sociétés: {db.query(Company).count()}")
        print(f"- Fournisseurs: {db.query(Supplier).count()}")
        print(f"- Factures: {db.query(Invoice).count()}")
        print(f"- Invoice Goals: {db.query(InvoiceGoal).count()}")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion des données: {str(e)}")
        db.rollback()
    finally:
        db.close()

def main():
    """Fonction principale"""
    print("=== Initialisation de la base de données locale ===\n")
    
    # Test de connexion
    print("1. Test de connexion...")
    if not test_connection():
        print("❌ Impossible de se connecter à la base de données")
        return
    
    # Création des tables
    create_tables()
    
    # Insertion des données d'exemple
    insert_sample_data()
    
    print("\n✅ Initialisation terminée avec succès!")
    print("\nVous pouvez maintenant tester l'API avec des données réelles.")

if __name__ == "__main__":
    main()
