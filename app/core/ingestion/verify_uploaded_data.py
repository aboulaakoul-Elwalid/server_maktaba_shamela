# import os
# import pinecone
# import logging
# from dotenv import load_dotenv

# # Set up basic logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # Load environment variables from .env file
# load_dotenv()

# # Get Pinecone credentials from environment variables
# api_key = os.getenv("PINECONE_API_KEY")
# environment = os.getenv("PINECONE_ENVIRONMENT")
# index_name = os.getenv("PINECONE_INDEX_NAME")

# if not api_key or not environment or not index_name:
#     logger.error("Pinecone API key, index name, and environment must be set in the .env file.")
#     exit(1)

# try:
#     # Initialize Pinecone using the new API method
#     pinecone.init(api_key=api_key, environment=environment)
#     index = pinecone.Index(index_name)
# except Exception as e:
#     logger.error(f"Failed to initialize Pinecone: {e}")
#     exit(1)

# # 1. Verify Index Statistics
# try:
#     stats = index.describe_index_stats()
#     print("Index Statistics:")
#     print(stats)
# except Exception as e:
#     logger.error(f"Error fetching index statistics: {e}")

# # 2. Test with a Sample Query
# # IMPORTANT: Replace the query_vector below with an actual embedding vector 
# # from your dataset (it must match the index dimensions, e.g., 1024).
# query_vector = [0.1, 0.2, 0.3]  # Placeholder: update with a valid vector
# try:
#     response = index.query(vector=query_vector, top_k=1, include_metadata=True)
#     if response and 'matches' in response and response['matches']:
#         print("Metadata for top match:")
#         print(response['matches'][0]['metadata'])
#     else:
#         print("No matches found; please verify your query vector.")
# except Exception as e:
#     logger.error(f"Error during query: {e}")