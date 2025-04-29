# import json
# import logging
# import argparse
# import pinecone
# import os
# from dotenv import load_dotenv

# # Set up basic logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # Load environment variables from .env file
# load_dotenv()

# def upload_to_pinecone(data, index_name, api_key, environment):
#     """Upload data to Pinecone index."""
#     # Initialize Pinecone
#     from pinecone import Pinecone, ServerlessSpec
    
#     # Create a Pinecone client
#     pc = Pinecone(api_key=api_key)
    
#     # Get the index
#     index = pc.Index(index_name)
    
#     try:
#         # Pinecone expects vectors in a specific format
#         vectors_to_upsert = []
#         for id, embedding, metadata in data:
#             vectors_to_upsert.append({
#                 "id": str(id),  # Convert to string to be safe
#                 "values": embedding,
#                 "metadata": metadata
#             })
        
#         # Upsert the vectors in batches to avoid exceeding size limits
#         batch_size = 100  # Adjust based on your vector dimension and metadata size
#         for i in range(0, len(vectors_to_upsert), batch_size):
#             batch = vectors_to_upsert[i:i+batch_size]
#             index.upsert(vectors=batch)
#             logger.info(f"Uploaded batch {i//batch_size + 1}/{(len(vectors_to_upsert)-1)//batch_size + 1} to Pinecone")
        
#         logger.info(f"Successfully uploaded {len(vectors_to_upsert)} vectors to Pinecone index '{index_name}'")
#     except Exception as e:
#         logger.error(f"Error uploading to Pinecone index '{index_name}': {e}")

# def load_prepared_data(json_file):
#     """Load prepared data from a JSON file."""
#     try:
#         with open(json_file, 'r', encoding='utf-8') as f:
#             data = json.load(f)
#         logger.info(f"Loaded prepared data from {json_file}")
#         return data
#     except FileNotFoundError:
#         logger.error(f"JSON file not found: {json_file}")
#         return None
#     except json.JSONDecodeError:
#         logger.error(f"Invalid JSON in file: {json_file}")
#         return None

# def main():
#     parser = argparse.ArgumentParser(description="Upload prepared data to Pinecone.")
#     parser.add_argument("--json_file", required=True, help="Path to the JSON file containing prepared data.")
#     args = parser.parse_args()

#     # Get Pinecone credentials from environment variables
#     api_key = os.getenv("PINECONE_API_KEY")
#     index_name = os.getenv("PINECONE_INDEX_NAME")  # Corrected variable name
#     environment = os.getenv("PINECONE_ENVIRONMENT")

#     # Check if environment variables are set
#     if not api_key or not index_name or not environment:
#         logger.error("Pinecone API key, index name, and environment must be set in the .env file.")
#         return

#     # Load the prepared data from the JSON file
#     data = load_prepared_data(args.json_file)
#     if data:
#         # Upload the data to Pinecone
#         upload_to_pinecone(data, index_name, api_key, environment)
#     else:
#         logger.warning("No data was loaded, upload aborted.")

# if __name__ == "__main__":
#     main()