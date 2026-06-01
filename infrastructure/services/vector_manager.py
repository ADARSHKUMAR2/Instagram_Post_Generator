import os
import chromadb
from sentence_transformers import SentenceTransformer
from PIL import Image

class VectorManager:
    def __init__(self):
        print("🧠 Initializing VectorManager...")
        
        # 1. Setup the local persistent Vector Database
        # This saves the vectors to a folder so you don't lose them when Docker restarts
        db_path = "/app/infrastructure/vectordb"
        if not os.path.exists(db_path):
            os.makedirs(db_path)
            
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        
        # Chroma organizes data into "collections" (like tables in SQL)
        self.collection = self.chroma_client.get_or_create_collection(
            name="drive_images",
            metadata={"hnsw:space": "cosine"} # Cosine similarity is best for CLIP
        )
        
        # 2. Load the Vision-Language Model (CLIP)
        print("📥 Loading CLIP Model (this may take a minute on first boot)...")
        # clip-ViT-B-32 is the perfect balance of lightweight and highly accurate
        self.model = SentenceTransformer('clip-ViT-B-32')
        print("✅ VectorManager ready!")

    def index_image(self, image_path: str, drive_file_id: str) -> bool:
        """
        Reads an image from disk, converts its 'meaning' into numbers, 
        and saves it to the Vector DB.
        """
        try:
            # Check if we already indexed this file to avoid duplicates
            existing = self.collection.get(ids=[drive_file_id])
            if existing and len(existing['ids']) > 0:
                print(f"⏭️ File {drive_file_id} already indexed. Skipping.")
                return True

            # Open image and convert to vector embedding
            image = Image.open(image_path)
            image_embedding = self.model.encode(image).tolist()
            
            # Save to ChromaDB
            self.collection.add(
                ids=[drive_file_id],
                embeddings=[image_embedding],
                metadatas=[{"source": "google_drive", "status": "indexed"}]
            )
            print(f"✅ Indexed image: {drive_file_id}")
            return True
            
        except Exception as e:
            print(f"🚨 Failed to index {drive_file_id}: {e}")
            return False

    def search(self, text_query: str, top_k: int = 3) -> list:
        """
        Converts text into a vector, compares it against all saved image vectors,
        and returns the closest matches.
        """
        try:
            # Convert the user's text ("cyberpunk city") into numbers
            text_embedding = self.model.encode(text_query).tolist()
            
            # Ask ChromaDB for the closest geometric matches
            results = self.collection.query(
                query_embeddings=[text_embedding],
                n_results=top_k
            )
            
            # Extract and return just the Google Drive IDs
            if results and len(results['ids']) > 0:
                return results['ids'][0]
            return []
            
        except Exception as e:
            print(f"🚨 Search failed: {e}")
            return []

    def get_stats(self):
        """Returns the total number of images currently indexed."""
        return self.collection.count()