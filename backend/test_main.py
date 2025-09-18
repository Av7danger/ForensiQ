# Simple test FastAPI server
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="UFDR Test API")

@app.get("/")
async def root():
    return {"message": "UFDR Test API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)