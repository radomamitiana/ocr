"""
Module d'extraction de données intelligente utilisant des patterns et LLM
"""

import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass
from src.api.models import *
from src.utils.logger import app_logger
from src.utils.exceptions import DataExtractionError


@dataclass
class ExtractionPattern:
    """Pattern d'extraction avec regex et contexte"""
    name: str
    pattern: str
    context_keywords: List[str]
    confidence_boost: float = 0.1


class DataExtractor:
    """Extracteur de données intelligent pour factures"""
    
    def __init__(self):
        self.patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, List[ExtractionPattern]]:
        """Initialise les patterns d'extraction"""
        return {
            'invoice_number': [
                ExtractionPattern(
                    'facture_num', 
                    r'(?:facture|invoice|n°|num|number)[\s:]*([A-Z0-9\-/]+)',
                    ['facture', 'invoice', 'numéro']
                ),
                ExtractionPattern(
                    'facture_simple',
                    r'F[A-Z]*[\-\s]*(\d{4,})',
                    ['facture']
                )
            ],
            'date': [
                ExtractionPattern(
                    'date_fr',
                    r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
                    ['date', 'émission', 'facture']
                ),
                ExtractionPattern(
                    'date_iso',
                    r'(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})',
                    ['date']
                )
            ],
            'amount': [
                ExtractionPattern(
                    'montant_euro',
                    r'(\d+[,\.\s]\d{2})\s*€',
                    ['total', 'montant', 'ttc', 'ht']
                ),
                ExtractionPattern(
                    'montant_decimal',
                    r'(\d+[,\.]\d{2})',
                    ['total', 'montant']
                )
            ],
            'siret': [
                ExtractionPattern(
                    'siret_pattern',
                    r'(?:siret|siren)[\s:]*(\d{9,14})',
                    ['siret', 'siren']
                )
            ],
            'vat_number': [
                ExtractionPattern(
                    'tva_fr',
                    r'(?:tva|vat)[\s:]*([A-Z]{2}\d{11})',
                    ['tva', 'intracommunautaire']
                )
            ]
        }
    
    def extract_invoice_data(self, text: str, structured_data: Dict = None) -> InvoiceData:
        """
        Extrait les données de facture du texte OCR
        
        Args:
            text: Texte extrait par OCR
            structured_data: Données structurées avec positions (optionnel)
            
        Returns:
            Données de facture structurées
        """
        try:
            app_logger.info("Début de l'extraction de données")
            
            # Nettoyage du texte
            cleaned_text = self._clean_text(text)
            
            # Extraction des différents champs
            supplier_data = self._extract_supplier_info(cleaned_text)
            customer_data = self._extract_customer_info(cleaned_text)
            invoice_info = self._extract_invoice_info(cleaned_text)
            line_items = self._extract_line_items(cleaned_text)
            totals = self._extract_totals(cleaned_text)
            
            # Création des objets
            supplier = Supplier(**supplier_data) if supplier_data else None
            customer = Customer(**customer_data) if customer_data else None
            invoice = Invoice(**invoice_info) if invoice_info else None
            
            # Métadonnées
            metadata = Metadata(
                filename="processed_invoice",
                confidence_score=self._calculate_confidence(cleaned_text),
                processing_time=0.0
            )
            
            # Validation
            validation = self._validate_data(totals, line_items)
            
            result = InvoiceData(
                metadata=metadata,
                supplier=supplier,
                customer=customer,
                invoice=invoice,
                line_items=line_items,
                totals=totals,
                validation=validation
            )
            
            app_logger.info("Extraction de données terminée")
            return result
            
        except Exception as e:
            app_logger.error(f"Erreur lors de l'extraction: {str(e)}")
            raise DataExtractionError(f"Échec de l'extraction de données: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Nettoie et normalise le texte"""
        # Suppression des caractères indésirables
        cleaned = re.sub(r'[^\w\s\-.,;:()€$%@#&/\\]', ' ', text)
        # Normalisation des espaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()
    
    def _extract_supplier_info(self, text: str) -> Dict[str, Any]:
        """Extrait les informations du fournisseur"""
        supplier_info = {}
        
        # Extraction du nom (généralement en haut du document)
        lines = text.split('\n')[:10]  # Premières lignes
        for line in lines:
            if len(line.strip()) > 3 and not re.search(r'\d{2}[/\-\.]\d{2}', line):
                supplier_info['name'] = line.strip()
                break
        
        # Extraction SIRET
        siret_match = self._extract_with_patterns(text, 'siret')
        if siret_match:
            supplier_info['siret'] = siret_match
        
        # Extraction numéro TVA
        vat_match = self._extract_with_patterns(text, 'vat_number')
        if vat_match:
            supplier_info['vat_number'] = vat_match
        
        return supplier_info
    
    def _extract_customer_info(self, text: str) -> Dict[str, Any]:
        """Extrait les informations du client"""
        customer_info = {}
        
        # Recherche de sections client
        client_patterns = [
            r'(?:client|customer|facturé à)[\s:]*([^\n]+)',
            r'(?:destinataire)[\s:]*([^\n]+)'
        ]
        
        for pattern in client_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                customer_info['name'] = match.group(1).strip()
                break
        
        return customer_info
    
    def _extract_invoice_info(self, text: str) -> Dict[str, Any]:
        """Extrait les informations de la facture"""
        invoice_info = {}
        
        # Numéro de facture
        invoice_num = self._extract_with_patterns(text, 'invoice_number')
        if invoice_num:
            invoice_info['number'] = invoice_num
        
        # Date de facture
        date_match = self._extract_with_patterns(text, 'date')
        if date_match:
            parsed_date = self._parse_date(date_match)
            if parsed_date:
                invoice_info['date'] = parsed_date
        
        # Devise (par défaut EUR)
        if '€' in text:
            invoice_info['currency'] = 'EUR'
        elif '$' in text:
            invoice_info['currency'] = 'USD'
        else:
            invoice_info['currency'] = 'EUR'
        
        return invoice_info
    
    def _extract_line_items(self, text: str) -> List[LineItem]:
        """Extrait les lignes de produits/services"""
        line_items = []
        
        # Pattern pour détecter les lignes de produits
        # Recherche de lignes avec quantité, prix unitaire, montant
        item_pattern = r'([^\d\n]+)\s+(\d+(?:[,\.]\d+)?)\s+(\d+(?:[,\.]\d{2})?)\s+(\d+(?:[,\.]\d{2})?)'
        
        matches = re.findall(item_pattern, text)
        
        for match in matches:
            try:
                description = match[0].strip()
                quantity = float(match[1].replace(',', '.'))
                unit_price = float(match[2].replace(',', '.'))
                amount = float(match[3].replace(',', '.'))
                
                line_item = LineItem(
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    amount_excl_vat=amount,
                    vat_rate=0.20,  # TVA par défaut 20%
                    vat_amount=amount * 0.20,
                    amount_incl_vat=amount * 1.20
                )
                
                line_items.append(line_item)
                
            except (ValueError, IndexError):
                continue
        
        return line_items
    
    def _extract_totals(self, text: str) -> Optional[Totals]:
        """Extrait les totaux de la facture"""
        totals_info = {}
        
        # Recherche des montants totaux
        total_patterns = [
            (r'(?:total\s+ht|sous.total)[\s:]*(\d+[,\.]\d{2})', 'subtotal_excl_vat'),
            (r'(?:total\s+tva|tva)[\s:]*(\d+[,\.]\d{2})', 'total_vat'),
            (r'(?:total\s+ttc|total)[\s:]*(\d+[,\.]\d{2})', 'total_incl_vat'),
            (r'(?:à\s+payer|net\s+à\s+payer)[\s:]*(\d+[,\.]\d{2})', 'amount_due')
        ]
        
        for pattern, field in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount = float(match.group(1).replace(',', '.'))
                    totals_info[field] = amount
                except ValueError:
                    continue
        
        return Totals(**totals_info) if totals_info else None
    
    def _extract_with_patterns(self, text: str, field_type: str) -> Optional[str]:
        """Extrait un champ en utilisant les patterns définis"""
        if field_type not in self.patterns:
            return None
        
        for pattern in self.patterns[field_type]:
            match = re.search(pattern.pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse une chaîne de date en objet date"""
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
            '%d/%m/%y', '%d-%m-%y', '%d.%m.%y',
            '%Y/%m/%d', '%Y-%m-%d', '%Y.%m.%d'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _calculate_confidence(self, text: str) -> float:
        """Calcule un score de confiance basé sur la présence de mots-clés"""
        keywords = [
            'facture', 'invoice', 'total', 'tva', 'ht', 'ttc',
            'siret', 'date', 'montant', 'quantité'
        ]
        
        found_keywords = sum(1 for keyword in keywords if keyword.lower() in text.lower())
        confidence = min(found_keywords / len(keywords), 1.0)
        
        return confidence
    
    def _validate_data(self, totals: Optional[Totals], line_items: List[LineItem]) -> Validation:
        """Valide la cohérence des données extraites"""
        validation = Validation()
        
        # Vérification des calculs
        if totals and line_items:
            calculated_subtotal = sum(item.amount_excl_vat or 0 for item in line_items)
            if totals.subtotal_excl_vat and abs(calculated_subtotal - totals.subtotal_excl_vat) < 0.01:
                validation.calculation_check = True
        
        # Vérification des champs requis
        required_fields_present = bool(totals and (totals.total_incl_vat or totals.amount_due))
        validation.required_fields_present = required_fields_present
        
        # Score de qualité des données
        quality_score = 0.0
        if totals:
            quality_score += 0.4
        if line_items:
            quality_score += 0.3
        if validation.calculation_check:
            quality_score += 0.3
        
        validation.data_quality_score = quality_score
        
        return validation
