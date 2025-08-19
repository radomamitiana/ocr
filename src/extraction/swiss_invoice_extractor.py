"""
Extracteur spécialisé pour les factures suisses utilisant la base de données
"""

import re
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import text
from src.database.connection import get_db
from src.utils.logger import app_logger


class SwissInvoiceExtractor:
    """Extracteur spécialisé utilisant la base de données pour l'apprentissage"""
    
    def __init__(self):
        self.db = None
        
        # Patterns génériques pour les factures
        self.invoice_number_patterns = [
            r"N[°\s]*de\s+facture\s*:?\s*(\d+(?:\s+\d+)*)",
            r"facture\s*:?\s*(\d+(?:\s+\d+)*)",
            r"N[°\s]*facture\s*:?\s*(\d+(?:\s+\d+)*)"
        ]
        
        self.date_patterns = [
            r"Date\s*:?\s*(\d{1,2})\s+(\w+)\s+(\d{4})",
            r"(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})"
        ]
        
        self.currency_patterns = [
            r"Montant\s+(CHF|EUR|USD)",
            r"(CHF|EUR|USD)\s+[\d\s'.,]+",
            r"Monnaie\s+(CHF|EUR|USD)"
        ]
        
        # Patterns génériques pour les montants
        self.amount_patterns = {
            'total_ttc': [
                r"Montant\s+à\s+payer[^\\n]*(?:CHF|EUR|USD)\s+([\d\s'.,]+)",
                r"Total\s+du\s+décompte[^\\n]*(?:CHF|EUR|USD)\s+([\d\s'.,]+)",
                r"(?:CHF|EUR|USD)\s+([\d\s'.,]+)(?=\s*$|\s*Point)"
            ],
            'total_ht': [
                r"Total\s+.*\(hors\s+TVA\)[^\\n]*(?:CHF|EUR|USD)\s+([\d\s'.,]+)",
                r"Electricité[^\\n]*(?:CHF|EUR|USD)\s+([\d\s'.,]+)(?=\s*TVA)"
            ],
            'tva': [
                r"TVA[^\\n]*(?:CHF|EUR|USD)\s+([\d\s'.,]+)",
                r"Total\s+TVA[^\\n]*(?:CHF|EUR|USD)\s+([\d\s'.,]+)"
            ]
        }
        
        # Mapping des mois français
        self.month_mapping = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
        }
    
    def extract_invoice_data_with_db(self, text: str) -> Dict[str, Any]:
        """Extrait les données de facture en utilisant la base de données"""
        app_logger.info("Extraction des données de facture avec base de données")
        
        # Création d'une nouvelle session de base de données
        self.db = next(get_db())
        
        try:
            # Nettoyage du texte
            clean_text = self._clean_text(text)
            
            extracted_data = {
                'invoice_number': self._extract_invoice_number(clean_text),
                'invoice_date': self._extract_date(clean_text),
                'company_erp_code': self._extract_company_from_db(clean_text),
                'supplier_name': self._extract_supplier_from_db(clean_text),
                'currency_code': self._extract_currency(clean_text),
                'amounts': self._extract_amounts(clean_text)
            }
            
            app_logger.info(f"Données extraites: {extracted_data}")
            return extracted_data
            
        finally:
            if self.db:
                self.db.close()
    
    def _clean_text(self, text: str) -> str:
        """Nettoie le texte pour améliorer l'extraction"""
        # Supprime les caractères de contrôle et normalise les espaces
        clean_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()
    
    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extrait le numéro de facture"""
        for pattern in self.invoice_number_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Nettoie le numéro (supprime les espaces)
                invoice_number = re.sub(r'\s+', '', match.group(1))
                app_logger.info(f"Numéro de facture trouvé: {invoice_number}")
                return invoice_number
        
        app_logger.warning("Numéro de facture non trouvé")
        return None
    
    def _extract_date(self, text: str) -> Optional[date]:
        """Extrait la date de facture"""
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    day = int(match.group(1))
                    month_name = match.group(2).lower()
                    year = int(match.group(3))
                    
                    month = self.month_mapping.get(month_name)
                    if month:
                        invoice_date = date(year, month, day)
                        app_logger.info(f"Date de facture trouvée: {invoice_date}")
                        return invoice_date
                except (ValueError, IndexError) as e:
                    app_logger.warning(f"Erreur lors du parsing de la date: {e}")
                    continue
        
        app_logger.warning("Date de facture non trouvée")
        return None
    
    def _extract_company_from_db(self, invoice_text: str) -> Optional[str]:
        """Extrait le code ERP de la société en utilisant la base de données"""
        try:
            # Récupération de tous les codes ERP des sociétés
            from sqlalchemy import text as sql_text
            query = sql_text("""
                SELECT company_erp_code, company_name 
                FROM company 
                WHERE company_erp_code IS NOT NULL
            """)
            
            companies = self.db.execute(query).fetchall()
            
            # Recherche dans le texte
            for company in companies:
                company_erp_code = company[0]
                company_name = company[1] if company[1] else ""
                
                # Recherche du code ERP dans le texte
                if company_erp_code and re.search(re.escape(company_erp_code), invoice_text, re.IGNORECASE):
                    app_logger.info(f"Code ERP société trouvé: {company_erp_code}")
                    return company_erp_code
                
                # Recherche du nom de société dans le texte
                if company_name and len(company_name) > 3:
                    # Recherche flexible du nom de société
                    company_words = company_name.split()
                    if len(company_words) >= 2:
                        # Recherche des premiers mots significatifs
                        search_pattern = r'\b' + re.escape(' '.join(company_words[:2])) + r'\b'
                        if re.search(search_pattern, invoice_text, re.IGNORECASE):
                            app_logger.info(f"Société trouvée par nom: {company_name} -> {company_erp_code}")
                            return company_erp_code
            
            app_logger.warning("Aucune société trouvée dans la base de données")
            return None
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la recherche de société: {str(e)}")
            return None
    
    def _extract_supplier_from_db(self, invoice_text: str) -> Optional[str]:
        """Extrait le nom du fournisseur en utilisant la base de données"""
        try:
            # Récupération de tous les noms de fournisseurs
            from sqlalchemy import text as sql_text
            query = sql_text("""
                SELECT DISTINCT supplier_name 
                FROM supplier 
                WHERE supplier_name IS NOT NULL 
                AND LENGTH(supplier_name) > 3
            """)
            
            suppliers = self.db.execute(query).fetchall()
            
            # Recherche dans le texte
            for supplier_row in suppliers:
                supplier_name = supplier_row[0]
                
                if supplier_name:
                    # Recherche exacte du nom
                    if re.search(re.escape(supplier_name), invoice_text, re.IGNORECASE):
                        app_logger.info(f"Fournisseur trouvé: {supplier_name}")
                        return supplier_name
                    
                    # Recherche flexible par mots-clés
                    supplier_words = supplier_name.split()
                    if len(supplier_words) >= 2:
                        # Recherche des premiers mots significatifs
                        search_pattern = r'\b' + re.escape(' '.join(supplier_words[:2])) + r'\b'
                        if re.search(search_pattern, invoice_text, re.IGNORECASE):
                            app_logger.info(f"Fournisseur trouvé par mots-clés: {supplier_name}")
                            return supplier_name
            
            app_logger.warning("Aucun fournisseur trouvé dans la base de données")
            return None
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la recherche de fournisseur: {str(e)}")
            return None
    
    def _extract_currency(self, text: str) -> str:
        """Extrait le code de devise"""
        for pattern in self.currency_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                currency = match.group(1).upper()
                app_logger.info(f"Devise trouvée: {currency}")
                return currency
        
        # Par défaut CHF pour les factures suisses
        app_logger.info("Devise par défaut: CHF")
        return "CHF"
    
    def _extract_amounts(self, text: str) -> Dict[str, Optional[Decimal]]:
        """Extrait les montants de la facture"""
        amounts = {
            'total_ttc': None,
            'total_ht': None,
            'tva': None
        }
        
        for amount_type, patterns in self.amount_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    try:
                        # Nettoie le montant (supprime espaces et apostrophes)
                        amount_str = match.group(1)
                        amount_str = re.sub(r"[\s']", '', amount_str)
                        amount_str = amount_str.replace(',', '.')
                        
                        amount = Decimal(amount_str)
                        amounts[amount_type] = amount
                        app_logger.info(f"{amount_type} trouvé: {amount}")
                        break
                    except (ValueError, IndexError) as e:
                        app_logger.warning(f"Erreur lors du parsing du montant {amount_type}: {e}")
                        continue
        
        return amounts
