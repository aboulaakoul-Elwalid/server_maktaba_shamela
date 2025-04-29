# import logging
# import os
# from dotenv import load_dotenv
# from pinecone import Pinecone
# #from sentence_transformers import SentenceTransformer  # Remove this import
# from utils import get_text_embedding  # Import your Mistral API function

# # Load environment variables from .env file
# load_dotenv()

# # Set up basic logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# def test_pinecone_with_query(api_key, index_name, query_text, top_k=20):
#     """
#     Test the Pinecone index by querying with a sample text using the Mistral embedding model.

#     Args:
#         api_key (str): Your Pinecone API key.
#         index_name (str): The name of your Pinecone index (e.g., 'shamela').
#         query_text (str): The query text to search for (e.g., 'What does the text say about prayer?').
#         top_k (int): The number of top results to retrieve (default is 5).

#     Returns:
#         None: Prints the results or an error message.
#     """
#     try:
#         # Step 1: Initialize Pinecone client
#         pc = Pinecone(api_key=api_key)
#         index = pc.Index(index_name)
#         logger.info(f"Connected to Pinecone index: {index_name}")

#         # Step 2: Generate embedding for the query text using Mistral API
#         query_embedding = get_text_embedding(query_text)
#         if query_embedding is None:
#             logger.error(f"Failed to generate embedding for query: '{query_text}'")
#             return

#         logger.info(f"Generated embedding for query: '{query_text}'")

#         # Step 3: Query the Pinecone index
#         response = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
#         logger.info(f"Received response from Pinecone with {len(response['matches'])} matches")

#         # Step 4: Print the results
#         if response['matches']:
#             for match in response['matches']:
#                 print(f"Score: {match['score']}")
#                 print(f"Section ID: {match['id']}")
#                 print(f"Book Name: {match['metadata']['book_name']}")
#                 print(f"Section Title: {match['metadata']['section_title']}")
#                 print(f"Text: {match['metadata']['text'][:200]}...")  # First 200 characters
#                 print("-" * 50)
#         else:
#             logger.warning("No matches found for the query.")

#     except Exception as e:
#         logger.error(f"An error occurred: {str(e)}")

# if __name__ == "__main__":
#     # Get Pinecone credentials from environment variables
#     API_KEY = os.getenv("PINECONE_API_KEY")
#     INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

#     # Replace these with your actual values
#     QUERY_TEXT = "م الادله التفصيليه قد تكفل به القياس"  # Arabic query about Zakat

#     # Run the test
#     test_pinecone_with_query(API_KEY, INDEX_NAME, QUERY_TEXT)