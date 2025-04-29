"""
Shamela Robust Dataset Preparation
==================================
This script implements the step-by-step plan for creating a unified dataset from Shamela resources.
It creates a new SQLite database with enhanced metadata and structure.

Usage:
    python prepare_robust_dataset.py

The script will create:
- shamela_robust.db: Main dataset database
- missing_content.txt: List of books without content
- missing_structure.txt: List of books without structure
- category_hierarchy.txt: Category parent-child mappings
- metadata_enrichment_plan.txt: Future enrichment strategies
- validation_report.txt: Summary of dataset validation
"""

import os
import sqlite3
import json
import sys
from pathlib import Path
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("shamela_prepare.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Shamela")

# Constants
OUTPUT_DB = "shamela_robust.db"
MASTER_DB = r"c:\shamela4\database\master.db"
KIZANA_ALL_BOOKS = r"c:\shamela4\kizana_all_books\kizana_all_books.db"  # This path may need adjustment
MISSING_CONTENT_FILE = "missing_content.txt"
MISSING_STRUCTURE_FILE = "missing_structure.txt"
CATEGORY_HIERARCHY_FILE = "category_hierarchy.txt"
METADATA_ENRICHMENT_PLAN_FILE = "metadata_enrichment_plan.txt"
VALIDATION_REPORT_FILE = "validation_report.txt"

def initialize_database():
    """Step 1: Initialize the Dataset Database"""
    logger.info("Step 1: Initializing the dataset database")
    
    if os.path.exists(OUTPUT_DB):
        logger.info(f"Removing existing database: {OUTPUT_DB}")
        os.remove(OUTPUT_DB)
    
    conn = sqlite3.connect(OUTPUT_DB)
    logger.info(f"Created new database: {OUTPUT_DB}")
    return conn

def define_books_table(conn):
    """Step 2: Define the Books Table"""
    logger.info("Step 2: Defining the books table")
    
    cursor = conn.cursor()
    
    # Create enhanced books table
    cursor.execute('''
    CREATE TABLE books (
        book_id INTEGER PRIMARY KEY,
        book_name TEXT,
        category_id INTEGER,
        main_author TEXT,
        book_date TEXT,
        pdf_links TEXT,
        publication_date TEXT,
        summary TEXT,
        keywords TEXT,
        edition TEXT,
        publisher TEXT,
        isbn TEXT
    )
    ''')
    
    # Copy data from master.db
    master_conn = sqlite3.connect(MASTER_DB)
    master_cursor = master_conn.cursor()
    
    # First, let's check what tables actually exist in the master database
    master_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = master_cursor.fetchall()
    logger.info(f"Tables in master database: {[t[0] for t in tables]}")
    
    # Look for a table that might contain book data
    book_table_name = None
    for table in tables:
        table_name = table[0]
        if table_name.lower() in ['book', 'books', 'main', 'books_info', 'bk']:
            book_table_name = table_name
            break
    
    if not book_table_name:
        # If no obvious book table is found, use the first table (or handle accordingly)
        if tables:
            book_table_name = tables[0][0]
            logger.warning(f"No obvious book table found. Using first table: {book_table_name}")
        else:
            logger.error("No tables found in master database!")
            return 0
    
    # Get table structure
    master_cursor.execute(f"PRAGMA table_info({book_table_name})")
    columns = master_cursor.fetchall()
    logger.info(f"Columns in {book_table_name}: {[col[1] for col in columns]}")
    
    # Get column indices based on actual column names
    column_names = [col[1] for col in columns]
    
    # Try to map column names to our expected fields
    book_id_col = next((col for col in column_names if col.lower() in ['id', 'book_id', 'bookid']), None)
    book_name_col = next((col for col in column_names if col.lower() in ['name', 'book_name', 'title']), None)
    category_id_col = next((col for col in column_names if col.lower() in ['cat', 'category', 'category_id']), None)
    main_author_col = next((col for col in column_names if col.lower() in ['authno', 'author', 'author_id']), None)
    book_date_col = next((col for col in column_names if col.lower() in ['betaka', 'date', 'book_date']), None)
    pdf_links_col = next((col for col in column_names if col.lower() in ['pdf', 'pdf_links', 'pdflink']), None)
    
    # Verify we found needed columns
    if not (book_id_col and book_name_col):
        logger.error(f"Required columns not found in {book_table_name}!")
        return 0
    
    # Get column indices
    book_id_idx = column_names.index(book_id_col)
    book_name_idx = column_names.index(book_name_col)
    category_id_idx = column_names.index(category_id_col) if category_id_col else -1
    main_author_idx = column_names.index(main_author_col) if main_author_col else -1
    book_date_idx = column_names.index(book_date_col) if book_date_col else -1
    pdf_links_idx = column_names.index(pdf_links_col) if pdf_links_col else -1
    
    # Fetch the data
    master_cursor.execute(f"SELECT * FROM {book_table_name}")
    books = master_cursor.fetchall()
    
    # Insert into our new table with proper error handling
    for book in books:
        # Prepare values with None for missing columns
        book_id = book[book_id_idx] if book_id_idx >= 0 else None
        book_name = book[book_name_idx] if book_name_idx >= 0 else None
        category_id = book[category_id_idx] if category_id_idx >= 0 and category_id_idx < len(book) else None
        main_author = book[main_author_idx] if main_author_idx >= 0 and main_author_idx < len(book) else None
        book_date = book[book_date_idx] if book_date_idx >= 0 and book_date_idx < len(book) else None
        pdf_links = book[pdf_links_idx] if pdf_links_idx >= 0 and pdf_links_idx < len(book) else None
        
        cursor.execute('''
        INSERT INTO books (
            book_id, book_name, category_id, main_author, book_date, pdf_links,
            publication_date, summary, keywords, edition, publisher, isbn
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL)
        ''', (
            
            
            
            
            book_id, book_name, category_id, main_author, book_date, pdf_links
        ))
    
    master_conn.close()
    
    # Commit changes
    conn.commit()
    
    # Count books
    cursor.execute("SELECT COUNT(*) FROM books")
    book_count = cursor.fetchone()[0]
    logger.info(f"Imported {book_count} books into the books table")
    
    return book_count

