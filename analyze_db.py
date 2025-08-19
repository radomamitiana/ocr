"""
Script d'analyse de la base de données PostgreSQL
"""

import sys
import json
from pathlib import Path

# Ajout du chemin src au PYTHONPATH
sys.path.append(str(Path(__file__).parent / "src"))

from src.database.connection import test_connection, analyze_database_schema, get_all_tables
from src.utils.logger import app_logger


def main():
    """
    Fonction principale d'analyse de la base de données
    """
    print("=== Analyse de la base de données PostgreSQL ===\n")
    
    # Test de connexion
    print("1. Test de connexion...")
    if test_connection():
        print("✅ Connexion réussie\n")
    else:
        print("❌ Échec de la connexion")
        return
    
    # Liste des tables disponibles
    print("2. Liste des tables disponibles...")
    all_tables = get_all_tables()
    if all_tables:
        print("Tables trouvées:")
        for table in all_tables:
            print(f"  - {table}")
        print()
    else:
        print("❌ Aucune table trouvée")
        return
    
    # Analyse du schéma
    print("3. Analyse du schéma des tables...")
    schema_info = analyze_database_schema()
    
    if not schema_info:
        print("❌ Aucune table trouvée")
        return
    
    # Affichage des résultats
    for table_name, structure in schema_info.items():
        print(f"\n📋 Table: {table_name}")
        print("=" * 50)
        
        if structure and structure.get('columns'):
            print("Colonnes:")
            for col in structure['columns']:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                max_length = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"  - {col['column_name']}: {col['data_type']}{max_length} {nullable}{default}")
        
        if structure and structure.get('constraints'):
            print("\nContraintes:")
            for constraint in structure['constraints']:
                print(f"  - {constraint['constraint_type']}: {constraint['constraint_name']} ({constraint['column_name']})")
    
    # Sauvegarde du schéma dans un fichier JSON
    output_file = Path(__file__).parent / "database_schema.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(schema_info, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Schéma sauvegardé dans: {output_file}")
    print("\n✅ Analyse terminée")


if __name__ == "__main__":
    main()
