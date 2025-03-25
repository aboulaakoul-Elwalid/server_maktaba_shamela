from fastapi import FastAPI, HTTPException
from models import EmbedRequest, EmbedResponse
from utils import get_text_embedding
import logging

# Create FastAPI instance
app = FastAPI(title="Arabia Embedding API", description="Generate text embeddings", version="0.1.0")

# Endpoint to generate an embedding for a given text
@app.post("/embed", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    logging.info(f"Received embedding request for text: {request.text[:50]}...")
    embedding = get_text_embedding(request.text)
    if embedding is None:
        logging.error("Embedding generation failed.")
        raise HTTPException(status_code=500, detail="Embedding generation failed")
    logging.info("Embedding generated successfully.")
    return EmbedResponse(embedding=embedding)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)