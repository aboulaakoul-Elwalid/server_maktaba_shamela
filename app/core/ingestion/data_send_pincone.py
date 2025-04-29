# import os
# import json
# import glob
# import pandas as pd
# from tqdm import tqdm
# from dotenv import load_dotenv
# from pinecone import Pinecone
# import sys

# # Load environment variables from .env file
# load_dotenv()

# # Configuration
# BATCH_SIZE = 100  # Batch size for uploading to Pinecone
# PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# # Set the category name here - change this to the category you want to process
# CATEGORY_NAME = "السيرة_النبوية"  # Replace with your chosen category name

# # Base directories for JSON and embeddings
# JSON_BASE_DIR = "../data/second_iteration"  # Update this to your JSON files directory
# EMBEDDINGS_BASE_DIR = "../data/csv_embeddings"  # Update this to your embeddings directory

# # Construct paths based on the category name
# JSON_FILE_PATH = os.path.join(JSON_BASE_DIR, f"{CATEGORY_NAME}_processed_processed.json")
# EMBEDDINGS_DIR = os.path.join(EMBEDDINGS_BASE_DIR, CATEGORY_NAME)

# def process_category(json_path, embeddings_dir, category_name, index):
#     """Process the JSON and embeddings for the given category and upload vectors to Pinecone."""
#     print(f"Starting processing for category: {category_name}")
#     print(f"JSON file: {json_path}")
#     print(f"Embeddings directory: {embeddings_dir}")
    
#     # Check if JSON file exists
#     if not os.path.exists(json_path):
#         print(f"ERROR: JSON file not found at: {json_path}")
#         available_json = [f for f in os.listdir(JSON_BASE_DIR) if f.endswith("_processed_processed.json")]
#         if available_json:
#             print("Available JSON files in the directory:")
#             for f in available_json:
#                 print(f" - {f}")
#         else:
#             print("No JSON files found in the directory.")
#         sys.exit(1)
    
#     # Find all CSV embedding files
#     embeddings_files = glob.glob(os.path.join(embeddings_dir, "*.csv"))
#     if not embeddings_files:
#         print(f"ERROR: No embedding CSV files found in: {embeddings_dir}")
#         sys.exit(1)
    
#     print(f"Found JSON file: {json_path}")
#     print(f"Found {len(embeddings_files)} embedding files")
    
#     # Load JSON data
#     print(f"Loading JSON data from {json_path}...")
#     with open(json_path, "r", encoding="utf-8") as f:
#         books = json.load(f)
#     print(f"Loaded {len(books)} books from JSON")
    
#     # Load and concatenate embeddings
#     print(f"Loading embeddings from {len(embeddings_files)} CSV files...")
#     all_embeddings = []

#     for file in embeddings_files:
#         print(f"Processing file: {file}")
#         df = pd.read_csv(file)
        
#         # Get the name of the first column (assumes embeddings are in first column)
#         embedding_col = df.columns[0]
        
#         # Convert string representations of lists to actual lists of floats
#         for idx, row in df.iterrows():
#             try:
#                 # Extract the string, remove brackets, split by comma, and convert to float
#                 embedding_str = row[embedding_col]
#                 if isinstance(embedding_str, str):
#                     # Remove brackets and split by comma
#                     values = embedding_str.strip('[]').split(',')
#                     # Convert to float
#                     embedding = [float(val.strip()) for val in values]
#                     all_embeddings.append(embedding)
#                 else:
#                     print(f"Warning: Non-string value found at row {idx}: {embedding_str}")
#             except Exception as e:
#                 print(f"Error processing row {idx}: {e}")
#                 print(f"Value was: {row[embedding_col]}")

#     embeddings = all_embeddings
#     print(f"Loaded {len(embeddings)} embeddings")
    
#     # Extract text chunks from JSON
#     print(f"Extracting text chunks...")
#     all_texts = []
#     for book in books:
#         book_id = book.get("book_id", "unknown")
#         book_title = book.get("title", "unknown")
        
#         # Check if this book has sections
#         if "sections" in book and book["sections"]:
#             # Process books with sections
#             for section in book["sections"]:
#                 section_id = section.get("section_id", "unknown")
#                 text = section.get("text", "")
#                 all_texts.append({
#                     "book_id": book_id,
#                     "book_title": book_title,
#                     "section_id": section_id,
#                     "text": text
#                 })
#         else:
#             # Process books without sections (treat the book itself as a section)
#             section_id = book.get("section_id", f"{book_id}_0_0_0_0")
#             text = book.get("text", "")
#             if text:  # Only add if there's text content
#                 all_texts.append({
#                     "book_id": book_id,
#                     "book_title": book_title,
#                     "section_id": section_id,
#                     "text": text
#                 })
#                 print(f"Added book {book_id} as a direct text chunk")
#             else:
#                 print(f"WARNING: Book {book_id} has no sections and no text content")
                
#     print(f"Extracted {len(all_texts)} text chunks")
    
#     # Check alignment between text chunks and embeddings
#     if len(all_texts) != len(embeddings):
#         print(f"WARNING: Mismatch - {len(all_texts)} text chunks vs {len(embeddings)} embeddings")
#         min_len = min(len(all_texts), len(embeddings))
#         print(f"Adjusting to {min_len} items")
#         all_texts = all_texts[:min_len]
#         embeddings = embeddings[:min_len]
    
#     # Prepare vectors for Pinecone
#     print(f"Preparing vectors for upload...")
#     vectors = []
#     for text_item, embedding in zip(all_texts, embeddings):
#         vector_id = f"{category_name.lower()}_{text_item['book_id']}_{text_item['section_id']}"
#         text = text_item["text"]
#         if len(text.encode('utf-8')) > 40000:  # Pinecone metadata size limit
#             print(f"WARNING: Text for {vector_id} exceeds size limit, truncating...")
#             text = text[:10000]  # Truncate to a safe length
        
#         metadata = {
#             "book_id": text_item["book_id"],
#             "book_title": text_item["book_title"],
#             "section_id": text_item["section_id"],
#             "text": text,
#             "category": category_name
#         }
        
#         vectors.append({
#             "id": vector_id,
#             "values": embedding,
#             "metadata": metadata
#         })
#     print(f"Prepared {len(vectors)} vectors")
    
#     # Upload vectors to Pinecone in batches
#     print(f"Uploading {len(vectors)} vectors in batches of {BATCH_SIZE}...")
#     for i in tqdm(range(0, len(vectors), BATCH_SIZE), desc="Uploading batches"):
#         batch = vectors[i:i + BATCH_SIZE]
#         try:
#             index.upsert(vectors=batch)
#             print(f"Uploaded batch {i // BATCH_SIZE + 1} with {len(batch)} vectors")
#         except Exception as e:
#             print(f"ERROR: Failed to upload batch {i // BATCH_SIZE + 1}: {e}")
    
#     print(f"Completed processing for category: {category_name}")

# def main():
#     # Validate environment variables
#     if not PINECONE_API_KEY or not PINECONE_INDEX_NAME:
#         print("ERROR: Missing PINECONE_API_KEY or PINECONE_INDEX_NAME in .env file")
#         sys.exit(1)
    
#     # Initialize Pinecone
#     print(f"Connecting to Pinecone index: {PINECONE_INDEX_NAME}")
#     pc = Pinecone(api_key=PINECONE_API_KEY)
#     index = pc.Index(PINECONE_INDEX_NAME)
    
#     # Process the hardcoded category
#     process_category(JSON_FILE_PATH, EMBEDDINGS_DIR, CATEGORY_NAME, index)

# if __name__ == "__main__":
#     main()