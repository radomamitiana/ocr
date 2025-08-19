"""
Service pour la gestion des factures avec sauvegarde en base de données
"""

import uuid
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.api.models import InvoiceData
from src.api.invoice_models import InvoiceDTO, InvoiceGoalDTO, PaymentStatus
from src.database.connection import get_db
from src.extraction.swiss_invoice_extractor import SwissInvoiceExtractor
from src.utils.logger import app_logger


class InvoiceService:
    """Service pour la gestion des factures"""
    
    def __init__(self):
        self.db = None
        self.db_extractor = SwissInvoiceExtractor()
    
    def create_invoice_from_extracted_data(self, extracted_data: InvoiceData, filename: str, raw_text: str = None) -> InvoiceDTO:
        """
        Crée une facture DTO à partir des données extraites avec amélioration par base de données
        """
        try:
            app_logger.info("Création du DTO Invoice à partir des données extraites avec BDD")
            
            # Génération d'un ID unique pour la facture
            invoice_id = uuid.uuid4()
            
            # Utilisation de l'extracteur basé sur la BDD si du texte brut est disponible
            db_data = None
            if raw_text:
                db_data = self.db_extractor.extract_invoice_data_with_db(raw_text)
            
            # Extraction des données avec priorité aux données de la BDD
            invoice_number = self._extract_invoice_number_enhanced(extracted_data, db_data)
            invoice_date = self._extract_invoice_date_enhanced(extracted_data, db_data)
            supplier_name = self._extract_supplier_name_enhanced(extracted_data, db_data)
            company_erp_code = self._extract_company_enhanced(extracted_data, db_data)
            currency_code = self._extract_currency_enhanced(extracted_data, db_data)
            
            # Extraction des montants avec priorité aux données de la BDD
            excluding_taxes, vat, including_taxes = self._extract_amounts_enhanced(extracted_data, db_data)
            
            # Détermination du statut
            payment_state = PaymentStatus.DRAFT
            completed = False
            draft = True
            
            # Création des InvoiceGoals si nécessaire
            invoice_goals = self._create_invoice_goals_dto_only_enhanced(invoice_id, extracted_data, including_taxes)
            
            # Construction du DTO de réponse
            invoice_dto = InvoiceDTO(
                id=invoice_id,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                company_erp_code=company_erp_code,
                supplier_name=supplier_name,
                excluding_taxes=excluding_taxes,
                vat=vat,
                including_taxes=including_taxes,
                payment_state=payment_state,
                currency_code=currency_code,
                completed=completed,
                draft=draft,
                state_validations=[],  # Vide pour l'instant
                invoice_goals=invoice_goals,
                document_urls=[filename] if filename else []
            )
            
            app_logger.info(f"DTO Invoice créé avec succès - ID: {invoice_id}")
            return invoice_dto
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la création du DTO Invoice: {str(e)}")
            raise
    
    def _extract_invoice_number(self, data: InvoiceData) -> Optional[str]:
        """Extrait le numéro de facture"""
        if data.invoice and data.invoice.number:
            return data.invoice.number
        return None
    
    def _extract_invoice_date(self, data: InvoiceData) -> Optional[date]:
        """Extrait la date de facture"""
        if data.invoice and data.invoice.date:
            if isinstance(data.invoice.date, str):
                try:
                    return datetime.strptime(data.invoice.date, "%Y-%m-%d").date()
                except ValueError:
                    return None
            return data.invoice.date
        return None
    
    def _find_or_create_company(self, data: InvoiceData) -> Optional[str]:
        """Trouve ou crée une société et retourne son ERP code"""
        try:
            # Recherche d'une société existante
            if data.customer and data.customer.name:
                query = text("""
                    SELECT company_erp_code 
                    FROM company 
                    WHERE LOWER(company_name) LIKE LOWER(:name_pattern)
                    LIMIT 1
                """)
                
                result = self.db.execute(query, {
                    'name_pattern': f'%{data.customer.name[:20]}%'
                }).fetchone()
                
                if result:
                    return result[0]
            
            # Recherche d'une société par défaut existante
            default_query = text("""
                SELECT company_erp_code 
                FROM company 
                LIMIT 1
            """)
            
            default_result = self.db.execute(default_query).fetchone()
            if default_result:
                return default_result[0]
            
            # Si aucune société n'existe, retourner None
            return None
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la recherche de société: {str(e)}")
            return None
    
    def _extract_supplier_name(self, data: InvoiceData) -> Optional[str]:
        """Extrait le nom du fournisseur"""
        if data.supplier and data.supplier.name:
            return data.supplier.name
        return None
    
    def _extract_excluding_taxes(self, data: InvoiceData) -> Optional[Decimal]:
        """Extrait le montant HT"""
        if data.totals and data.totals.subtotal_excl_vat:
            return Decimal(str(data.totals.subtotal_excl_vat))
        return None
    
    def _extract_vat(self, data: InvoiceData) -> Optional[Decimal]:
        """Extrait le montant de TVA"""
        if data.totals and data.totals.total_vat:
            return Decimal(str(data.totals.total_vat))
        return None
    
    def _extract_including_taxes(self, data: InvoiceData) -> Optional[Decimal]:
        """Extrait le montant TTC"""
        if data.totals and data.totals.total_incl_vat:
            return Decimal(str(data.totals.total_incl_vat))
        elif data.totals and data.totals.amount_due:
            return Decimal(str(data.totals.amount_due))
        return None
    
    def _insert_invoice_to_db(self, invoice_id: uuid.UUID, invoice_number: Optional[str],
                             invoice_date: Optional[date], company_erp_code: Optional[str],
                             supplier_name: Optional[str], excluding_taxes: Optional[Decimal],
                             vat: Optional[Decimal], including_taxes: Optional[Decimal],
                             payment_state: str, completed: bool, draft: bool, filename: str):
        """Insère la facture en base de données"""
        try:
            query = text("""
                INSERT INTO invoice (
                    id, invoice_number, invoice_date, company_erp_code, supplier_name,
                    excluding_taxes, vat, including_taxes, payment_state, currency_code,
                    is_complete, is_draft, created_date, created_by
                ) VALUES (
                    :id, :invoice_number, :invoice_date, :company_erp_code, :supplier_name,
                    :excluding_taxes, :vat, :including_taxes, :payment_state, :currency_code,
                    :is_complete, :is_draft, :created_date, :created_by
                )
            """)
            
            self.db.execute(query, {
                'id': str(invoice_id),
                'invoice_number': invoice_number,
                'invoice_date': invoice_date,
                'company_erp_code': company_erp_code,
                'supplier_name': supplier_name,
                'excluding_taxes': float(excluding_taxes) if excluding_taxes else None,
                'vat': float(vat) if vat else None,
                'including_taxes': float(including_taxes) if including_taxes else None,
                'payment_state': payment_state,
                'currency_code': 'EUR',
                'is_complete': completed,
                'is_draft': draft,
                'created_date': datetime.now(),
                'created_by': 'ocr_system'
            })
            
            self.db.commit()
            app_logger.info(f"Facture insérée en base avec l'ID: {invoice_id}")
            
        except Exception as e:
            app_logger.error(f"Erreur lors de l'insertion en base: {str(e)}")
            self.db.rollback()
            raise
    
    def _create_invoice_goals_dto_only(self, invoice_id: uuid.UUID, data: InvoiceData) -> list[InvoiceGoalDTO]:
        """Crée les InvoiceGoals DTO sans sauvegarde en base"""
        invoice_goals = []
        
        try:
            # Création d'un InvoiceGoal par défaut si on a un montant
            if data.totals and data.totals.total_incl_vat:
                goal_id = uuid.uuid4()
                
                # Création du DTO seulement
                invoice_goal_dto = InvoiceGoalDTO(
                    id=goal_id,
                    invoice_id=invoice_id,
                    amount=Decimal(str(data.totals.total_incl_vat))
                )
                
                invoice_goals.append(invoice_goal_dto)
                
        except Exception as e:
            app_logger.error(f"Erreur lors de la création des InvoiceGoals DTO: {str(e)}")
        
        return invoice_goals
    
    def _extract_invoice_number_enhanced(self, data: InvoiceData, db_data: Optional[dict]) -> Optional[str]:
        """Extrait le numéro de facture avec priorité aux données BDD"""
        if db_data and db_data.get('invoice_number'):
            return db_data['invoice_number']
        return self._extract_invoice_number(data)
    
    def _extract_invoice_date_enhanced(self, data: InvoiceData, db_data: Optional[dict]) -> Optional[date]:
        """Extrait la date de facture avec priorité aux données BDD"""
        if db_data and db_data.get('invoice_date'):
            return db_data['invoice_date']
        return self._extract_invoice_date(data)
    
    def _extract_supplier_name_enhanced(self, data: InvoiceData, db_data: Optional[dict]) -> Optional[str]:
        """Extrait le nom du fournisseur avec priorité aux données BDD"""
        if db_data and db_data.get('supplier_name'):
            return db_data['supplier_name']
        return self._extract_supplier_name(data)
    
    def _extract_company_enhanced(self, data: InvoiceData, db_data: Optional[dict]) -> Optional[str]:
        """Extrait le code ERP de la société avec priorité aux données BDD"""
        if db_data and db_data.get('company_erp_code'):
            return db_data['company_erp_code']
        
        # Fallback sur les données extraites
        if data.customer and data.customer.name:
            return data.customer.name
        
        return None
    
    def _extract_currency_enhanced(self, data: InvoiceData, db_data: Optional[dict]) -> str:
        """Extrait le code de devise avec priorité aux données BDD"""
        if db_data and db_data.get('currency_code'):
            return db_data['currency_code']
        
        # Fallback sur les données extraites
        if data.invoice and data.invoice.currency:
            return data.invoice.currency
        
        return "EUR"  # Par défaut
    
    def _extract_amounts_enhanced(self, data: InvoiceData, db_data: Optional[dict]) -> tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """Extrait les montants avec priorité aux données BDD"""
        excluding_taxes = None
        vat = None
        including_taxes = None
        
        # Priorité aux données BDD
        if db_data and db_data.get('amounts'):
            amounts = db_data['amounts']
            excluding_taxes = amounts.get('total_ht')
            vat = amounts.get('tva')
            including_taxes = amounts.get('total_ttc')
        
        # Fallback sur les données extraites si pas trouvé
        if not excluding_taxes:
            excluding_taxes = self._extract_excluding_taxes(data)
        if not vat:
            vat = self._extract_vat(data)
        if not including_taxes:
            including_taxes = self._extract_including_taxes(data)
        
        return excluding_taxes, vat, including_taxes
    
    def _create_invoice_goals_dto_only_enhanced(self, invoice_id: uuid.UUID, data: InvoiceData, including_taxes: Optional[Decimal] = None) -> list[InvoiceGoalDTO]:
        """Crée les InvoiceGoals DTO avec montant amélioré"""
        invoice_goals = []
        
        try:
            # Utilise le montant TTC amélioré ou celui des données extraites
            amount = including_taxes
            if not amount and data.totals and data.totals.total_incl_vat:
                amount = Decimal(str(data.totals.total_incl_vat))
            
            if amount:
                goal_id = uuid.uuid4()
                
                # Création du DTO seulement
                invoice_goal_dto = InvoiceGoalDTO(
                    id=goal_id,
                    invoice_id=invoice_id,
                    amount=amount
                )
                
                invoice_goals.append(invoice_goal_dto)
                
        except Exception as e:
            app_logger.error(f"Erreur lors de la création des InvoiceGoals DTO: {str(e)}")
        
        return invoice_goals

    def __del__(self):
        """Fermeture de la session de base de données"""
        if hasattr(self, 'db') and self.db:
            self.db.close()


def get_invoice_service() -> InvoiceService:
    """Factory pour créer le service Invoice"""
    return InvoiceService()