def define_authors_table(conn):
    """Step 3: Define the Authors Table"""
    logger.info("Step 3: Defining the authors table")
    
    cursor = conn.cursor()
    
    # Create enhanced authors table
    cursor.execute('''
    CREATE TABLE authors (
        author_id INTEGER PRIMARY KEY,
        author_name TEXT,
        death_number INTEGER,
        death_text TEXT,
        birth_date TEXT,
        death_date TEXT,
        nationality TEXT,
        school_of_thought TEXT
    )
    ''')
    
    # Copy data from master.db
    master_conn = sqlite3.connect(MASTER_DB)
    master_cursor = master_conn.cursor()
    
    master_cursor.execute("SELECT * FROM author")
    authors = master_cursor.fetchall()
    
    column_names = [desc[0] for desc in master_cursor.description]
    author_id_idx = column_names.index("id") if "id" in column_names else 0
    author_name_idx = column_names.index("name") if "name" in column_names else 1
    death_number_idx = column_names.index("death") if "death" in column_names else 2
    death_text_idx = column_names.index("info") if "info" in column_names else 3
    
    for author in authors:
        cursor.execute('''
        INSERT INTO authors (
            author_id, author_name, death_number, death_text,
            birth_date, death_date, nationality, school_of_thought
        ) VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL)
        ''', (
            author[author_id_idx], author[author_name_idx],
            author[death_number_idx], author[death_text_idx]
        ))
    
    master_conn.close()
    
    # Commit changes
    conn.commit()
    
    # Count authors
    cursor.execute("SELECT COUNT(*) FROM authors")
    author_count = cursor.fetchone()[0]
    logger.info(f"Imported {author_count} authors into the authors table")
    
    return author_count

