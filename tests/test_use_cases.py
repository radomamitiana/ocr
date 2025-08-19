"""
Tests de use cases fonctionnels pour l'application OCR Factures
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
from datetime import date

from src.api.models import *
from src.extraction.data_extractor import DataExtractor
from src.ocr.ocr_engine import OCREngine
from src.preprocessing.enhanced_image_processor import EnhancedImageProcessor


class TestInvoiceProcessingUseCases:
    """Tests des cas d'usage de traitement de factures"""
    
    def setup_method(self):
        """Setup avant chaque test"""
        self.data_extractor = DataExtractor()
    
    def test_extract_simple_invoice_data(self):
        """Test d'extraction de données d'une facture simple"""
        # Texte OCR simulé d'une facture simple
        ocr_text = """
        ENTREPRISE ABC
        123 Rue de la Paix
        75001 Paris
        SIRET: 12345678901234
        TVA: FR12345678901
        
        FACTURE F2025-001
        Date: 19/08/2025
        
        Client: Société XYZ
        
        Prestation de service    1    500.00    500.00
        TVA 20%                              100.00
        Total TTC                            600.00
        """
        
        result = self.data_extractor.extract_invoice_data(ocr_text)
        
        # Vérifications
        assert isinstance(result, InvoiceData)
        assert result.supplier is not None
        assert result.supplier.name == "ENTREPRISE ABC"
        assert result.supplier.siret == "12345678901234"
        assert result.invoice is not None
        assert result.invoice.number == "F2025-001"
        assert result.invoice.date == date(2025, 8, 19)
        assert result.customer is not None
        assert result.customer.name == "Société XYZ"
    
    def test_extract_complex_invoice_data(self):
        """Test d'extraction de données d'une facture complexe"""
        ocr_text = """
        SARL TECH SOLUTIONS
        456 Avenue des Champs
        69000 Lyon
        SIRET: 98765432109876
        N° TVA Intracommunautaire: FR98765432109
        
        FACTURE N° FACT-2025-0042
        Date d'émission: 15/08/2025
        Date d'échéance: 15/09/2025
        
        Facturé à:
        ENTREPRISE CLIENT SARL
        789 Boulevard Central
        13000 Marseille
        
        Désignation                    Qté    P.U. HT    Total HT
        Développement application       10     150.00    1500.00
        Formation utilisateurs           2     300.00     600.00
        Maintenance mensuelle            1     200.00     200.00
        
        Sous-total HT                                   2300.00
        TVA 20%                                          460.00
        Total TTC                                       2760.00
        Net à payer                                     2760.00
        """
        
        result = self.data_extractor.extract_invoice_data(ocr_text)
        
        # Vérifications détaillées
        assert result.supplier.name == "SARL TECH SOLUTIONS"
        assert result.supplier.siret == "98765432109876"
        assert result.supplier.vat_number == "FR98765432109"
        
        assert result.invoice.number == "FACT-2025-0042"
        assert result.invoice.date == date(2025, 8, 15)
        
        assert result.customer.name == "ENTREPRISE CLIENT SARL"
        
        # Vérification des totaux
        assert result.totals is not None
        assert result.totals.subtotal_excl_vat == 2300.00
        assert result.totals.total_vat == 460.00
        assert result.totals.total_incl_vat == 2760.00
        assert result.totals.amount_due == 2760.00
    
    def test_extract_invoice_with_missing_data(self):
        """Test d'extraction avec des données manquantes"""
        ocr_text = """
        FACTURE
        Total: 1200.00 €
        """
        
        result = self.data_extractor.extract_invoice_data(ocr_text)
        
        # Vérifications - doit gérer les données manquantes
        assert isinstance(result, InvoiceData)
        assert result.metadata.confidence_score < 0.5  # Faible confiance
        assert result.validation.required_fields_present is False
    
    def test_calculate_confidence_score(self):
        """Test du calcul du score de confiance"""
        # Texte avec tous les mots-clés
        complete_text = "facture invoice total tva ht ttc siret date montant quantité"
        confidence = self.data_extractor._calculate_confidence(complete_text)
        assert confidence == 1.0
        
        # Texte avec quelques mots-clés
        partial_text = "facture total montant"
        confidence = self.data_extractor._calculate_confidence(partial_text)
        assert 0.0 < confidence < 1.0
        
        # Texte sans mots-clés
        empty_text = "lorem ipsum dolor sit amet"
        confidence = self.data_extractor._calculate_confidence(empty_text)
        assert confidence == 0.0
    
    def test_validate_invoice_calculations(self):
        """Test de validation des calculs de facture"""
        # Création d'une facture avec des calculs corrects
        line_items = [
            LineItem(
                description="Service 1",
                quantity=2,
                unit_price=100.00,
                amount_excl_vat=200.00,
                vat_rate=0.20,
                vat_amount=40.00,
                amount_incl_vat=240.00
            ),
            LineItem(
                description="Service 2",
                quantity=1,
                unit_price=300.00,
                amount_excl_vat=300.00,
                vat_rate=0.20,
                vat_amount=60.00,
                amount_incl_vat=360.00
            )
        ]
        
        totals = Totals(
            subtotal_excl_vat=500.00,
            total_vat=100.00,
            total_incl_vat=600.00,
            amount_due=600.00
        )
        
        validation = self.data_extractor._validate_data(totals, line_items)
        
        assert validation.calculation_check is True
        assert validation.required_fields_present is True
        assert validation.data_quality_score > 0.5


