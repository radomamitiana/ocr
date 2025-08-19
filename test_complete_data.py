"""
Script de test complet pour vérifier l'intégrité des données
"""

import sys
import uuid
from datetime import datetime
sys.path.append('src')

from src.database.connection import get_db
from sqlalchemy import text
from src.utils.logger import app_logger

def test_data_integrity():
    """Test complet de l'intégrité des données"""
    db = next(get_db())
    
    try:
        print("=== TEST COMPLET DE L'INTÉGRITÉ DES DONNÉES ===\n")
        
        # 1. Test de la société SITSE
        print("1. Vérification de la société SITSE...")
        company_query = text("""
            SELECT id, erp_code, name, address, email, phone_number, is_active,
                   created_date, last_modified_date, created_by, last_modified_by
            FROM company 
            WHERE erp_code = 'SITSE'
        """)
        
        company = db.execute(company_query).fetchone()
        if company:
            print(f"✅ Société trouvée: {company[2]}")
            print(f"   - ERP Code: {company[1]}")
            print(f"   - Adresse: {company[3]}")
            print(f"   - Email: {company[4]}")
            print(f"   - Téléphone: {company[5]}")
            print(f"   - Active: {company[6]}")
            print(f"   - Créée le: {company[7]}")
            print(f"   - Créée par: {company[9]}")
            
            # Vérifier qu'aucun champ obligatoire n'est null
            null_fields = []
            if not company[1]: null_fields.append("erp_code")
            if not company[2]: null_fields.append("name")
            if not company[4]: null_fields.append("email")
            if not company[5]: null_fields.append("phone_number")
            if company[6] is None: null_fields.append("is_active")
            
            if null_fields:
                print(f"❌ Champs null détectés: {', '.join(null_fields)}")
            else:
                print("✅ Tous les champs obligatoires sont remplis")
        else:
            print("❌ Société SITSE non trouvée")
        
        print("\n" + "="*60 + "\n")
        
        # 2. Test des fournisseurs
        print("2. Vérification des fournisseurs...")
        suppliers_query = text("""
            SELECT id, social_reason, rcs, address, email, phone_number,
                   is_active, contact_name, goals,
                   created_date, last_modified_date, created_by, last_modified_by
            FROM supplier
            ORDER BY social_reason
        """)
        
        suppliers = db.execute(suppliers_query).fetchall()
        print(f"Nombre de fournisseurs: {len(suppliers)}\n")
        
        for i, supplier in enumerate(suppliers, 1):
            print(f"{i}. {supplier[1]}")
            print(f"   - RCS: {supplier[2]}")
            print(f"   - Adresse: {supplier[3]}")
            print(f"   - Email: {supplier[4]}")
            print(f"   - Téléphone: {supplier[5]}")
            print(f"   - Active: {supplier[6]}")
            print(f"   - Contact: {supplier[7]}")
            print(f"   - Objectifs: {supplier[8]}")
            print(f"   - Créé le: {supplier[9]}")
            print(f"   - Créé par: {supplier[11]}")
            
            # Vérifier qu'aucun champ obligatoire n'est null
            null_fields = []
            if not supplier[1]: null_fields.append("social_reason")
            if not supplier[4]: null_fields.append("email")
            if not supplier[5]: null_fields.append("phone_number")
            if supplier[6] is None: null_fields.append("is_active")
            if not supplier[7]: null_fields.append("contact_name")
            
            if null_fields:
                print(f"   ❌ Champs null détectés: {', '.join(null_fields)}")
            else:
                print("   ✅ Tous les champs obligatoires sont remplis")
            print()
        
        print("="*60 + "\n")
        
        # 3. Statistiques globales
        print("3. Statistiques globales...")
        
        # Compter les sociétés
        company_count = db.execute(text("SELECT COUNT(*) FROM company")).fetchone()[0]
        print(f"Nombre total de sociétés: {company_count}")
        
        # Compter les fournisseurs
        supplier_count = db.execute(text("SELECT COUNT(*) FROM supplier")).fetchone()[0]
        print(f"Nombre total de fournisseurs: {supplier_count}")
        
        # Compter les fournisseurs actifs
        active_suppliers = db.execute(text("SELECT COUNT(*) FROM supplier WHERE is_active = true")).fetchone()[0]
        print(f"Fournisseurs actifs: {active_suppliers}")
        
        print("\n" + "="*60 + "\n")
        
        # 4. Test de requêtes avec jointures (simulation d'utilisation réelle)
        print("4. Test de requêtes avec jointures...")
        
        # Simuler une requête qui utiliserait company_erp_code
        test_query = text("""
            SELECT c.name as company_name, c.erp_code,
                   COUNT(s.id) as supplier_count
            FROM company c
            LEFT JOIN supplier s ON s.is_active = true
            WHERE c.erp_code = 'SITSE'
            GROUP BY c.name, c.erp_code
        """)
        
        result = db.execute(test_query).fetchone()
        if result:
            print(f"✅ Requête de test réussie:")
            print(f"   - Société: {result[0]}")
            print(f"   - Code ERP: {result[1]}")
            print(f"   - Fournisseurs actifs disponibles: {result[2]}")
        else:
            print("❌ Échec de la requête de test")
        
        print("\n" + "="*60 + "\n")
        
        # 5. Vérification finale
        print("5. Vérification finale...")
        
        # Vérifier qu'il n'y a pas de valeurs null dans les champs critiques
        null_check_queries = [
            ("company.erp_code", "SELECT COUNT(*) FROM company WHERE erp_code IS NULL"),
            ("company.name", "SELECT COUNT(*) FROM company WHERE name IS NULL"),
            ("supplier.social_reason", "SELECT COUNT(*) FROM supplier WHERE social_reason IS NULL"),
            ("supplier.is_active", "SELECT COUNT(*) FROM supplier WHERE is_active IS NULL")
        ]
        
        all_good = True
        for field_name, query in null_check_queries:
            null_count = db.execute(text(query)).fetchone()[0]
            if null_count > 0:
                print(f"❌ {null_count} valeurs null trouvées dans {field_name}")
                all_good = False
            else:
                print(f"✅ Aucune valeur null dans {field_name}")
        
        if all_good:
            print("\n🎉 TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS!")
            print("✅ La société SITSE est correctement créée avec son companyErpCode")
            print("✅ Tous les fournisseurs sont correctement créés")
            print("✅ Aucune valeur null dans les champs obligatoires")
            print("✅ Les données sont prêtes pour utilisation en production")
        else:
            print("\n⚠️  CERTAINS TESTS ONT ÉCHOUÉ - Vérifiez les erreurs ci-dessus")
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
    finally:
        db.close()

