from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from math import radians, sin, cos, sqrt, atan2
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PyPDF2 import PdfReader
import tempfile
import shutil
import re

# Load environment variables from .env file if it exists (local development)
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="NGO Connect API",
    description="API for NGO recommendations and PDF chat functionality",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Initialize Firebase
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Warning: Failed to initialize Firebase: {e}")
db = firestore.client()

# Initialize Gemini AI
def initialize_gemini():
    # Try to get API key from environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment variables. "
            "Please set it in your Render dashboard under Environment Variables."
        )
    
    try:
        genai.configure(api_key=api_key)
        # Use the latest Gemini model
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        return model
    except Exception as e:
        raise ValueError(f"Failed to initialize Gemini model: {e}")

# Initialize the model
try:
    model = initialize_gemini()
except Exception as e:
    print(f"Warning: {e}")
    model = None

@app.get("/health")
async def health_check():
    """Health check endpoint to verify API key and model status"""
    if not model:
        raise HTTPException(
            status_code=500,
            detail="Gemini model not initialized. Please check your API key configuration."
        )
    return {"status": "healthy", "model": "initialized"}

def extract_text_from_pdf(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text from PDF: {str(e)}")

def clean_markdown(text):
    """Remove markdown formatting and clean up the text."""
    # Remove markdown headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown bold and italic
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    
    # Remove markdown code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # Remove inline code
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Fix double line breaks
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()

@app.post("/chat-with-pdf/")
async def chat_with_pdf(
    file: UploadFile = File(...),
    question: str = Form(...)
):
    """Chat with a PDF document using Gemini AI"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    temp_dir = tempfile.mkdtemp()  # Create a temporary directory
    temp_file_path = os.path.join(temp_dir, "temp.pdf")
    
    try:
        # Save uploaded file to temporary directory
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract text from PDF
        pdf_text = extract_text_from_pdf(temp_file_path)
        
        # Prepare prompt for Gemini
        prompt = f"""Based on the following document, please answer this question: {question}

Document content:
{pdf_text}

Please provide your answer in plain text format without markdown formatting.
"""

        # Get response from Gemini with safety settings
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ]
        
        response = model.generate_content(
            prompt,
            safety_settings=safety_settings,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )
        
        # Clean any remaining markdown from the response
        cleaned_response = clean_markdown(response.text)
        
        return {
            "answer": cleaned_response,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up: remove temporary directory and its contents
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")

# Models for recommendation system
class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    radius: Optional[float] = 50.0

class NGOResponse(BaseModel):
    ngo_id: str
    ngoName: str
    distance: float
    location: dict
    description: Optional[str] = None
    contact: Optional[str] = None
    logoUrl: Optional[str] = None
    ngoRating: Optional[float] = None

def haversine_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    r = 6371
    return c * r

def get_nearby_ngos(user_lat: float, user_lon: float, radius: float = 50) -> List[dict]:
    try:
        ngo_ref = db.collection('ngo')
        ngos = ngo_ref.get()
        nearby_ngos = []
        
        for ngo in ngos:
            ngo_data = ngo.to_dict()
            if 'location' not in ngo_data:
                continue
            
            ngo_lat = ngo_data['location'].get('latitude')
            ngo_lon = ngo_data['location'].get('longitude')
            
            if ngo_lat is None or ngo_lon is None:
                continue
            
            distance = haversine_distance(user_lat, user_lon, ngo_lat, ngo_lon)
            
            if distance <= radius:
                ngo_info = {
                    'ngo_id': ngo.id,
                    'ngoName': ngo_data.get('ngoName', 'Unknown'),
                    'distance': round(distance, 2),
                    'location': ngo_data['location'],
                    'description': ngo_data.get('description'),
                    'contact': ngo_data.get('contact'),
                    'logoUrl': ngo_data.get('logoUrl'),
                    'ngoRating': ngo_data.get('ngoRating'),
                    **ngo_data
                }
                nearby_ngos.append(ngo_info)
        
        nearby_ngos.sort(key=lambda x: x['distance'])
        return nearby_ngos
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting nearby NGOs: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Welcome to NGO Connect API"}

@app.post("/nearby-ngos/", response_model=List[NGOResponse])
async def find_nearby_ngos(request: LocationRequest):
    """Get nearby NGOs based on user location"""
    try:
        nearby = get_nearby_ngos(request.latitude, request.longitude, request.radius)
        return nearby
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)