def define_categories_table(conn):
    """Step 4: Define the Categories Table"""
    logger.info("Step 4: Defining the categories table")
    
    cursor = conn.cursor()
    
    # Create enhanced categories table
    cursor.execute('''
    CREATE TABLE categories (
        category_id INTEGER PRIMARY KEY,
        category_name TEXT,
        category_order INTEGER,
        parent_category_id INTEGER NULL
    )
    ''')
    
    # Copy data from master.db
    master_conn = sqlite3.connect(MASTER_DB)
    master_cursor = master_conn.cursor()
    
    master_cursor.execute("SELECT * FROM category")
    categories = master_cursor.fetchall()
    
    column_names = [desc[0] for desc in master_cursor.description]
    category_id_idx = column_names.index("id") if "id" in column_names else 0
    category_name_idx = column_names.index("name") if "name" in column_names else 1
    category_order_idx = column_names.index("catord") if "catord" in column_names else 2
    
    for category in categories:
        cursor.execute('''
        INSERT INTO categories (
            category_id, category_name, category_order, parent_category_id
        ) VALUES (?, ?, ?, NULL)
        ''', (
            category[category_id_idx], category[category_name_idx], category[category_order_idx]
        ))
    
    master_conn.close()
    
    # Create category hierarchy mapping file with placeholder text
    with open(CATEGORY_HIERARCHY_FILE, 'w', encoding='utf-8') as f:
        f.write("# Category Hierarchy Mapping\n\n")
        f.write("# Format: child_category_id|parent_category_id|child_name|parent_name\n\n")
        
        # List all categories for manual mapping
        cursor.execute("SELECT category_id, category_name FROM categories ORDER BY category_id")
        for category in cursor.fetchall():
            f.write(f"{category[0]}|NULL|{category[1]}|\n")
    
    # Commit changes
    conn.commit()
    
    # Count categories
    cursor.execute("SELECT COUNT(*) FROM categories")
    category_count = cursor.fetchone()[0]
    logger.info(f"Imported {category_count} categories into the categories table")
    logger.info(f"Created category hierarchy mapping file: {CATEGORY_HIERARCHY_FILE}")
    
    return category_count

def extract_content_tables(conn):
    """Step 5: Extract Content Tables"""
    logger.info("Step 5: Extracting content tables")
    
    cursor = conn.cursor()
    
    # Get all book_ids
    cursor.execute("SELECT book_id FROM books")
    book_ids = [row[0] for row in cursor.fetchall()]
    
    # Target paths for content DBs
    db_path_template = r"c:\shamela4\database\book\{dir_name}\{file_name}.db"
    missing_content = []
    
    total_tables = 0
    
    for book_id in book_ids:
        # For directory name, use 3-digit format with leading zeros
        dir_name = f"{book_id:03d}"[:3]
        
        # Try to find matching DB file in the directory
        target_dir = os.path.join(r"c:\shamela4\database\book", dir_name)
        
        if not os.path.exists(target_dir):
            missing_content.append(book_id)
            continue
            
        found = False
        
        # Check all possible DB files for this book
        for file_name in os.listdir(target_dir):
            if file_name.endswith('.db') and file_name.rstrip('.db').endswith(str(book_id)):
                source_db_path = os.path.join(target_dir, file_name)
                
                # Connect to source db
                try:
                    source_conn = sqlite3.connect(source_db_path)
                    source_cursor = source_conn.cursor()
                    
                    # Check if the book content table exists
                    table_name = f"b{book_id}"
                    source_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                    if source_cursor.fetchone():
                        # Create new content table with enhanced schema
                        cursor.execute(f'''
                        CREATE TABLE IF NOT EXISTS b{book_id} (
                            chunk_id INTEGER PRIMARY KEY,
                            content TEXT,
                            part INTEGER,
                            page INTEGER,
                            number INTEGER,
                            services TEXT,
                            is_deleted INTEGER,
                            section_title TEXT NULL,
                            citations TEXT NULL
                        )
                        ''')
                        
                        # Copy data
                        source_cursor.execute(f"SELECT * FROM b{book_id}")
                        rows = source_cursor.fetchall()
                        
                        column_names = [desc[0] for desc in source_cursor.description]
                        id_idx = column_names.index("id") if "id" in column_names else 0
                        content_idx = column_names.index("nass") if "nass" in column_names else 1
                        part_idx = column_names.index("part") if "part" in column_names else 2
                        page_idx = column_names.index("page") if "page" in column_names else 3
                        number_idx = column_names.index("id") if "number" not in column_names else column_names.index("number")
                        services_idx = column_names.index("services") if "services" in column_names else -1
                        is_deleted_idx = column_names.index("isdeleted") if "isdeleted" in column_names else -1
                        
                        for row in rows:
                            services_value = row[services_idx] if services_idx >= 0 and services_idx < len(row) else None
                            is_deleted_value = row[is_deleted_idx] if is_deleted_idx >= 0 and is_deleted_idx < len(row) else 0
                            
                            cursor.execute(f'''
                            INSERT INTO b{book_id} (
                                chunk_id, content, part, page, number, services, is_deleted,
                                section_title, citations
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                            ''', (
                                row[id_idx], row[content_idx], row[part_idx], row[page_idx],
                                row[number_idx], services_value, is_deleted_value
                            ))
                        
                        total_tables += 1
                        found = True
                        
                    source_conn.close()
                    
                except sqlite3.Error as e:
                    logger.error(f"Error processing book {book_id} from {source_db_path}: {e}")
                
                # Break if we found and processed the table
                if found:
                    break
                    
        if not found:
            missing_content.append(book_id)
    
    # Write missing content list
    with open(MISSING_CONTENT_FILE, 'w', encoding='utf-8') as f:
        for book_id in missing_content:
            f.write(f"{book_id}\n")
    
    # Commit changes
    conn.commit()
    
    logger.info(f"Extracted {total_tables} content tables")
    logger.info(f"Found {len(missing_content)} books without content tables")
    logger.info(f"Missing content list written to: {MISSING_CONTENT_FILE}")
    
    return total_tables, missing_content

