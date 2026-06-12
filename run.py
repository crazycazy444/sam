import uvicorn
import os

if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("static", exist_ok=True)

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