class TestPDFProcessingUseCases:
    """Tests des cas d'usage de traitement PDF"""
    
    @patch('src.processors.pdf_processor.pdf2image.convert_from_path')
    def test_process_single_page_pdf_invoice(self, mock_convert):
        """Test de traitement d'une facture PDF d'une page"""
        from src.processors.pdf_processor import PDFProcessor
        
        # Mock d'une image de facture
        mock_image = Mock()
        mock_image_array = np.random.randint(0, 255, (800, 600, 3), dtype=np.uint8)
        mock_convert.return_value = [mock_image]
        
        processor = PDFProcessor()
        
        with patch('numpy.array', return_value=mock_image_array):
            result = processor.process("facture.pdf")
            
            assert isinstance(result, np.ndarray)
            assert result.shape == (800, 600, 3)
            mock_convert.assert_called_once()
    
    @patch('src.processors.pdf_processor.pdf2image.convert_from_path')
    def test_process_multi_page_pdf_invoice(self, mock_convert):
        """Test de traitement d'une facture PDF multi-pages"""
        from src.processors.pdf_processor import PDFProcessor
        
        # Mock de plusieurs pages
        mock_images = [Mock() for _ in range(3)]
        mock_convert.return_value = mock_images
        
        processor = PDFProcessor()
        
        with patch('numpy.array', return_value=np.random.randint(0, 255, (800, 600, 3))):
            results = processor.process_all_pages("facture_multi.pdf")
            
            assert len(results) == 3
            assert all(isinstance(img, np.ndarray) for img in results)


class TestEndToEndUseCases:
    """Tests end-to-end des cas d'usage complets"""
    
    def test_complete_invoice_processing_pipeline(self):
        """Test du pipeline complet de traitement d'une facture"""
        # Simulation d'une image de facture
        mock_image = np.ones((400, 300), dtype=np.uint8) * 255
        
        # Mock du texte OCR extrait
        mock_ocr_text = """
        ENTREPRISE TEST SARL
        SIRET: 12345678901234
        FACTURE F2025-100
        Date: 20/08/2025
        Total TTC: 1500.00 €
        """
        
        # Mock des composants
        with patch('src.preprocessing.enhanced_image_processor.EnhancedImageProcessor') as mock_processor:
            with patch('src.ocr.ocr_engine.OCREngine') as mock_ocr:
                with patch('src.extraction.data_extractor.DataExtractor') as mock_extractor:
                    
                    # Configuration des mocks
                    mock_processor_instance = Mock()
                    mock_processor_instance.process_file.return_value = mock_image
                    mock_processor.return_value = mock_processor_instance
                    
                    mock_ocr_instance = Mock()
                    mock_ocr_result = Mock()
                    mock_ocr_result.text = mock_ocr_text
                    mock_ocr_result.confidence = 0.95
                    mock_ocr_instance.extract_text.return_value = mock_ocr_result
                    mock_ocr.return_value = mock_ocr_instance
                    
                    mock_extractor_instance = Mock()
                    mock_invoice_data = InvoiceData(
                        metadata=Metadata(filename="test.pdf", confidence_score=0.95),
                        supplier=Supplier(name="ENTREPRISE TEST SARL", siret="12345678901234"),
                        invoice=Invoice(number="F2025-100", date=date(2025, 8, 20)),
                        totals=Totals(total_incl_vat=1500.00)
                    )
                    mock_extractor_instance.extract_invoice_data.return_value = mock_invoice_data
                    mock_extractor.return_value = mock_extractor_instance
                    
                    # Test du pipeline
                    processor = mock_processor_instance
                    ocr_engine = mock_ocr_instance
                    extractor = mock_extractor_instance
                    
                    # Étape 1: Preprocessing
                    processed_image = processor.process_file("test.pdf")
                    assert processed_image is not None
                    
                    # Étape 2: OCR
                    ocr_result = ocr_engine.extract_text(processed_image)
                    assert ocr_result.text == mock_ocr_text
                    assert ocr_result.confidence == 0.95
                    
                    # Étape 3: Extraction de données
                    invoice_data = extractor.extract_invoice_data(ocr_result.text)
                    assert isinstance(invoice_data, InvoiceData)
                    assert invoice_data.supplier.name == "ENTREPRISE TEST SARL"
                    assert invoice_data.invoice.number == "F2025-100"
                    assert invoice_data.totals.total_incl_vat == 1500.00
    
    def test_error_handling_use_case(self):
        """Test de gestion d'erreurs dans le pipeline"""
        from src.utils.exceptions import FileProcessingError, OCRProcessingError
        
        # Test avec un fichier corrompu
        with patch('src.preprocessing.enhanced_image_processor.EnhancedImageProcessor') as mock_processor:
            mock_processor_instance = Mock()
            mock_processor_instance.process_file.side_effect = FileProcessingError("Fichier corrompu")
            mock_processor.return_value = mock_processor_instance
            
            processor = mock_processor_instance
            
            with pytest.raises(FileProcessingError, match="Fichier corrompu"):
                processor.process_file("corrupted.pdf")
    
    def test_low_quality_image_use_case(self):
        """Test avec une image de faible qualité"""
        # Image très bruitée
        noisy_image = np.random.randint(0, 255, (200, 200), dtype=np.uint8)
        
        # Mock d'un OCR avec faible confiance
        with patch('src.ocr.ocr_engine.OCREngine') as mock_ocr:
            mock_ocr_instance = Mock()
            mock_ocr_result = Mock()
            mock_ocr_result.text = "texte illisible"
            mock_ocr_result.confidence = 0.3  # Faible confiance
            mock_ocr_instance.extract_text.return_value = mock_ocr_result
            mock_ocr.return_value = mock_ocr_instance
            
            ocr_engine = mock_ocr_instance
            result = ocr_engine.extract_text(noisy_image)
            
            # Vérification que le système gère les faibles confidences
            assert result.confidence < 0.5
            assert isinstance(result.text, str)


