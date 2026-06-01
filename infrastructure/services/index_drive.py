import os
import time
from infrastructure.services.vector_manager import VectorManager
from infrastructure.services.google_drive import GoogleDriveManager

TEMP_INDEX_DIR = "/tmp/drive_indexing"

def run_indexer():
    print("🚀 Starting Semantic Ingestion Crawler...")
    
    # Ensure temporary download folder exists
    if not os.path.exists(TEMP_INDEX_DIR):
        os.makedirs(TEMP_INDEX_DIR)
        
    # Initialize your services
    drive_manager = GoogleDriveManager()
    vector_manager = VectorManager()
    
    print(f"📊 Current vector database count: {vector_manager.get_stats()} images.")
    
    try:
        # 1. Fetch all image files from the designated Google Drive folder
        # (Make sure your service account has access to this folder!)
        print("🔍 Scanning Google Drive for image files...")
        drive_images = drive_manager.list_images() # Uses your existing list method
        
        if not drive_images:
            print("📭 No images found in the connected Google Drive folder.")
            return

        print(f"📋 Found {len(drive_images)} images on Drive. Commencing processing pipeline...")
        
        success_count = 0
        
        for index, img_file in enumerate(drive_images):
            file_id = img_file['id']
            file_name = img_file['name']
            
            print(f"\n🔄 [{index + 1}/{len(drive_images)}] Processing: {file_name} ({file_id})")
            
            # 2. Check if already indexed to prevent wasting bandwidth/CPU
            existing = vector_manager.collection.get(ids=[file_id])
            if existing and len(existing['ids']) > 0:
                print(f"⏭️ Already indexed in ChromaDB. Skipping download.")
                continue
                
            local_path = os.path.join(TEMP_INDEX_DIR, f"{file_id}.png")
            
            try:
                # 3. Download image temporarily from Drive
                print(f"📥 Downloading from Drive...")
                drive_manager.download_file(file_id, local_path)
                
                # 4. Generate embeddings and save to ChromaDB
                print(f"🧠 Vectorizing with CLIP model...")
                success = vector_manager.index_image(local_path, file_id)
                
                if success:
                    success_count += 1
                    
            except Exception as e:
                print(f"🚨 Error processing file {file_name}: {e}")
                
            finally:
                # 5. Strictly purge the file locally to maintain zero footprint
                if os.path.exists(local_path):
                    os.remove(local_path)
                    print(f"🧹 Temporary local file deleted.")
                    
        print(f"\n✨ Ingestion complete! Successfully indexed {success_count} new images.")
        print(f"📊 Total vectors now stored: {vector_manager.get_stats()}")
        
    except Exception as e:
        print(f"❌ Critical failure in ingestion crawler: {e}")

if __name__ == "__main__":
    run_indexer()