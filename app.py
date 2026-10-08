from fastapi import FastAPI 
app = FastAPI(title="Wi-Fi Controller API")

@app.get("/health")
def health_check():
    return {"status": "online", "service": "wifi-controller"}

@app.post("/authorize")
def authorize_user(mac_address: str, duration_minutes: int):
    return {"status": "authorized", "mac": mac_address, "duration": duration_minutes}
