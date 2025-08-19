"""
Extracteur de données amélioré avec ML utilisant la base de données locale
"""

import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.api.models import *
from src.database.connection import get_db
from src.extraction.data_extractor import DataExtractor
from src.utils.logger import app_logger
from src.utils.exceptions import DataExtractionError


class MLEnhancedExtractor(DataExtractor):
    """
    Extracteur de données amélioré avec apprentissage automatique
    utilisant les données historiques de la base de données
    """
    
    def __init__(self):
        super().__init__()
        self.db = next(get_db())
    
    def extract_invoice_data_with_ml(self, text: str, structured_data: Dict = None, 
                                   filename: str = None) -> InvoiceData:
        """
        Extrait les données de facture avec amélioration ML
        
        Args:
            text: Texte extrait par OCR
            structured_data: Données structurées avec positions
            filename: Nom du fichier traité
            
        Returns:
            Données de facture améliorées avec ML
        """
        try:
            app_logger.info("Début de l'extraction ML améliorée")
            
            # Extraction de base
            base_data = super().extract_invoice_data(text, structured_data)
            
            # Amélioration avec les données historiques
            enhanced_data = self._enhance_with_historical_data(base_data, text)
            
            # Amélioration avec reconnaissance de patterns
            pattern_enhanced_data = self._enhance_with_pattern_recognition(enhanced_data, text)
            
            # Validation et correction avec ML
            validated_data = self._ml_validate_and_correct(pattern_enhanced_data, text)
            
            # Sauvegarde des données ML pour apprentissage futur
            self._save_ml_training_data(validated_data, text, filename)
            
            app_logger.info("Extraction ML améliorée terminée")
            return validated_data
            
        except Exception as e:
            app_logger.error(f"Erreur lors de l'extraction ML: {str(e)}")
            # Fallback vers l'extraction de base
            return super().extract_invoice_data(text, structured_data)
    
    def _enhance_with_historical_data(self, base_data: InvoiceData, text: str) -> InvoiceData:
        """
        Améliore les données avec l'historique de la base de données
        """
        try:
            # Recherche de fournisseurs similaires
            if base_data.supplier and base_data.supplier.name:
                similar_supplier = self._find_similar_supplier(base_data.supplier.name)
                if similar_supplier:
                    app_logger.info(f"Fournisseur similaire trouvé: {similar_supplier['social_reason']}")
                    # Améliorer les données du fournisseur
                    base_data.supplier.name = similar_supplier['social_reason']
                    if not base_data.supplier.rcs and similar_supplier['rcs']:
                        base_data.supplier.rcs = similar_supplier['rcs']
                    if not base_data.supplier.address and similar_supplier['address']:
                        base_data.supplier.address = similar_supplier['address']
            
            # Recherche de sociétés similaires
            if base_data.customer and base_data.customer.name:
                similar_company = self._find_similar_company(base_data.customer.name)
                if similar_company:
                    app_logger.info(f"Société similaire trouvée: {similar_company['company_name']}")
                    base_data.customer.name = similar_company['company_name']
                    if not base_data.customer.address and similar_company['company_address']:
                        base_data.customer.address = {'street': similar_company['company_address']}
            
            # Amélioration des montants avec patterns historiques
            if base_data.totals:
                base_data.totals = self._enhance_amounts_with_history(base_data.totals, text)
            
            return base_data
            
        except Exception as e:
            app_logger.error(f"Erreur lors de l'amélioration historique: {str(e)}")
            return base_data
    
    def _find_similar_supplier(self, supplier_name: str) -> Optional[Dict]:
        """
        Trouve un fournisseur similaire dans la base de données
        """
        try:
            # Recherche par similarité de nom
            query = text("""
                SELECT social_reason, rcs, address, email, phone_number
                FROM supplier 
                WHERE is_active = true 
                AND (
                    LOWER(social_reason) LIKE LOWER(:name_pattern)
                    OR similarity(social_reason, :supplier_name) > 0.3
                )
                ORDER BY similarity(social_reason, :supplier_name) DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query, {
                'name_pattern': f'%{supplier_name[:10]}%',
                'supplier_name': supplier_name
            }).fetchone()
            
            if result:
                return dict(result._mapping)
            return None
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la recherche de fournisseur: {str(e)}")
            return None
    
    def _find_similar_company(self, company_name: str) -> Optional[Dict]:
        """
        Trouve une société similaire dans la base de données
        """
        try:
            query = text("""
                SELECT company_name, company_address, company_erp_code, company_rcs
                FROM company 
                WHERE (
                    LOWER(company_name) LIKE LOWER(:name_pattern)
                    OR similarity(company_name, :company_name) > 0.3
                )
                ORDER BY similarity(company_name, :company_name) DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query, {
                'name_pattern': f'%{company_name[:10]}%',
                'company_name': company_name
            }).fetchone()
            
            if result:
                return dict(result._mapping)
            return None
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la recherche de société: {str(e)}")
            return None
    
    def _enhance_amounts_with_history(self, totals: Totals, text: str) -> Totals:
        """
        Améliore les montants avec les patterns historiques
        """
        try:
            # Recherche de patterns de montants dans l'historique
            query = text("""
                SELECT excluding_taxes, vat, including_taxes
                FROM invoice 
                WHERE including_taxes IS NOT NULL
                ORDER BY created_date DESC
                LIMIT 100
            """)
            
            historical_invoices = self.db.execute(query).fetchall()
            
            # Analyse des patterns de TVA
            if historical_invoices:
                vat_rates = []
                for invoice in historical_invoices:
                    if invoice.excluding_taxes and invoice.vat and invoice.excluding_taxes > 0:
                        rate = float(invoice.vat) / float(invoice.excluding_taxes)
                        if 0.15 <= rate <= 0.25:  # TVA raisonnable
                            vat_rates.append(rate)
                
                if vat_rates:
                    avg_vat_rate = sum(vat_rates) / len(vat_rates)
                    app_logger.info(f"Taux de TVA moyen historique: {avg_vat_rate:.2%}")
                    
                    # Correction des montants si incohérents
                    if totals.subtotal_excl_vat and not totals.total_vat:
                        totals.total_vat = totals.subtotal_excl_vat * avg_vat_rate
                    
                    if totals.subtotal_excl_vat and totals.total_vat and not totals.total_incl_vat:
                        totals.total_incl_vat = totals.subtotal_excl_vat + totals.total_vat
            
            return totals
            
        except Exception as e:
            app_logger.error(f"Erreur lors de l'amélioration des montants: {str(e)}")
            return totals
    
    def _enhance_with_pattern_recognition(self, data: InvoiceData, text: str) -> InvoiceData:
        """
        Améliore les données avec reconnaissance de patterns avancée
        """
        try:
            # Amélioration du numéro de facture avec patterns ML
            if not data.invoice or not data.invoice.number:
                enhanced_number = self._extract_invoice_number_ml(text)
                if enhanced_number:
                    if not data.invoice:
                        data.invoice = Invoice(number=enhanced_number, currency="EUR")
                    else:
                        data.invoice.number = enhanced_number
            
            # Amélioration des dates avec patterns ML
            dates = self._extract_dates_ml(text)
            if dates and data.invoice:
                if not data.invoice.date and dates.get('invoice_date'):
                    data.invoice.date = dates['invoice_date']
                if not data.invoice.due_date and dates.get('due_date'):
                    data.invoice.due_date = dates['due_date']
            
            # Amélioration des montants avec patterns ML
            if data.totals:
                enhanced_totals = self._extract_amounts_ml(text)
                if enhanced_totals:
                    if not data.totals.total_incl_vat and enhanced_totals.get('total_ttc'):
                        data.totals.total_incl_vat = enhanced_totals['total_ttc']
                    if not data.totals.subtotal_excl_vat and enhanced_totals.get('total_ht'):
                        data.totals.subtotal_excl_vat = enhanced_totals['total_ht']
                    if not data.totals.total_vat and enhanced_totals.get('total_tva'):
                        data.totals.total_vat = enhanced_totals['total_tva']
            
            return data
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la reconnaissance de patterns: {str(e)}")
            return data
    
    def _extract_invoice_number_ml(self, text: str) -> Optional[str]:
        """
        Extraction améliorée du numéro de facture avec ML
        """
        # Patterns avancés pour numéros de facture
        patterns = [
            r'(?:FACTURE|INVOICE|N°|Réf\.?)\s*:?\s*([A-Z0-9\-/]{3,20})',
            r'([A-Z]{2,4}[\-\s]*\d{4,})',
            r'(\d{4,}[\-/]\d{2,})',
            r'([A-Z]+\d{6,})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) >= 3 and not match.isdigit():
                    return match.strip()
        
        return None
    
    def _extract_dates_ml(self, text: str) -> Dict[str, Optional[date]]:
        """
        Extraction améliorée des dates avec ML
        """
        dates = {}
        
        # Patterns pour dates
        date_patterns = [
            r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            r'(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})',
        ]
        
        found_dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                parsed_date = self._parse_date(match)
                if parsed_date:
                    found_dates.append(parsed_date)
        
        # Logique pour assigner les dates
        if found_dates:
            # La première date est souvent la date de facture
            dates['invoice_date'] = found_dates[0]
            # S'il y a plusieurs dates, la dernière peut être l'échéance
            if len(found_dates) > 1:
                dates['due_date'] = found_dates[-1]
        
        return dates
    
    def _extract_amounts_ml(self, text: str) -> Dict[str, Optional[float]]:
        """
        Extraction améliorée des montants avec ML
        """
        amounts = {}
        
        # Patterns pour montants avec contexte
        amount_patterns = [
            (r'(?:TOTAL\s+TTC|Total\s+TTC)[\s:]*(\d+(?:[,\.]\d{2})?)', 'total_ttc'),
            (r'(?:TOTAL\s+HT|Total\s+HT)[\s:]*(\d+(?:[,\.]\d{2})?)', 'total_ht'),
            (r'(?:TVA|T\.V\.A)[\s:]*(\d+(?:[,\.]\d{2})?)', 'total_tva'),
            (r'(?:À\s+PAYER|MONTANT\s+DÛ)[\s:]*(\d+(?:[,\.]\d{2})?)', 'amount_due'),
        ]
        
        for pattern, amount_type in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    amount_str = matches[0].replace(',', '.')
                    amounts[amount_type] = float(amount_str)
                except ValueError:
                    continue
        
        return amounts
    
    def _ml_validate_and_correct(self, data: InvoiceData, text: str) -> InvoiceData:
        """
        Validation et correction avec ML
        """
        try:
            # Validation de cohérence des montants
            if data.totals:
                data.totals = self._validate_amounts_consistency(data.totals)
            
            # Validation des données obligatoires
            data.validation = self._calculate_ml_validation_score(data, text)
            
            return data
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la validation ML: {str(e)}")
            return data
    
    def _validate_amounts_consistency(self, totals: Totals) -> Totals:
        """
        Valide et corrige la cohérence des montants
        """
        if totals.subtotal_excl_vat and totals.total_vat and totals.total_incl_vat:
            calculated_total = totals.subtotal_excl_vat + totals.total_vat
            if abs(calculated_total - totals.total_incl_vat) > 0.01:
                app_logger.warning("Incohérence détectée dans les montants, correction automatique")
                totals.total_incl_vat = calculated_total
        
        return totals
    
    def _calculate_ml_validation_score(self, data: InvoiceData, text: str) -> Validation:
        """
        Calcule un score de validation ML avancé
        """
        validation = Validation()
        score = 0.0
        total_checks = 0
        
        # Vérifications avancées
        checks = [
            (data.invoice and data.invoice.number, "Numéro de facture"),
            (data.totals and data.totals.total_incl_vat, "Montant TTC"),
            (data.supplier and data.supplier.name, "Nom fournisseur"),
            (data.invoice and data.invoice.date, "Date facture"),
        ]
        
        for check, description in checks:
            total_checks += 1
            if check:
                score += 1
                app_logger.debug(f"✓ {description}")
            else:
                app_logger.debug(f"✗ {description}")
        
        validation.required_fields_present = score >= 2
        validation.data_quality_score = score / total_checks if total_checks > 0 else 0.0
        
        # Validation des calculs
        if data.totals:
            validation.calculation_check = self._check_calculation_consistency(data.totals)
        
        return validation
    
    def _check_calculation_consistency(self, totals: Totals) -> bool:
        """
        Vérifie la cohérence des calculs
        """
        if totals.subtotal_excl_vat and totals.total_vat and totals.total_incl_vat:
            calculated = totals.subtotal_excl_vat + totals.total_vat
            return abs(calculated - totals.total_incl_vat) <= 0.01
        return False
    
    def _save_ml_training_data(self, data: InvoiceData, raw_text: str, filename: str):
        """
        Sauvegarde les données pour l'apprentissage ML futur
        """
        try:
            # Sauvegarder dans invoice_ml_data pour apprentissage futur
            ml_data = {
                'extracted_data': data.dict(),
                'confidence_score': data.metadata.confidence_score,
                'processing_time': data.metadata.processing_time,
                'validation_score': data.validation.data_quality_score if data.validation else 0.0,
                'filename': filename
            }
            
            query = text("""
                INSERT INTO invoice_ml_data (raw_text, extracted_data, confidence_score, 
                                           processing_time, validation_score, data_quality_score)
                VALUES (:raw_text, :extracted_data, :confidence_score, :processing_time, 
                        :validation_score, :data_quality_score)
            """)
            
            self.db.execute(query, {
                'raw_text': raw_text[:10000],  # Limiter la taille
                'extracted_data': json.dumps(ml_data, default=str),
                'confidence_score': data.metadata.confidence_score,
                'processing_time': data.metadata.processing_time,
                'validation_score': data.validation.data_quality_score if data.validation else 0.0,
                'data_quality_score': data.validation.data_quality_score if data.validation else 0.0
            })
            
            self.db.commit()
            app_logger.info("Données ML sauvegardées pour apprentissage futur")
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la sauvegarde ML: {str(e)}")
            self.db.rollback()
    
    def __del__(self):
        """Fermeture de la session de base de données"""
        if hasattr(self, 'db'):
            self.db.close()
