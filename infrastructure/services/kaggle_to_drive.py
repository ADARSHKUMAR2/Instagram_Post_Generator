import os
import json
import kagglehub
from infrastructure.services.google_drive import GoogleDriveManager

# The "Lock File" to ensure we never duplicate datasets
REGISTRY_FILE = "infrastructure/dataset_registry.json"
TARGET_DRIVE_FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE" # Put your folder ID here

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, "r") as f:
            return json.load(f)
    return {"ingested_datasets": []}

def save_registry(registry_data):
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry_data, f, indent=4)

def ingest_kaggle_dataset(dataset_handle: str):
    registry = load_registry()
    
    # 1. The Safety Check
    if dataset_handle in registry["ingested_datasets"]:
        print(f"🛑 HALTED: Dataset '{dataset_handle}' has already been pushed to Google Drive.")
        return

    print(f"🚀 Starting ingestion for: {dataset_handle}")
    
    # 2. Download via Kagglehub
    # Note: Kagglehub inherently caches this locally, so if the script crashes 
    # midway, it won't waste time re-downloading the zip file next time.
    print("📥 Downloading dataset from Kaggle...")
    local_path = kagglehub.dataset_download(dataset_handle)
    print(f"✅ Downloaded to temporary cache: {local_path}")
    
    # 3. Initialize Drive Manager
    drive_manager = GoogleDriveManager()
    
    # 4. Scan the downloaded folder for images and upload
    uploaded_count = 0
    for root, dirs, files in os.walk(local_path):
        for file in files:
            # Filter for images
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                full_path = os.path.join(root, file)
                
                print(f"☁️ Uploading to Drive: {file}...")
                try:
                    drive_manager.upload_image(full_path, TARGET_DRIVE_FOLDER_ID)
                    uploaded_count += 1
                except Exception as e:
                    print(f"🚨 Failed to upload {file}: {e}")

    # 5. Lock it down
    print(f"\n🎉 Success! {uploaded_count} images pushed to Google Drive.")
    registry["ingested_datasets"].append(dataset_handle)
    save_registry(registry)
    print("🔒 Dataset locked in registry. It will not be processed again.")

if __name__ == "__main__":
    # Fire the pipeline!
    ingest_kaggle_dataset("lprdosmil/unsplash-random-images-collection")