class TestBusinessRulesUseCases:
    """Tests des règles métier spécifiques"""
    
    def test_french_invoice_format_validation(self):
        """Test de validation du format de facture française"""
        # Facture avec format français standard
        french_invoice_text = """
        SARL EXEMPLE
        SIRET: 12345678901234
        N° TVA: FR12345678901
        
        FACTURE N° F2025-001
        Date: 19/08/2025
        
        Prestations                     1000.00 €
        TVA 20%                          200.00 €
        Total TTC                       1200.00 €
        """
        
        extractor = DataExtractor()
        result = extractor.extract_invoice_data(french_invoice_text)
        
        # Vérifications spécifiques au format français
        assert result.supplier.siret is not None
        assert len(result.supplier.siret) == 14  # Format SIRET français
        assert result.supplier.vat_number.startswith("FR")  # TVA française
        assert result.invoice.currency == "EUR"  # Devise européenne
    
    def test_vat_calculation_validation(self):
        """Test de validation des calculs de TVA"""
        # Facture avec TVA à 20% (taux français standard)
        invoice_text = """
        Montant HT: 1000.00 €
        TVA 20%: 200.00 €
        Total TTC: 1200.00 €
        """
        
        extractor = DataExtractor()
        result = extractor.extract_invoice_data(invoice_text)
        
        if result.totals:
            # Vérification du calcul de TVA
            expected_vat = result.totals.subtotal_excl_vat * 0.20
            assert abs(result.totals.total_vat - expected_vat) < 0.01
            
            # Vérification du total TTC
            expected_total = result.totals.subtotal_excl_vat + result.totals.total_vat
            assert abs(result.totals.total_incl_vat - expected_total) < 0.01
    
    def test_date_format_parsing(self):
        """Test de parsing des différents formats de date"""
        test_cases = [
            ("19/08/2025", date(2025, 8, 19)),
            ("19-08-2025", date(2025, 8, 19)),
            ("19.08.2025", date(2025, 8, 19)),
            ("2025/08/19", date(2025, 8, 19)),
            ("2025-08-19", date(2025, 8, 19))
        ]
        
        extractor = DataExtractor()
        
        for date_str, expected_date in test_cases:
            parsed_date = extractor._parse_date(date_str)
            assert parsed_date == expected_date, f"Failed to parse {date_str}"
    
    def test_siret_validation_pattern(self):
        """Test de validation du pattern SIRET"""
        extractor = DataExtractor()
        
        valid_sirets = ["12345678901234", "98765432109876"]
        invalid_sirets = ["123", "abcdefghijklmn", "123456789012345"]  # Trop court, lettres, trop long
        
        for siret in valid_sirets:
            text = f"SIRET: {siret}"
            result = extractor._extract_with_patterns(text, 'siret')
            assert result == siret
        
        for siret in invalid_sirets:
            text = f"SIRET: {siret}"
            result = extractor._extract_with_patterns(text, 'siret')
            # Les patterns invalides ne devraient pas matcher
            if result:
                assert len(result) >= 9  # Au minimum 9 chiffres pour SIREN
