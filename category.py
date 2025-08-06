#!/usr/bin/env python3
"""
KDP Category List Converter
Converts ebooks_us_category_list_2024-06-03.xlsx to structured JSON format
for use in KDP automation category selection
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Any
import re

class KDPCategoryConverter:
    def __init__(self, excel_file_path: str):
        self.excel_file_path = excel_file_path
        self.categories_df = None
        self.load_categories()
    
    def load_categories(self):
        """Load categories from Excel file"""
        try:
            print(f"Loading categories from: {self.excel_file_path}")
            self.categories_df = pd.read_excel(self.excel_file_path)
            print(f"Loaded {len(self.categories_df)} categories")
            
            # Display column info
            print(f"Columns: {list(self.categories_df.columns)}")
            
            # Show sample data
            print("\nSample category:")
            sample = self.categories_df.iloc[0]
            for col in self.categories_df.columns:
                print(f"  {col}: {sample[col]}")
                
        except Exception as e:
            print(f"Error loading Excel file: {e}")
            raise
    
    def clean_category_path(self, path: str) -> List[str]:
        """Clean and split category path into components"""
        if pd.isna(path):
            return []
        
        # Remove "Kindle eBooks > " prefix
        clean_path = str(path).replace("Kindle eBooks > ", "")
        
        # Split by " > " separator
        components = [comp.strip() for comp in clean_path.split(" > ")]
        
        return [comp for comp in components if comp]  # Remove empty strings
    
    def build_hierarchical_structure(self) -> Dict[str, Any]:
        """Build hierarchical category tree structure"""
        tree = {}
        
        for _, row in self.categories_df.iterrows():
            path_components = self.clean_category_path(row['Category Path'])
            
            if not path_components:
                continue
            
            # Navigate/create tree structure
            current_level = tree
            
            for i, component in enumerate(path_components):
                if component not in current_level:
                    current_level[component] = {
                        'children': {},
                        'data': None  # Will store category data for leaf nodes
                    }
                
                # If this is the final component, store the full category data
                if i == len(path_components) - 1:
                    current_level[component]['data'] = {
                        'browseNodeID': str(row['browseNodeID']) if pd.notna(row['browseNodeID']) else None,
                        'name': str(row['name']) if pd.notna(row['name']) else None,
                        'level': int(row['Level']) if pd.notna(row['Level']) else None,
                        'fullName': str(row['fullName']) if pd.notna(row['fullName']) else None,
                        'parentBrowseNodeID': str(row['parentBrowseNodeID']) if pd.notna(row['parentBrowseNodeID']) else None,
                        'topLevelCategoryName': str(row['topLevelCategoryName']) if pd.notna(row['topLevelCategoryName']) else None,
                        'book1Rank': int(row['Book1Rank']) if pd.notna(row['Book1Rank']) else None,
                        'book100Rank': int(row['Book100Rank']) if pd.notna(row['Book100Rank']) else None,
                        'categoryPath': path_components,
                        'categoryPathString': ' > '.join(path_components)
                    }
                
                current_level = current_level[component]['children']
        
        return tree
    
    def build_lookup_tables(self) -> Dict[str, Any]:
        """Build various lookup tables for easy category finding"""
        lookups = {
            'by_browse_node_id': {},
            'by_name': {},
            'by_path': {},
            'by_top_level': {},
            'by_bisac_mapping': {}  # We'll add BISAC mappings here
        }
        
        for _, row in self.categories_df.iterrows():
            path_components = self.clean_category_path(row['Category Path'])
            
            category_data = {
                'browseNodeID': str(row['browseNodeID']) if pd.notna(row['browseNodeID']) else None,
                'name': str(row['name']) if pd.notna(row['name']) else None,
                'level': int(row['Level']) if pd.notna(row['Level']) else None,
                'fullName': str(row['fullName']) if pd.notna(row['fullName']) else None,
                'parentBrowseNodeID': str(row['parentBrowseNodeID']) if pd.notna(row['parentBrowseNodeID']) else None,
                'topLevelCategoryName': str(row['topLevelCategoryName']) if pd.notna(row['topLevelCategoryName']) else None,
                'categoryPath': path_components,
                'categoryPathString': ' > '.join(path_components) if path_components else '',
                'book1Rank': int(row['Book1Rank']) if pd.notna(row['Book1Rank']) else None,
                'book100Rank': int(row['Book100Rank']) if pd.notna(row['Book100Rank']) else None
            }
            
            # By browse node ID
            if category_data['browseNodeID']:
                lookups['by_browse_node_id'][category_data['browseNodeID']] = category_data
            
            # By name (case insensitive)
            if category_data['name']:
                name_key = category_data['name'].lower()
                if name_key not in lookups['by_name']:
                    lookups['by_name'][name_key] = []
                lookups['by_name'][name_key].append(category_data)
            
            # By full path
            if path_components:
                path_key = ' > '.join(path_components).lower()
                lookups['by_path'][path_key] = category_data
            
            # By top level category
            if category_data['topLevelCategoryName']:
                top_level_key = category_data['topLevelCategoryName'].lower()
                if top_level_key not in lookups['by_top_level']:
                    lookups['by_top_level'][top_level_key] = []
                lookups['by_top_level'][top_level_key].append(category_data)
        
        return lookups
    
    def create_bisac_mapping(self) -> Dict[str, List[str]]:
        """Create enhanced BISAC to KDP category mapping based on actual KDP data"""
        
        # Enhanced BISAC mapping using actual KDP category structure
        bisac_mapping = {
            # Sports & Recreation -> Sports & Outdoors
            'SPO032000': ['Sports & Outdoors', 'Water Sports', 'Fishing'],  # Fishing
            'SPO000000': ['Sports & Outdoors'],  # General Sports
            'SPO016000': ['Sports & Outdoors', 'Hunting & Fishing', 'Hunting'],  # Hunting
            'SPO025000': ['Sports & Outdoors', 'Outdoor Recreation'],  # Outdoor Recreation
            'SPO013000': ['Sports & Outdoors', 'Individual Sports', 'Golf'],  # Golf
            'SPO063000': ['Sports & Outdoors', 'Water Sports'],  # Water Sports
            
            # Fiction -> Literature & Fiction
            'FIC027000': ['Literature & Fiction', 'Erotica'],  # Erotica General
            'FIC027020': ['Literature & Fiction', 'Erotica'],  # BDSM
            'FIC027060': ['Literature & Fiction', 'Erotica'],  # Suspense
            'FIC027120': ['Literature & Fiction', 'Erotica'],  # Romantic
            'FIC000000': ['Literature & Fiction'],  # General Fiction
            'FIC022000': ['Literature & Fiction', 'Literary Fiction'],  # Literary
            'FIC028000': ['Literature & Fiction', 'Short Stories'],  # Short Stories
            'FIC006000': ['Literature & Fiction', 'Action & Adventure'],  # Action & Adventure
            'FIC017000': ['Literature & Fiction', 'Fantasy'],  # Fantasy
            'FIC023000': ['Literature & Fiction', 'Psychological Thrillers'],  # Psychological
            'FIC014000': ['Literature & Fiction', 'Historical Fiction'],  # Historical
            'FIC043000': ['Literature & Fiction', 'LGBTQ+'],  # LGBTQ
            
            # Biography & Autobiography -> Biographies & Memoirs
            'BIO026000': ['Biographies & Memoirs', 'Specific Groups', 'LGBTQ+'],  # LGBT
            'BIO000000': ['Biographies & Memoirs'],  # General Biography
            'BIO001000': ['Biographies & Memoirs', 'Artists, Architects, Photographers'],  # Artists
            
            # Social Science -> Politics & Social Sciences
            'SOC026000': ['Politics & Social Sciences', 'Sociology', 'Gender Studies'],  # Gender Studies
            'SOC005000': ['Politics & Social Sciences', 'Anthropology'],  # Anthropology
            'SOC004000': ['Politics & Social Sciences', 'Sociology'],  # Sociology
            'SOC021000': ['Politics & Social Sciences', 'Social Sciences'],  # Communication & Media
            'SOC002000': ['Politics & Social Sciences', 'Sociology'],  # Sociology General
            'SOC050000': ['Politics & Social Sciences', 'LGBTQ+ Studies'],  # LGBTQ Studies
            
            # Family & Relationships -> Parenting & Relationships
            'FAM024000': ['Parenting & Relationships', 'Family Relationships'],  # Family
            'FAM034000': ['Parenting & Relationships', 'Love & Romance'],  # Marriage
            'FAM030000': ['Parenting & Relationships', 'Marriage'],  # Marriage
            'FAM054000': ['Parenting & Relationships', 'Love & Romance'],  # Love & Romance
            
            # Health, Fitness & Dieting
            'HEA024000': ['Health, Fitness & Dieting', "Women's Health"],  # Women's Health
            'HEA000000': ['Health, Fitness & Dieting'],  # General Health
            'HEA047000': ['Health, Fitness & Dieting', 'Sexual Health'],  # Sexual Health
            
            # Humor & Entertainment
            'HUM003000': ['Humor & Entertainment', 'Parodies'],  # Parodies
            'HUM000000': ['Humor & Entertainment'],  # General Humor
            
            # Performing Arts -> Arts & Photography
            'PER024000': ['Arts & Photography', 'Performing Arts', 'Theater'],  # Theater
            'PER000000': ['Arts & Photography', 'Performing Arts'],  # Performing Arts
            
            # Self-Help
            'SEL000000': ['Self-Help'],  # General Self-Help
            'SEL031000': ['Self-Help', 'Sexual Instruction'],  # Sexual Instruction
            'SEL027000': ['Self-Help', 'Personal Growth'],  # Personal Growth
            
            # Business & Money
            'BUS000000': ['Business & Money'],  # General Business
            'BUS071000': ['Business & Money', 'Leadership'],  # Leadership
            
            # Reference
            'REF000000': ['Reference'],  # General Reference
            'REF013000': ['Reference', 'Almanacs & Yearbooks'],  # Almanacs
            
            # Default fallback
            'DEFAULT': ['Literature & Fiction']
        }
        
        return bisac_mapping
    
    def convert_to_json(self, output_path: str = "kdp_categories.json"):
        """Convert categories to comprehensive JSON format"""
        
        print("Building category structures...")
        
        # Build all structures
        hierarchical_tree = self.build_hierarchical_structure()
        lookup_tables = self.build_lookup_tables()
        bisac_mapping = self.create_bisac_mapping()
        
        # Create comprehensive JSON structure
        categories_json = {
            'metadata': {
                'source_file': self.excel_file_path,
                'total_categories': len(self.categories_df),
                'generated_at': pd.Timestamp.now().isoformat(),
                'description': 'Amazon KDP Categories converted from Excel to JSON for automation'
            },
            
            'hierarchical_tree': hierarchical_tree,
            'lookup_tables': lookup_tables,
            'bisac_mapping': bisac_mapping,
            
            # Flat list for easy iteration
            'categories_flat': []
        }
        
        # Add flat list
        for _, row in self.categories_df.iterrows():
            path_components = self.clean_category_path(row['Category Path'])
            
            category_flat = {
                'overallIndex': int(row['overallIndex']) if pd.notna(row['overallIndex']) else None,
                'name': str(row['name']) if pd.notna(row['name']) else None,
                'browseNodeID': str(row['browseNodeID']) if pd.notna(row['browseNodeID']) else None,
                'level': int(row['Level']) if pd.notna(row['Level']) else None,
                'categoryPath': path_components,
                'categoryPathString': ' > '.join(path_components) if path_components else '',
                'parentName': str(row['parentName']) if pd.notna(row['parentName']) else None,
                'parentBrowseNodeID': str(row['parentBrowseNodeID']) if pd.notna(row['parentBrowseNodeID']) else None,
                'topLevelCategoryName': str(row['topLevelCategoryName']) if pd.notna(row['topLevelCategoryName']) else None,
                'fullName': str(row['fullName']) if pd.notna(row['fullName']) else None,
                'alsoKnownAs': str(row['alsoKnownAs']) if pd.notna(row['alsoKnownAs']) else None,
                'book1Rank': int(row['Book1Rank']) if pd.notna(row['Book1Rank']) else None,
                'book100Rank': int(row['Book100Rank']) if pd.notna(row['Book100Rank']) else None,
                'nLast30Days': int(row['nLast30Days']) if pd.notna(row['nLast30Days']) else None
            }
            
            categories_json['categories_flat'].append(category_flat)
        
        # Save to JSON file
        print(f"Saving to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(categories_json, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully converted {len(self.categories_df)} categories to JSON")
        
        # Print some statistics
        self.print_conversion_stats(categories_json)
        
        return categories_json
    
    def print_conversion_stats(self, categories_json: Dict):
        """Print conversion statistics"""
        print("\n" + "="*60)
        print("CONVERSION STATISTICS")
        print("="*60)
        
        print(f"Total categories: {categories_json['metadata']['total_categories']}")
        
        # Count by level
        level_counts = {}
        for cat in categories_json['categories_flat']:
            level = cat['level']
            if level:
                level_counts[level] = level_counts.get(level, 0) + 1
        
        print("\nCategories by level:")
        for level in sorted(level_counts.keys()):
            print(f"  Level {level}: {level_counts[level]} categories")
        
        # Count by top level category
        top_level_counts = {}
        for cat in categories_json['categories_flat']:
            top_level = cat['topLevelCategoryName']
            if top_level:
                top_level_counts[top_level] = top_level_counts.get(top_level, 0) + 1
        
        print(f"\nTop level categories ({len(top_level_counts)}):")
        for top_level, count in sorted(top_level_counts.items()):
            print(f"  {top_level}: {count} subcategories")
        
        print(f"\nBISAC mappings: {len(categories_json['bisac_mapping'])} codes mapped")
        print(f"Lookup tables: {len(categories_json['lookup_tables'])} tables created")
        
        print("="*60)

def main():
    """Main function"""
    
    # Input file path - update this to your Excel file location
    excel_file = "ebooks_us_category_list_2024-06-03.xlsx"
    output_file = "kdp_categories.json"
    
    # Check if input file exists
    if not Path(excel_file).exists():
        print(f"Error: Excel file not found: {excel_file}")
        print("Please update the excel_file variable with the correct path")
        return
    
    try:
        # Convert categories
        converter = KDPCategoryConverter(excel_file)
        categories_json = converter.convert_to_json(output_file)
        
        print(f"\nSUCCESS: Categories converted to {output_file}")
        print("\nYou can now use this JSON file in your KDP automation!")
        print("\nExample usage:")
        print("```python")
        print("import json")
        print("with open('kdp_categories.json', 'r') as f:")
        print("    categories = json.load(f)")
        print("```")
        
    except Exception as e:
        print(f"ERROR: Conversion failed: {e}")

if __name__ == "__main__":
    main()