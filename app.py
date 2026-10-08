from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os

app = FastAPI(title="Wi-Fi Controller API")

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve captive portal home page
@app.get("/")
def read_index():
    return FileResponse("static/index.html")

@app.get("/health")
def health_check():
    return {"status": "online", "message": "Wi-Fi Controller is running"}

@app.post("/authorize")
def authorize_user(mac_address: str, duration_minutes: int):
    # This endpoint receives authorization signals from n8n
    return {
        "status": "authorized",
        "mac": mac_address,
        "duration": duration_minutes
    }
