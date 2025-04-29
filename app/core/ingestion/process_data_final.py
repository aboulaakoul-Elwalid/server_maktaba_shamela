# import json
# import csv
# import logging
# import argparse
# import os

# # Set up basic logging to track what’s happening
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# def load_original_json(file_path):
#     """Load book metadata from the original JSON file."""
#     with open(file_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
    
#     # Assuming a single book for simplicity
#     if isinstance(data, list):
#         book = data[0]  # Take the first book
#     else:
#         book = data
    
#     book_info = {
#         book["book_id"]: {
#             "book_name": book["book_name"],
#             "author_name": book.get("author_name", "Unknown"),
#             "category_name": book.get("category_name", "No category")
#         }
#     }
#     return book_info

# def load_processed_json(file_path, target_book_id=None):
#     """Load section data from the processed JSON file, filtering by book_id."""
#     with open(file_path, 'r', encoding='utf-8') as f:
#         sections = json.load(f)

#     if target_book_id is None:
#         return sections  # Load all sections if no target_book_id is provided

#     filtered_sections = []
#     for section in sections:
#         if section.get('book_id') == target_book_id:
#             filtered_sections.append(section)

#     return filtered_sections

# def load_embeddings(csv_file):
#     """Load embeddings from the CSV file."""
#     embeddings = []
#     with open(csv_file, 'r', encoding='utf-8') as f:
#         reader = csv.reader(f)
#         for row in reader:
#             try:
#                 # Assuming embeddings are in a single column as a string like "[0.1, 0.2]"
#                 embedding = eval(row[0])  # Use eval for simplicity; ast.literal_eval is safer in production
#                 embeddings.append([float(x) for x in embedding])
#             except Exception as e:
#                 logger.error(f"Failed to parse embedding: {row} - {e}")
#                 continue
#     return embeddings

# def prepare_data_for_pinecone(original_json_path, processed_json_path, embeddings_csv_path, target_book_id=None):
#     """Prepare data for Pinecone by pairing embeddings with metadata from JSON files."""
#     # Load all data
#     logger.info("Loading original JSON...")
#     book_info = load_original_json(original_json_path)
#     logger.info("Loading processed JSON...")
#     sections = load_processed_json(processed_json_path, target_book_id)
#     logger.info("Loading embeddings...")
#     embeddings = load_embeddings(embeddings_csv_path)

#     # Check for mismatched lengths
#     if len(sections) != len(embeddings):
#         logger.warning(
#             f"Mismatched lengths: {len(sections)} sections, {len(embeddings)} embeddings. "
#             "Processing available pairs only."
#         )

#     pinecone_data = []
#     min_length = min(len(sections), len(embeddings))

#     # Process each section and embedding pair
#     for i in range(min_length):
#         section = sections[i]
#         embedding = embeddings[i]
#         section_id = section['section_id']
#         book_id = section.get('book_id')

#         # Verify book_id exists in book_info
#         if book_id not in book_info:
#             logger.warning(f"Book ID {book_id} not found in original JSON.")
#             continue

#         book_metadata = book_info[book_id]
#         metadata = {
#             'book_id': book_id,
#             'book_name': book_metadata['book_name'],
#             'author_name': book_metadata['author_name'],
#             'category_name': book_metadata['category_name'],
#             'section_title': section.get('title', 'Untitled'),
#             'text': section.get('text', ''),
#             'section_id': section_id
#         }

#         pinecone_data.append((section_id, embedding, metadata))

#     logger.info(f"Prepared {len(pinecone_data)} entries for Pinecone.")
#     return pinecone_data

# def main():
#     parser = argparse.ArgumentParser(description="Prepare data for Pinecone.")
#     parser.add_argument("--original_json", required=True, help="Path to original JSON file.")
#     parser.add_argument("--processed_json", required=True, help="Path to processed JSON file.")
#     parser.add_argument("--embeddings_csv", required=True, help="Path to embeddings CSV file.")
#     parser.add_argument("--target_book_id", type=int, default=None, help="Target book_id for processed JSON.")
#     parser.add_argument("--output_file", type=str, default="output.json", help="Base name for output JSON file.")
#     parser.add_argument("--output_dir", type=str, default="/mnt/c/shamela4/scripts/shamela_output/code/output", help="Path to output directory.")
#     args = parser.parse_args()

#     try:
#         data = prepare_data_for_pinecone(args.original_json, args.processed_json, args.embeddings_csv, args.target_book_id)
#         if data:
#             # Construct the full output path
#             output_path = os.path.join(args.output_dir, args.output_file)

#             # Create the output directory if it doesn't exist
#             os.makedirs(args.output_dir, exist_ok=True)

#             # Save to JSON file
#             with open(output_path, 'w', encoding='utf-8') as f:
#                 json.dump(data, f, ensure_ascii=False, indent=4)
#             logger.info(f"Saved prepared data to {output_path}")

#         else:
#             logger.warning("No data was prepared.")
#     except Exception as e:
#         logger.error(f"An error occurred: {str(e)}")

# if __name__ == "__main__":
#     main()