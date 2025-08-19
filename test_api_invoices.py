"""
Script de test pour l'API process-invoice avec les factures du dossier invoices
"""

import os
import requests
import json
from pathlib import Path
import time

def test_api_with_invoices():
    """Test l'API avec toutes les factures du dossier invoices"""
    
    # Configuration
    api_url = "http://localhost:8000/api/v1/process-invoice"
    invoices_dir = Path("invoices")
    
    # Vérifier que le dossier existe
    if not invoices_dir.exists():
        print(f"❌ Dossier {invoices_dir} non trouvé")
        return
    
    # Récupérer tous les fichiers PDF
    pdf_files = list(invoices_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ Aucun fichier PDF trouvé dans {invoices_dir}")
        return
    
    print(f"🔍 Trouvé {len(pdf_files)} factures à traiter")
    print("="*60)
    
    results = []
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n📄 Test {i}/{len(pdf_files)}: {pdf_file.name}")
        print("-" * 40)
        
        try:
            # Préparer le fichier pour l'upload
            with open(pdf_file, 'rb') as f:
                files = {
                    'file': (pdf_file.name, f, 'application/pdf')
                }
                
                # Options de traitement
                options = {
                    "language": "fra",
                    "enable_validation": True,
                    "confidence_threshold": 0.7
                }
                
                data = {
                    'options': json.dumps(options)
                }
                
                # Appel à l'API
                start_time = time.time()
                response = requests.post(api_url, files=files, data=data, timeout=60)
                processing_time = time.time() - start_time
                
                print(f"⏱️  Temps de traitement: {processing_time:.2f}s")
                print(f"📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print("✅ Traitement réussi!")
                    
                    # Afficher les données extraites
                    if 'invoice' in result:
                        invoice = result['invoice']
                        print(f"   📋 Numéro: {invoice.get('invoiceNumber', 'N/A')}")
                        print(f"   📅 Date: {invoice.get('invoiceDate', 'N/A')}")
                        print(f"   🏢 Société: {invoice.get('companyErpCode', 'N/A')}")
                        print(f"   🏭 Fournisseur: {invoice.get('supplierName', 'N/A')}")
                        print(f"   💰 Montant TTC: {invoice.get('includingTaxes', 'N/A')}")
                        print(f"   💱 Devise: {invoice.get('currencyCode', 'N/A')}")
                        
                        # Vérifier les valeurs null
                        null_fields = []
                        critical_fields = ['invoiceNumber', 'invoiceDate', 'companyErpCode', 
                                         'supplierName', 'includingTaxes']
                        
                        for field in critical_fields:
                            if not invoice.get(field):
                                null_fields.append(field)
                        
                        if null_fields:
                            print(f"   ⚠️  Champs null: {', '.join(null_fields)}")
                        else:
                            print("   ✅ Tous les champs critiques sont remplis")
                    
                    results.append({
                        'file': pdf_file.name,
                        'status': 'success',
                        'processing_time': processing_time,
                        'data': result
                    })
                    
                else:
                    error_detail = response.json() if response.content else {'error': 'Unknown error'}
                    print(f"❌ Erreur: {error_detail}")
                    
                    results.append({
                        'file': pdf_file.name,
                        'status': 'error',
                        'processing_time': processing_time,
                        'error': error_detail
                    })
                
        except requests.exceptions.Timeout:
            print("❌ Timeout - Le traitement a pris trop de temps")
            results.append({
                'file': pdf_file.name,
                'status': 'timeout',
                'processing_time': 60,
                'error': 'Request timeout'
            })
            
        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            results.append({
                'file': pdf_file.name,
                'status': 'exception',
                'processing_time': 0,
                'error': str(e)
            })
    
    # Résumé des résultats
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*60)
    
    successful = len([r for r in results if r['status'] == 'success'])
    failed = len(results) - successful
    
    print(f"✅ Réussis: {successful}/{len(results)}")
    print(f"❌ Échoués: {failed}/{len(results)}")
    
    if successful > 0:
        avg_time = sum([r['processing_time'] for r in results if r['status'] == 'success']) / successful
        print(f"⏱️  Temps moyen: {avg_time:.2f}s")
    
    # Détail des échecs
    if failed > 0:
        print(f"\n❌ DÉTAIL DES ÉCHECS:")
        for result in results:
            if result['status'] != 'success':
                print(f"   - {result['file']}: {result.get('error', 'Unknown error')}")
    
    # Sauvegarde des résultats
    results_file = Path("test_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Résultats sauvegardés dans {results_file}")
    
    return results

def check_api_health():
    """Vérifie que l'API est accessible"""
    try:
        health_url = "http://localhost:8000/api/v1/health"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            print("✅ API accessible et fonctionnelle")
            return True
        else:
            print(f"❌ API répond avec le code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter à l'API")
        print("   Vérifiez que le serveur est démarré sur http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 TEST DE L'API PROCESS-INVOICE")
    print("="*60)
    
    # Vérifier que l'API est accessible
    if not check_api_health():
        print("\n💡 Pour démarrer l'API:")
        print("   cd ocr_factures")
        print("   python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload")
        exit(1)
    
    # Lancer les tests
    results = test_api_with_invoices()
    
    print("\n🏁 Tests terminés!")
