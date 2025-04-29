# import pandas as pd
# from dotenv import load_dotenv
# import os
# import argparse
# import time  # Import the time module
# import logging #Import logging

# load_dotenv()  # Load environment variables from .env file

# from utils import get_embeddings_in_chunks  # Modified absolute import

# #Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# def generate_and_save_embeddings(csv_input_path, output_dir, start_chunk=0):
#     """
#     Reads text data from CSV, generates Mistral embeddings in chunks, and saves them to separate CSV files in batches,
#     preserving the original filename and creating category folders.

#     Args:
#         csv_input_path (str): Path to the input CSV file.
#         output_dir (str): Path to the main directory to save the embedding CSV chunks.
#         start_chunk (int, optional): The chunk number to start processing from. Defaults to 0.
#     """
#     try:
#         logging.info(f"Reading CSV file: {csv_input_path}")
#         df = pd.read_csv(csv_input_path)
#     except FileNotFoundError:
#         logging.error(f"Error: Input CSV file not found at {csv_input_path}")
#         return

#     if 'text' not in df.columns:
#         logging.error(f"Error: 'text' column not found in the input CSV file.")
#         return

#     texts = df['text'].tolist()
#     logging.info(f"Generating embeddings for {len(texts)} texts...")

#     # Reduce chunk size to stay within token limits (16,384 tokens max)
#     # Based on error message, each text is approximately 169 tokens on average
#     chunk_size = 30  # Reduced to stay under API token limit
#     delay = 1       # Delay between API calls
#     num_chunks = (len(texts) + chunk_size - 1) // chunk_size
#     batch_size = 100  # Store each API call result in its own batch

#     # Extract filename and category from input path
#     filename = os.path.basename(csv_input_path)
#     base_filename = filename[:-4]  # Remove '.csv'
#     category = base_filename.split('_')[0]  # Extract category from filename (e.g., "أصول الفقه")
#     embedded_filename = base_filename.replace('processed_processed', 'embedded') #Replace processed_processed with embedded

#     # Create category folder
#     category_dir = os.path.join(output_dir, category)
#     os.makedirs(category_dir, exist_ok=True)

#     embeddings = [] #Store embeddings here
#     for i in range(start_chunk, num_chunks):
#         start_index = i * chunk_size
#         end_index = min((i + 1) * chunk_size, len(texts))
#         chunk = texts[start_index:end_index]

#         logging.info(f"Processing chunk {i+1}/{num_chunks}. Texts: {start_index}-{end_index-1}")

#         try:
#             chunk_embeddings = get_embeddings_in_chunks(chunk)
#             embeddings.extend(chunk_embeddings)
#         except Exception as e:
#             logging.exception(f"Error processing chunk {i+1}: {e}")
#             # Handle the error appropriately (e.g., retry, skip, etc.)
#             continue

#         time.sleep(delay)  # Wait for 1 second

#         # Check if it's time to store the current batch
#         if (i + 1) % batch_size == 0 or (i + 1) == num_chunks:
#             batch_num = (i + 1) // batch_size if (i + 1) % batch_size == 0 else (i + 1) // batch_size + 1
#             output_csv_path = os.path.join(category_dir, f'{embedded_filename}_batch_{batch_num}.csv')
            
#             # Robust file saving with retry logic
#             max_retries = 3
#             for retry in range(max_retries):
#                 try:
#                     # First save to a temporary file in the WSL filesystem
#                     temp_path = f"/tmp/embeddings_temp_{batch_num}.csv"
#                     batch_df = pd.DataFrame({'embeddings': embeddings})
#                     batch_df.to_csv(temp_path, index=False)
                    
#                     # Then copy to the Windows filesystem
#                     import shutil
#                     shutil.copy2(temp_path, output_csv_path)
                    
#                     # Remove temp file
#                     os.remove(temp_path)
                    
#                     logging.info(f"Embeddings for batch {batch_num} saved to: {output_csv_path}")
#                     break
#                 except OSError as e:
#                     if retry < max_retries - 1:
#                         logging.warning(f"I/O error saving batch {batch_num}, retrying ({retry+1}/{max_retries}): {e}")
#                         time.sleep(2)  # Wait before retrying
#                     else:
#                         logging.error(f"Failed to save batch {batch_num} after {max_retries} attempts: {e}")
#                         # Save to fallback location in WSL filesystem
#                         fallback_path = f"/tmp/{embedded_filename}_batch_{batch_num}.csv"
#                         batch_df.to_csv(fallback_path, index=False)
#                         logging.info(f"Saved batch {batch_num} to fallback location: {fallback_path}")
            
#             embeddings = []  # Clear embeddings

#     logging.info("All embeddings generated and saved to separate CSV files in batches.")


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description='Generate embeddings from CSV file and save to separate CSV files in batches.')
#     parser.add_argument('input_csv', type=str, help='Path to the input CSV file.')
#     parser.add_argument('output_dir', type=str, help='Path to the directory to save the embedding CSV chunks.')
#     parser.add_argument('--start_chunk', type=int, default=0, help='The chunk number to start processing from.')
#     args = parser.parse_args()

#     input_csv = args.input_csv
#     output_dir = args.output_dir
#     start_chunk = args.start_chunk

#     generate_and_save_embeddings(input_csv, output_dir, start_chunk)