def extract_structure_tables(conn):
    """Step 6: Extract Structure Tables"""
    logger.info("Step 6: Extracting structure tables")
    
    cursor = conn.cursor()
    
    # Get all book_ids
    cursor.execute("SELECT book_id FROM books")
    book_ids = [row[0] for row in cursor.fetchall()]
    
    # Target paths for structure DBs
    db_path_template = r"c:\shamela4\database\book\{dir_name}\{file_name}.db"
    missing_structure = []
    
    total_tables = 0
    
    for book_id in book_ids:
        # For directory name, use 3-digit format with leading zeros
        dir_name = f"{book_id:03d}"[:3]
        
        # Try to find matching DB file in the directory
        target_dir = os.path.join(r"c:\shamela4\database\book", dir_name)
        
        if not os.path.exists(target_dir):
            missing_structure.append(book_id)
            continue
            
        found = False
        
        # Check all possible DB files for this book
        for file_name in os.listdir(target_dir):
            if file_name.endswith('.db') and file_name.rstrip('.db').endswith(str(book_id)):
                source_db_path = os.path.join(target_dir, file_name)
                
                # Connect to source db
                try:
                    source_conn = sqlite3.connect(source_db_path)
                    source_cursor = source_conn.cursor()
                    
                    # Check if the book structure table exists
                    table_name = f"t{book_id}"
                    source_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                    if source_cursor.fetchone():
                        # Create new structure table with enhanced schema
                        cursor.execute(f'''
                        CREATE TABLE IF NOT EXISTS t{book_id} (
                            section_id INTEGER PRIMARY KEY,
                            section_title TEXT,
                            page INTEGER,
                            parent_section_id INTEGER,
                            is_deleted INTEGER
                        )
                        ''')
                        
                        # Copy data
                        source_cursor.execute(f"SELECT * FROM t{book_id}")
                        rows = source_cursor.fetchall()
                        
                        column_names = [desc[0] for desc in source_cursor.description]
                        id_idx = column_names.index("id") if "id" in column_names else 0
                        content_idx = column_names.index("tit") if "tit" in column_names else 1
                        page_idx = column_names.index("page") if "page" in column_names else 2
                        parent_idx = column_names.index("lvl") if "lvl" in column_names else 3
                        is_deleted_idx = column_names.index("isdeleted") if "isdeleted" in column_names else -1
                        
                        for row in rows:
                            is_deleted_value = row[is_deleted_idx] if is_deleted_idx >= 0 and is_deleted_idx < len(row) else 0
                            
                            cursor.execute(f'''
                            INSERT INTO t{book_id} (
                                section_id, section_title, page, parent_section_id, is_deleted
                            ) VALUES (?, ?, ?, ?, ?)
                            ''', (
                                row[id_idx], row[content_idx], row[page_idx], row[parent_idx], is_deleted_value
                            ))
                        
                        total_tables += 1
                        found = True
                        
                    source_conn.close()
                    
                except sqlite3.Error as e:
                    logger.error(f"Error processing book {book_id} from {source_db_path}: {e}")
                
                # Break if we found and processed the table
                if found:
                    break
                    
        if not found:
            missing_structure.append(book_id)
    
    # Write missing structure list
    with open(MISSING_STRUCTURE_FILE, 'w', encoding='utf-8') as f:
        for book_id in missing_structure:
            f.write(f"{book_id}\n")
    
    # Commit changes
    conn.commit()
    
    logger.info(f"Extracted {total_tables} structure tables")
    logger.info(f"Found {len(missing_structure)} books without structure tables")
    logger.info(f"Missing structure list written to: {MISSING_STRUCTURE_FILE}")
    
    return total_tables, missing_structure

