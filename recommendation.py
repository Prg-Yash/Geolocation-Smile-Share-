import firebase_admin
from firebase_admin import credentials, firestore
from math import radians, sin, cos, sqrt, atan2
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Initialize FastAPI
app = FastAPI(
    title="NGO Recommendation API",
    description="API for getting nearby NGOs based on user location",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize Firebase
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

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
    email: Optional[str] = None
    phone: Optional[str] = None
    logoUrl: Optional[str] = None
    categories: Optional[List[str]] = None
    displayType: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    isVerified: Optional[str] = None
    mission: Optional[str] = None
    vision: Optional[str] = None

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    # Radius of earth in kilometers
    r = 6371
    return c * r

def get_nearby_ngos(user_lat: float, user_lon: float, radius: float = 50) -> List[dict]:
    """
    Get NGOs sorted by distance from user location
    """
    try:
        # Get all NGOs from Firebase
        ngo_ref = db.collection('ngo')
        ngos = ngo_ref.get()
        
        nearby_ngos = []
        
        for ngo in ngos:
            ngo_data = ngo.to_dict()
            
            # Skip if NGO doesn't have location data
            if 'location' not in ngo_data:
                continue
                
            ngo_lat = ngo_data['location'].get('latitude')
            ngo_lon = ngo_data['location'].get('longitude')
            
            if ngo_lat is None or ngo_lon is None:
                continue
            
            # Calculate distance
            distance = haversine_distance(user_lat, user_lon, ngo_lat, ngo_lon)
            
            # Only include NGOs within the specified radius
            if distance <= radius:
                ngo_info = {
                    'ngo_id': ngo_data.get('ngoId', ngo.id),  # Use ngoId from data or fallback to document ID
                    'ngoName': ngo_data.get('ngoName', 'Unknown'),
                    'distance': round(distance, 2),
                    'location': {
                        'latitude': ngo_lat,
                        'longitude': ngo_lon,
                        'address': ngo_data['location'].get('address', '')
                    },
                    'description': ngo_data.get('description'),
                    'email': ngo_data.get('email'),
                    'phone': ngo_data.get('phone'),
                    'logoUrl': ngo_data.get('logoUrl', ''),
                    'categories': ngo_data.get('categories', []),
                    'displayType': ngo_data.get('displayType'),
                    'district': ngo_data.get('district'),
                    'state': ngo_data.get('state'),
                    'isVerified': ngo_data.get('isVerified'),
                    'mission': ngo_data.get('mission'),
                    'vision': ngo_data.get('vision')
                }
                nearby_ngos.append(ngo_info)
        
        # Sort NGOs by distance
        nearby_ngos.sort(key=lambda x: x['distance'])
        
        return nearby_ngos
        
    except Exception as e:
        print(f"Error getting nearby NGOs: {e}")  # Log the error
        raise HTTPException(status_code=500, detail=f"Error getting nearby NGOs: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Welcome to NGO Recommendation API"}

@app.post("/nearby-ngos/", response_model=List[NGOResponse])
async def find_nearby_ngos(request: LocationRequest):
    """
    Get nearby NGOs based on user location
    
    Parameters:
    - latitude: User's latitude
    - longitude: User's longitude
    - radius: Search radius in kilometers (optional, default: 50km)
    
    Returns:
    List of nearby NGOs sorted by distance
    """
    try:
        nearby = get_nearby_ngos(request.latitude, request.longitude, request.radius)
        return nearby
    except Exception as e:
        print(f"Error in find_nearby_ngos: {str(e)}")  # Log the error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch nearby NGOs: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
