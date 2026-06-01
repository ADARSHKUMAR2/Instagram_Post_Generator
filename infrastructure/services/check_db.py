from infrastructure.services.vector_manager import VectorManager

def peek_at_database():
    print("🧠 Connecting directly to ChromaDB...")
    try:
        # Initialize your VectorManager
        vm = VectorManager()
        
        # Access the raw ChromaDB collection
        # (Assuming your class saves it as 'self.collection'. 
        # If it's named something else like 'self._collection', update this line)
        collection = vm.collection 
        
        count = collection.count()
        print(f"\n📊 Total vectors currently in database: {count}")
        
        if count > 0:
            print("\n🔍 Peeking at the most recent entries from Google Drive:")
            
            # .peek() grabs actual records without needing a search query
            results = collection.peek(limit=3) 
            
            for i in range(len(results['ids'])):
                print(f"\n📸 Record [{i+1}]")
                print(f"   ID (Vector Hash): {results['ids'][i]}")
                print(f"   Metadata: {results['metadatas'][i]}")
        else:
            print("\n⚠️ The database is completely empty.")
            
    except Exception as e:
        print(f"\n🚨 Error reading database: {e}")

if __name__ == "__main__":
    peek_at_database()