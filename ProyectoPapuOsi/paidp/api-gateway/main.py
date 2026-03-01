from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer
import requests
import os

app = FastAPI(title="PAIDP API Gateway")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

INGESTION_URL = "http://ingestion-service:8001/ingest"

@app.post("/analyze")
async def analyze(payload: dict, token: str = Depends(oauth2_scheme)):
    
    response = requests.post(INGESTION_URL, json=payload)
    
    return response.json()