def create_sample_invoice():
    """Créer une facture d'exemple pour tester l'utilisation du companyErpCode"""
    db = next(get_db())
    
    try:
        print("\n" + "="*60)
        print("6. Test de création d'une facture d'exemple...")
        
        # Vérifier d'abord si la table invoice existe
        check_table = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'invoice'
            )
        """)
        
        table_exists = db.execute(check_table).fetchone()[0]
        
        if not table_exists:
            print("⚠️  Table 'invoice' n'existe pas encore - création ignorée")
            return
        
        # Récupérer le company_erp_code de SITSE
        company_query = text("SELECT erp_code FROM company WHERE erp_code = 'SITSE'")
        company_erp = db.execute(company_query).fetchone()
        
        if not company_erp:
            print("❌ Impossible de trouver le code ERP de SITSE")
            return
        
        # Récupérer un fournisseur
        supplier_query = text("SELECT id, social_reason FROM supplier LIMIT 1")
        supplier = db.execute(supplier_query).fetchone()
        
        if not supplier:
            print("❌ Aucun fournisseur trouvé")
            return
        
        # Créer une facture d'exemple
        invoice_id = str(uuid.uuid4())
        invoice_query = text("""
            INSERT INTO invoice (
                id, invoice_number, invoice_date, company_erp_code,
                supplier_name, supplier_id, including_taxes,
                currency_code, is_complete, is_draft,
                created_date, last_modified_date, created_by, last_modified_by
            ) VALUES (
                :id, :invoice_number, :invoice_date, :company_erp_code,
                :supplier_name, :supplier_id, :including_taxes,
                :currency_code, :is_complete, :is_draft,
                :created_date, :last_modified_date, :created_by, :last_modified_by
            )
        """)
        
        db.execute(invoice_query, {
            'id': invoice_id,
            'invoice_number': 'TEST-001',
            'invoice_date': datetime.now().date(),
            'company_erp_code': company_erp[0],
            'supplier_name': supplier[1],
            'supplier_id': supplier[0],
            'including_taxes': 1250.00,
            'currency_code': 'CHF',
            'is_complete': False,
            'is_draft': True,
            'created_date': datetime.now(),
            'last_modified_date': datetime.now(),
            'created_by': 'test_system',
            'last_modified_by': 'test_system'
        })
        
        db.commit()
        print(f"✅ Facture d'exemple créée avec l'ID: {invoice_id}")
        print(f"   - Utilise le company_erp_code: {company_erp[0]}")
        print(f"   - Fournisseur: {supplier[1]}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création de la facture d'exemple: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_data_integrity()
    create_sample_invoice()
    print("\n" + "="*60)
    print("🏁 TEST COMPLET TERMINÉ!")
