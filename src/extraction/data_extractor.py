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
        """Extrait les informations du fournisseur (émetteur de la facture)"""
        supplier_info = {}
        
        # Le fournisseur est généralement en haut du document, avant les mots-clés client
        lines = text.split('\n')
        supplier_section = []
        
        # Chercher la section fournisseur (avant "FACTURER À", "CLIENT", etc.)
        for i, line in enumerate(lines):
            line_clean = line.strip().upper()
            if any(keyword in line_clean for keyword in ['FACTURER', 'CLIENT', 'DESTINATAIRE', 'FACTURE']):
                break
            if line.strip() and len(line.strip()) > 2:
                supplier_section.append(line.strip())
        
        # Extraire le nom du fournisseur (première ligne significative)
        if supplier_section:
            # Chercher une ligne qui ressemble à un nom d'entreprise
            for line in supplier_section[:5]:  # Premières lignes
                if (len(line) > 3 and 
                    not re.search(r'\d{2}[/\-\.]\d{2}', line) and  # Pas une date
                    not re.search(r'^\d+$', line) and  # Pas juste un numéro
                    not '@' in line):  # Pas un email
                    supplier_info['name'] = line
                    break
        
        # Extraction SIRET
        siret_match = self._extract_with_patterns(text, 'siret')
        if siret_match:
            supplier_info['siret'] = siret_match
        
        # Extraction numéro TVA
        vat_match = self._extract_with_patterns(text, 'vat_number')
        if vat_match:
            supplier_info['vat_number'] = vat_match
        
        # Extraction adresse et contact
        address_info = self._extract_address_from_section(supplier_section)
        if address_info:
            supplier_info['address'] = address_info
        
        contact_info = self._extract_contact_from_section(supplier_section)
        if contact_info:
            supplier_info['contact'] = contact_info
        
        return supplier_info
    
    def _extract_customer_info(self, text: str) -> Dict[str, Any]:
        """Extrait les informations du client (destinataire de la facture)"""
        customer_info = {}
        
        # Chercher la section client après les mots-clés "FACTURER À", "CLIENT", etc.
        lines = text.split('\n')
        customer_section = []
        in_customer_section = False
        
        for line in lines:
            line_clean = line.strip().upper()
            
            # Détecter le début de la section client
            if any(keyword in line_clean for keyword in ['FACTURER À', 'FACTURER A', 'CLIENT', 'DESTINATAIRE']):
                in_customer_section = True
                continue
            
            # Arrêter à la section suivante
            if in_customer_section and any(keyword in line_clean for keyword in ['DESCRIPTION', 'PRESTATION', 'TOTAL', 'MONTANT']):
                break
            
            # Collecter les lignes de la section client
            if in_customer_section and line.strip():
                customer_section.append(line.strip())
        
        # Extraire le nom du client (première ligne significative)
        if customer_section:
            # Chercher une ligne qui ressemble à un nom d'entreprise
            for line in customer_section[:3]:  # Premières lignes
                if (len(line) > 3 and 
                    not re.search(r'\d{2}[/\-\.]\d{2}', line) and  # Pas une date
                    not line.upper().startswith('CONTACT') and  # Pas la ligne contact
                    not line.upper().startswith('R.C.S')):  # Pas le RCS
                    customer_info['name'] = line
                    break
        
        # Extraction adresse du client
        address_info = self._extract_address_from_section(customer_section)
        if address_info:
            customer_info['address'] = address_info
        
        # Extraction ID client (RCS, etc.)
        for line in customer_section:
            if 'R.C.S' in line.upper():
                # Extraire le numéro RCS
                rcs_match = re.search(r'R\.C\.S[^0-9]*(\d+(?:\s+\d+)*)', line, re.IGNORECASE)
                if rcs_match:
                    customer_info['customer_id'] = rcs_match.group(1).replace(' ', '')
                break
        
        return customer_info
    
    def _extract_invoice_info(self, text: str) -> Dict[str, Any]:
        """Extrait les informations de la facture"""
        invoice_info = {}
        
        # Numéro de facture - patterns améliorés
        invoice_patterns = [
            r'(?:N°\s*FACTURE|FACTURE\s*N°|INVOICE\s*NUMBER)[\s:]*([A-Z0-9\-/]+)',
            r'FAC[\-\s]*([A-Z0-9\-/]+)',
            r'(?:N°|Réf\s*N°)[\s:]*([A-Z0-9\-/]+)'
        ]
        
        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_info['number'] = match.group(1).strip()
                break
        
        # Date de facture - temporairement désactivée à cause du problème Pydantic
        # date_patterns = [
        #     r'(?:DATE|Date)[\s:]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        #     r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})'
        # ]
        # 
        # for pattern in date_patterns:
        #     match = re.search(pattern, text)
        #     if match:
        #         parsed_date = self._parse_date(match.group(1))
        #         if parsed_date:
        #             invoice_info['date'] = parsed_date
        #             break
        
        # Date d'échéance - temporairement désactivée à cause du problème Pydantic
        # due_date_patterns = [
        #     r'(?:Date\s*d.échéance|échéance|Due\s*date)[\s:]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        #     r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})'
        # ]
        # 
        # for pattern in due_date_patterns:
        #     match = re.search(pattern, text, re.IGNORECASE)
        #     if match:
        #         parsed_due_date = self._parse_date(match.group(1))
        #         if parsed_due_date:
        #             invoice_info['due_date'] = parsed_due_date
        #             break
        
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
        
        # Patterns améliorés pour les montants totaux
        total_patterns = [
            # Sous-total HT
            (r'(?:Sous.total|TOTAL\s+HT)[\s:]*(\d+(?:[,\.]\d{2})?)', 'subtotal_excl_vat'),
            # TVA
            (r'(?:TVA\s*\d+%|TVA)[\s:]*(\d+(?:[,\.]\d{2})?)', 'total_vat'),
            # Total TTC
            (r'(?:TOTAL\s+TTC|Total\s+TTC)[\s:]*(\d+(?:[,\.]\d{2})?)', 'total_incl_vat'),
            # Montant à payer
            (r'(?:TOTAL|Total)[\s:]*(\d+(?:[,\.]\d{2})?)', 'amount_due')
        ]
        
        # Chercher les montants dans le texte
        lines = text.split('\n')
        for line in lines:
            line_upper = line.upper()
            
            # Chercher spécifiquement les lignes de totaux
            if any(keyword in line_upper for keyword in ['TOTAL', 'TVA', 'SOUS-TOTAL']):
                for pattern, field in total_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match and field not in totals_info:
                        try:
                            amount_str = match.group(1).replace(',', '.')
                            amount = float(amount_str)
                            totals_info[field] = amount
                        except ValueError:
                            continue
        
        # Si on trouve un montant TTC, l'utiliser aussi comme montant dû
        if 'total_incl_vat' in totals_info and 'amount_due' not in totals_info:
            totals_info['amount_due'] = totals_info['total_incl_vat']
        
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
    
    def _extract_address_from_section(self, section_lines: List[str]) -> Optional[Dict[str, Any]]:
        """Extrait l'adresse d'une section de texte"""
        if not section_lines:
            return None
        
        address_info = {}
        
        # Chercher les lignes qui ressemblent à une adresse
        for line in section_lines:
            # Code postal et ville (pattern français)
            postal_match = re.search(r'(\d{5})\s+([A-Z\s]+)', line.upper())
            if postal_match:
                address_info['postal_code'] = postal_match.group(1)
                address_info['city'] = postal_match.group(2).strip()
                continue
            
            # Rue/avenue (contient des numéros et des mots comme rue, avenue, etc.)
            if re.search(r'\d+.*(?:rue|avenue|boulevard|place|rond.point|parc)', line, re.IGNORECASE):
                address_info['street'] = line
                continue
        
        # Pays par défaut
        if address_info:
            address_info['country'] = 'France'
        
        return address_info if address_info else None
    
    def _extract_contact_from_section(self, section_lines: List[str]) -> Optional[Dict[str, Any]]:
        """Extrait les informations de contact d'une section de texte"""
        if not section_lines:
            return None
        
        contact_info = {}
        
        for line in section_lines:
            # Email
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
            if email_match:
                contact_info['email'] = email_match.group(1)
            
            # Téléphone
            phone_match = re.search(r'(?:tél|tel|phone)[\s:]*([0-9\s\.\-\+]{10,})', line, re.IGNORECASE)
            if phone_match:
                contact_info['phone'] = phone_match.group(1).strip()
        
        return contact_info if contact_info else None
