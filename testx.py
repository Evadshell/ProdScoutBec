from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
from urllib.parse import quote
from langchain_community.document_loaders import BraveSearchLoader
import os
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DIFFBOT_API_KEY = '939b1f619b77603bacb76713807e5c15'
BRAVE_API_KEY = "BSA8hqEXArzukdTLYiHgcgIAKxHk1OK"

# Get the absolute path to the client/public directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_PUBLIC_DIR = os.path.join(BASE_DIR, 'client', 'public')

# Ensure the directory exists
os.makedirs(CLIENT_PUBLIC_DIR, exist_ok=True)

class SearchQuery(BaseModel):
    query: str

def save_json_file(data: dict, filename: str) -> None:
    """Save JSON data to file with proper error handling"""
    filepath = os.path.join(CLIENT_PUBLIC_DIR, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved file to: {filepath}")  # Debug print
    except Exception as e:
        print(f"Error saving file: {e}")  # Debug print
        raise HTTPException(status_code=500, detail=f"Failed to save JSON file: {str(e)}")
def clean_image_url(url: str) -> str:
    """Validate and clean image URLs"""
    # Skip akamai pixel tracking URLs
    if 'akam' in url or 'pixel' in url:
        return None
    # Add more validation as needed
    return url

@app.post("/api/search")
async def search_products(search_query: SearchQuery):
    try:
        # Initialize BraveSearch
        loader = BraveSearchLoader(
            query=search_query.query,
            api_key=BRAVE_API_KEY,
            search_kwargs={"count": 3}
        )
        
        docs = loader.load()
        urls = [doc.metadata["link"] for doc in docs]
        
        json_results = []
        
        # Create initial empty JSON files
        for i in range(1, 4):
            empty_data = {"objects": []}
            save_json_file(empty_data, f'diffbot_response_{i}.json')
        
        for i, url in enumerate(urls, 1):
            encoded_url = quote(url, safe='')
            endpoint = f'https://api.diffbot.com/v3/product?token={DIFFBOT_API_KEY}&url={encoded_url}'
            
            response = requests.get(endpoint)
            if not response.ok:
                continue
                
            json_data = response.json()
            if 'objects' in json_data:
                for obj in json_data['objects']:
                    if 'images' in obj:
                        obj['images'] = [
                            img for img in obj['images']
                            if img.get('url') and clean_image_url(img['url'])
                        ]
                        for img in obj['images']:
                            img['url'] = clean_image_url(img['url'])
            save_json_file(json_data, f'diffbot_response_{i}.json')
            
            if 'objects' in json_data and json_data['objects']:
                json_results.append(json_data)
        
        return {"status": "success", "results": json_results}
    
    except Exception as e:
        print(f"Error in search_products: {e}")  # Debug print
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)