#!/usr/bin/env python3
"""
KDP File Preparation and Organization Script
"""

import pandas as pd
import os
import shutil
import time
import schedule
from datetime import datetime
import logging
from pathlib import Path
import json

class KDPFileManager:
    def __init__(self, csv_file_path, output_directory="./prepared_books"):
        """
        Initialize the KDP File Manager
        
        Args:
            csv_file_path (str): Path to the CSV file with book metadata
            output_directory (str): Directory to organize prepared files
        """
        self.csv_file_path = csv_file_path
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        self.processed_books = set()
        
        # Setup logging directory
        self.setup_logging()
        
        # Load book data
        self.load_book_data()
    
    def setup_logging(self):
        """Setup logging with logs directory"""
        logs_dir = Path("./logs")
        logs_dir.mkdir(exist_ok=True)
        
        log_file = logs_dir / f"kdp_preparation_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ],
            force=True  # Override any existing logging config
        )
        
    def load_book_data(self):
        """Load book metadata from CSV file"""
        try:
            # Handle different file formats
            if self.csv_file_path.endswith('.xlsx'):
                self.books_df = pd.read_excel(self.csv_file_path)
            else:
                self.books_df = pd.read_csv(self.csv_file_path, sep=';')
            
            logging.info(f"Loaded {len(self.books_df)} books from {self.csv_file_path}")
            
        except Exception as e:
            logging.error(f"Error loading book data: {e}")
            raise
    
    def clean_file_path(self, file_path):
        """Clean file path by removing extra quotes"""
        if file_path and isinstance(file_path, str):
            return file_path.strip().strip('"""').strip('"')
        return file_path
    
    def convert_to_json_safe(self, value):
        """Convert numpy types to JSON-safe Python types"""
        if pd.isna(value):
            return None
        if hasattr(value, 'item'):  # numpy types
            return value.item()
        return value
    
    def prepare_book_files(self, book_index):
        """
        Prepare files for a single book
        
        Args:
            book_index (int): Index of the book in the dataframe
        """
        book = self.books_df.iloc[book_index]
        book_title = str(book['title']).replace(' ', '_').replace('/', '_').replace('\\', '_')
        
        # Create book directory
        book_dir = self.output_directory / f"book_{book_index:03d}_{book_title}"
        book_dir.mkdir(exist_ok=True)
        
        logging.info(f"Preparing book: {book['title']}")
        
        # File paths to copy
        files_to_copy = {
            'ebook_cover': self.clean_file_path(book['eBook-Cover']),
            'print_cover': self.clean_file_path(book['Print-Cover']),
            'epub': self.clean_file_path(book['epub']),
            'docx': self.clean_file_path(book['docx'])
        }
        
        # Copy files to organized directory
        copied_files = {}
        for file_type, source_path in files_to_copy.items():
            if source_path and os.path.exists(source_path):
                file_extension = Path(source_path).suffix
                dest_filename = f"{book_title}_{file_type}{file_extension}"
                dest_path = book_dir / dest_filename
                
                try:
                    shutil.copy2(source_path, dest_path)
                    copied_files[file_type] = str(dest_path)
                    logging.info(f"Copied {file_type}: {dest_filename}")
                except Exception as e:
                    logging.error(f"Error copying {file_type}: {e}")
            else:
                logging.warning(f"File not found for {file_type}: {source_path}")
        
        # Create metadata file with JSON-safe data
        metadata = {
            'title': str(book['title']),
            'subtitle': str(book['subtitle']) if pd.notna(book['subtitle']) else None,
            'author': str(book['author']),
            'description_html': str(book['description_html']),
            'keywords': str(book['keywords']),
            'language': str(book['language']),
            'bisac': str(book['bisac']),
            'age_min': self.convert_to_json_safe(book['age_min']),
            'age_max': self.convert_to_json_safe(book['age_max']),
            'trim_size': str(book['trim_size']),
            'paper_color': str(book['paper_color']),
            'cover_finish': str(book['cover_finish']),
            'price_print_eur': self.convert_to_json_safe(book['price_print_eur']) / 100,  
            'price_print_usd': self.convert_to_json_safe(book['price_print_usd']) / 100,
            'price_ebook_eur': self.convert_to_json_safe(book['price_ebook_eur']) / 100,
            'price_ebook_usd': self.convert_to_json_safe(book['price_ebook_usd']) / 100,
            'files': copied_files,
            'prepared_at': datetime.now().isoformat()
        }
        
        # Save metadata as JSON
        metadata_file = book_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Created metadata file: {metadata_file}")
        return book_dir
    
    def get_next_books_to_process(self, count=3):
        """
        Get the next books to process (those not yet processed)
        
        Args:
            count (int): Number of books to process
            
        Returns:
            list: List of book indices to process
        """
        available_books = []
        for i in range(len(self.books_df)):
            if i not in self.processed_books:
                available_books.append(i)
                if len(available_books) >= count:
                    break
        
        return available_books
    
    def process_daily_batch(self):
        """Process the daily batch of 3 books"""
        try:
            books_to_process = self.get_next_books_to_process(3)
            
            if not books_to_process:
                logging.info("No more books to process")
                return
            
            logging.info(f"Processing daily batch: {len(books_to_process)} books")
            
            prepared_dirs = []
            for book_index in books_to_process:
                book_dir = self.prepare_book_files(book_index)
                prepared_dirs.append(book_dir)
                self.processed_books.add(book_index)
            
            # Create a batch summary with JSON-safe data
            batch_summary = {
                'processed_at': datetime.now().isoformat(),
                'books_processed': [int(x) for x in books_to_process],  # Convert to regular int
                'prepared_directories': [str(d) for d in prepared_dirs],
                'remaining_books': int(len(self.books_df) - len(self.processed_books))
            }
            
            summary_file = self.output_directory / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(summary_file, 'w') as f:
                json.dump(batch_summary, f, indent=2)
            
            logging.info(f"Daily batch completed. {batch_summary['remaining_books']} books remaining.")
            
            # IMPORTANT: Manual upload reminder
            print("\n" + "="*60)
            print("READY FOR MANUAL UPLOAD")
            print("="*60)
            for i, book_index in enumerate(books_to_process):
                book_title = self.books_df.iloc[book_index]['title']
                print(f"{i+1}. {book_title}")
                print(f"   Directory: {prepared_dirs[i]}")
            print("\nPlease upload these books manually to KDP")
            print("Files are organized and metadata is prepared in JSON format")
            print("="*60)
            
        except Exception as e:
            logging.error(f"Error in daily batch processing: {e}")
            raise

def main():
    """Main function to set up and run the automation"""
    
    # Configuration - Change this to 'metadata_test.csv' for testing
    CSV_FILE = "metadata_test.csv"  # Change to "metadata_test.csv" for testing
    OUTPUT_DIR = "./prepared_books"
    
    # Verify CSV file exists
    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file '{CSV_FILE}' not found!")
        print("Please update the CSV_FILE variable with the correct path.")
        print("For testing, run: python create_test_environment.py first")
        return
    
    # Initialize the file manager
    kdp_manager = KDPFileManager(CSV_FILE, OUTPUT_DIR)
    
    # Schedule daily processing at 9:00 AM
    schedule.every().day.at("09:00").do(kdp_manager.process_daily_batch)
    
    print("KDP File Preparation Scheduler Started")
    print("=" * 50)
    print(f"CSV File: {CSV_FILE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Total Books: {len(kdp_manager.books_df)}")
    print("Scheduled: Every day at 09:00")
    print("=" * 50)
    print("\nPress Ctrl+C to stop the scheduler")
    
    # Run one batch immediately for testing
    print("\nRunning initial batch...")
    kdp_manager.process_daily_batch()
    
    # Keep the scheduler running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\nScheduler stopped by user")

if __name__ == "__main__":
    main()