def validate_dataset(conn, book_count, author_count, category_count, content_tables, structure_tables):
    """Step 7: Validate the Dataset"""
    logger.info("Step 7: Validating the dataset")
    
    cursor = conn.cursor()
    
    validation_results = []
    
    # Check book count
    cursor.execute("SELECT COUNT(*) FROM books")
    actual_book_count = cursor.fetchone()[0]
    validation_results.append(f"Books table: Expected {book_count}, Found {actual_book_count}")
    
    # Check author count
    cursor.execute("SELECT COUNT(*) FROM authors")
    actual_author_count = cursor.fetchone()[0]
    validation_results.append(f"Authors table: Expected {author_count}, Found {actual_author_count}")
    
    # Check category count
    cursor.execute("SELECT COUNT(*) FROM categories")
    actual_category_count = cursor.fetchone()[0]
    validation_results.append(f"Categories table: Expected {category_count}, Found {actual_category_count}")
    
    # Get count of content tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'b%' AND name NOT LIKE 'books'")
    actual_content_tables = len(cursor.fetchall())
    validation_results.append(f"Content tables: Expected {len(content_tables)}, Found {actual_content_tables}")
    
    # Get count of structure tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 't%'")
    actual_structure_tables = len(cursor.fetchall())
    validation_results.append(f"Structure tables: Expected {len(structure_tables)}, Found {actual_structure_tables}")
    
    # Sample test: Check that some book with PDF links has content
    cursor.execute("SELECT book_id, pdf_links FROM books WHERE pdf_links IS NOT NULL AND pdf_links != '' LIMIT 10")
    books_with_pdf = cursor.fetchall()
    
    for book_id, _ in books_with_pdf:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='b{book_id}'")
        has_content = cursor.fetchone() is not None
        validation_results.append(f"Book {book_id} with PDF: {'Has content table' if has_content else 'Missing content table'}")
    
    # Write validation report
    with open(VALIDATION_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Validation Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for result in validation_results:
            f.write(f"- {result}\n")
    
    logger.info(f"Validation report written to: {VALIDATION_REPORT_FILE}")
    
    return validation_results

def create_scalability_plan():
    """Step 8: Plan for Scalability"""
    logger.info("Step 8: Creating scalability plan")
    
    with open(METADATA_ENRICHMENT_PLAN_FILE, 'w', encoding='utf-8') as f:
        f.write("# Metadata Enrichment and Scalability Plan\n\n")
        
        f.write("## Future Database Migration\n\n")
        f.write("### PostgreSQL Migration\n")
        f.write("- Convert SQLite schema to PostgreSQL\n")
        f.write("- Use psycopg2 for Python connection\n")
        f.write("- Implement proper connection pooling\n")
        f.write("- Set up user roles and permissions\n\n")
        
        f.write("### Indexing Strategy\n")
        f.write("- Create indexes on book_id in all content tables\n")
        f.write("- Create indexes on category_id in the books table\n")
        f.write("- Create indexes on chunk_id in content tables\n")
        f.write("- Create full-text search indexes on content fields\n\n")
        
        f.write("### Table Partitioning\n")
        f.write("- Partition content tables by book_id ranges (e.g., b1-b1000, b1001-b2000)\n")
        f.write("- Implement horizontal sharding for very large tables\n")
        f.write("- Consider time-based partitioning for log and activity tables\n\n")
        
        f.write("### Vector Database Integration\n")
        f.write("- Implement Pinecone or other vector database for embeddings\n")
        f.write("- Store chunk_id reference in vector DB for content retrieval\n")
        f.write("- Create embeddings batch processing pipeline\n\n")
    
    logger.info(f"Scalability plan written to: {METADATA_ENRICHMENT_PLAN_FILE}")

def main():
    """Main execution function"""
    logger.info("Starting Shamela Robust Dataset preparation")
    
    # Step 1: Initialize the database
    conn = initialize_database()
    
    try:
        # Step 2: Define the Books Table
        book_count = define_books_table(conn)
        
        # Step 3: Define the Authors Table
        author_count = define_authors_table(conn)
        
        # Step 4: Define the Categories Table
        category_count = define_categories_table(conn)
        
        # Step 5: Extract Content Tables
        content_tables, missing_content = extract_content_tables(conn)
        
        # Step 6: Extract Structure Tables
        structure_tables, missing_structure = extract_structure_tables(conn)
        
        # Step 7: Validate the Dataset
        validate_dataset(conn, book_count, author_count, category_count,
                         content_tables, structure_tables)
        
        # Step 8: Create Scalability Plan
        create_scalability_plan()
        
        logger.info("Shamela Robust Dataset preparation completed successfully")
        
    except Exception as e:
        logger.error(f"Error during database preparation: {e}", exc_info=True)
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()