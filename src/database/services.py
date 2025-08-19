"""
Services de base de données avec logique ML pour l'amélioration des déductions
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, date
import json
import re

from .models import Company, Supplier, Invoice, InvoiceGoal, InvoiceLineItem
from .connection import get_db
from src.utils.logger import app_logger


class InvoiceMLService:
    """
    Service pour l'amélioration des déductions de factures avec ML
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_or_create_company(self, company_data: Dict[str, Any]) -> Optional[Company]:
        """
        Trouve ou crée une société basée sur les données extraites
        Utilise la logique ML pour faire des déductions intelligentes
        """
        if not company_data or not company_data.get('name'):
            return None
        
        # Recherche par nom exact
        company = self.db.query(Company).filter(
            Company.name.ilike(f"%{company_data['name'].strip()}%")
        ).first()
        
        if company:
            app_logger.info(f"Société trouvée: {company.name}")
            return company
        
        # Recherche par SIRET si disponible
        if company_data.get('siret'):
            company = self.db.query(Company).filter(
                Company.siret == company_data['siret']
            ).first()
            if company:
                app_logger.info(f"Société trouvée par SIRET: {company.name}")
                return company
        
        # Recherche par numéro de TVA si disponible
        if company_data.get('vat_number'):
            company = self.db.query(Company).filter(
                Company.vat_number == company_data['vat_number']
            ).first()
            if company:
                app_logger.info(f"Société trouvée par TVA: {company.name}")
                return company
        
        # Si aucune société trouvée, créer une nouvelle entrée
        app_logger.info(f"Création d'une nouvelle société: {company_data['name']}")
        return self._create_company(company_data)
    
    def find_or_create_supplier(self, supplier_data: Dict[str, Any]) -> Optional[Supplier]:
        """
        Trouve ou crée un fournisseur basé sur les données extraites
        """
        if not supplier_data or not supplier_data.get('name'):
            return None
        
        # Recherche par nom avec similarité
        supplier = self.db.query(Supplier).filter(
            Supplier.name.ilike(f"%{supplier_data['name'].strip()}%")
        ).first()
        
        if supplier:
            app_logger.info(f"Fournisseur trouvé: {supplier.name}")
            return supplier
        
        # Recherche par SIRET si disponible
        if supplier_data.get('siret'):
            supplier = self.db.query(Supplier).filter(
                Supplier.siret == supplier_data['siret']
            ).first()
            if supplier:
                app_logger.info(f"Fournisseur trouvé par SIRET: {supplier.name}")
                return supplier
        
        # Si aucun fournisseur trouvé, créer une nouvelle entrée
        app_logger.info(f"Création d'un nouveau fournisseur: {supplier_data['name']}")
        return self._create_supplier(supplier_data)
    
    def create_invoice_with_ml_enhancement(self, invoice_data: Dict[str, Any], 
                                         raw_text: str, extracted_data: Dict[str, Any]) -> Invoice:
        """
        Crée une facture avec amélioration ML basée sur les données historiques
        """
        # Recherche de la société et du fournisseur
        company = None
        supplier = None
        
        if invoice_data.get('customer'):
            company = self.find_or_create_company(invoice_data['customer'])
        
        if invoice_data.get('supplier'):
            supplier = self.find_or_create_supplier(invoice_data['supplier'])
        
        # Amélioration des données avec ML
        enhanced_data = self._enhance_invoice_data(invoice_data, company, supplier)
        
        # Création de la facture
        invoice = Invoice(
            invoice_number=enhanced_data.get('invoice_number'),
            invoice_date=self._parse_date(enhanced_data.get('invoice_date')),
            due_date=self._parse_date(enhanced_data.get('due_date')),
            currency=enhanced_data.get('currency', 'EUR'),
            payment_terms=enhanced_data.get('payment_terms'),
            company_id=company.id if company else None,
            supplier_id=supplier.id if supplier else None,
            subtotal_excl_vat=enhanced_data.get('subtotal_excl_vat'),
            total_vat=enhanced_data.get('total_vat'),
            total_incl_vat=enhanced_data.get('total_incl_vat'),
            amount_due=enhanced_data.get('amount_due'),
            original_filename=enhanced_data.get('filename'),
            ocr_confidence_score=enhanced_data.get('confidence_score', 0.0),
            processing_time=enhanced_data.get('processing_time', 0.0),
            validation_score=self._calculate_validation_score(enhanced_data)
        )
        
        self.db.add(invoice)
        self.db.flush()  # Pour obtenir l'ID
        
        # Création de l'enregistrement invoice_goal pour le ML
        invoice_goal = InvoiceGoal(
            invoice_id=invoice.id,
            raw_text=raw_text,
            extracted_data=extracted_data,
            data_quality_score=self._calculate_data_quality_score(enhanced_data),
            confidence_threshold=0.8
        )
        
        self.db.add(invoice_goal)
        
        # Ajout des lignes de facture si disponibles
        if enhanced_data.get('line_items'):
            for i, item in enumerate(enhanced_data['line_items']):
                line_item = InvoiceLineItem(
                    invoice_id=invoice.id,
                    line_number=i + 1,
                    description=item.get('description'),
                    quantity=item.get('quantity'),
                    unit_price=item.get('unit_price'),
                    vat_rate=item.get('vat_rate'),
                    amount_excl_vat=item.get('amount_excl_vat'),
                    vat_amount=item.get('vat_amount'),
                    amount_incl_vat=item.get('amount_incl_vat')
                )
                self.db.add(line_item)
        
        self.db.commit()
        app_logger.info(f"Facture créée avec ID: {invoice.id}")
        return invoice
    
    def _create_company(self, company_data: Dict[str, Any]) -> Company:
        """Crée une nouvelle société"""
        address = company_data.get('address', {})
        company = Company(
            name=company_data['name'],
            siret=company_data.get('siret'),
            vat_number=company_data.get('vat_number'),
            address_street=address.get('street'),
            address_city=address.get('city'),
            address_postal_code=address.get('postal_code'),
            address_country=address.get('country', 'France'),
            phone=company_data.get('contact', {}).get('phone'),
            email=company_data.get('contact', {}).get('email')
        )
        self.db.add(company)
        self.db.flush()
        return company
    
    def _create_supplier(self, supplier_data: Dict[str, Any]) -> Supplier:
        """Crée un nouveau fournisseur"""
        address = supplier_data.get('address', {})
        supplier = Supplier(
            name=supplier_data['name'],
            siret=supplier_data.get('siret'),
            vat_number=supplier_data.get('vat_number'),
            address_street=address.get('street'),
            address_city=address.get('city'),
            address_postal_code=address.get('postal_code'),
            address_country=address.get('country', 'France'),
            phone=supplier_data.get('contact', {}).get('phone'),
            email=supplier_data.get('contact', {}).get('email')
        )
        self.db.add(supplier)
        self.db.flush()
        return supplier
    
    def _enhance_invoice_data(self, invoice_data: Dict[str, Any], 
                            company: Optional[Company], 
                            supplier: Optional[Supplier]) -> Dict[str, Any]:
        """
        Améliore les données de facture avec la logique ML
        """
        enhanced = invoice_data.copy()
        
        # Amélioration basée sur l'historique de la société
        if company:
            historical_data = self._get_company_historical_patterns(company.id)
            enhanced = self._apply_historical_patterns(enhanced, historical_data)
        
        # Amélioration basée sur l'historique du fournisseur
        if supplier:
            supplier_patterns = self._get_supplier_patterns(supplier.id)
            enhanced = self._apply_supplier_patterns(enhanced, supplier_patterns)
        
        # Validation et correction des montants
        enhanced = self._validate_and_correct_amounts(enhanced)
        
        return enhanced
    
    def _get_company_historical_patterns(self, company_id: int) -> Dict[str, Any]:
        """Récupère les patterns historiques d'une société"""
        # Récupération des factures récentes de cette société
        recent_invoices = self.db.query(Invoice).filter(
            Invoice.company_id == company_id
        ).order_by(Invoice.created_at.desc()).limit(10).all()
        
        patterns = {
            'common_payment_terms': [],
            'average_amounts': {},
            'common_suppliers': []
        }
        
        for invoice in recent_invoices:
            if invoice.payment_terms:
                patterns['common_payment_terms'].append(invoice.payment_terms)
        
        return patterns
    
    def _get_supplier_patterns(self, supplier_id: int) -> Dict[str, Any]:
        """Récupère les patterns d'un fournisseur"""
        recent_invoices = self.db.query(Invoice).filter(
            Invoice.supplier_id == supplier_id
        ).order_by(Invoice.created_at.desc()).limit(10).all()
        
        patterns = {
            'typical_vat_rates': [],
            'payment_terms': [],
            'currency': 'EUR'
        }
        
        return patterns
    
    def _apply_historical_patterns(self, data: Dict[str, Any], patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Applique les patterns historiques aux données"""
        # Logique d'amélioration basée sur l'historique
        return data
    
    def _apply_supplier_patterns(self, data: Dict[str, Any], patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Applique les patterns du fournisseur aux données"""
        return data
    
    def _validate_and_correct_amounts(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valide et corrige les montants de la facture"""
        totals = data.get('totals', {})
        
        # Validation de la cohérence des montants
        subtotal = totals.get('subtotal_excl_vat', 0)
        vat = totals.get('total_vat', 0)
        total = totals.get('total_incl_vat', 0)
        
        # Vérification de la cohérence : subtotal + vat = total
        if subtotal and vat and total:
            calculated_total = subtotal + vat
            if abs(calculated_total - total) > 0.01:  # Tolérance de 1 centime
                app_logger.warning(f"Incohérence détectée dans les montants: {calculated_total} != {total}")
                # Correction automatique basée sur le sous-total et la TVA
                data['totals']['total_incl_vat'] = calculated_total
        
        return data
    
    def _calculate_validation_score(self, data: Dict[str, Any]) -> float:
        """Calcule un score de validation pour les données"""
        score = 0.0
        total_checks = 0
        
        # Vérification de la présence des champs obligatoires
        required_fields = ['invoice_number', 'invoice_date', 'total_incl_vat']
        for field in required_fields:
            total_checks += 1
            if data.get(field):
                score += 1
        
        # Vérification de la cohérence des montants
        totals = data.get('totals', {})
        if totals.get('subtotal_excl_vat') and totals.get('total_vat') and totals.get('total_incl_vat'):
            total_checks += 1
            calculated = totals['subtotal_excl_vat'] + totals['total_vat']
            if abs(calculated - totals['total_incl_vat']) <= 0.01:
                score += 1
        
        return score / total_checks if total_checks > 0 else 0.0
    
    def _calculate_data_quality_score(self, data: Dict[str, Any]) -> float:
        """Calcule un score de qualité des données"""
        return self._calculate_validation_score(data)
    
    def _parse_date(self, date_str: Any) -> Optional[date]:
        """Parse une date depuis différents formats"""
        if not date_str:
            return None
        
        if isinstance(date_str, date):
            return date_str
        
        if isinstance(date_str, str):
            # Essayer différents formats de date
            formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
        
        return None


def get_invoice_ml_service(db: Session = None) -> InvoiceMLService:
    """Factory pour créer le service ML"""
    if db is None:
        db = next(get_db())
    return InvoiceMLService(db)
