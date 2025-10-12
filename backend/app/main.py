from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import analyze

app = FastAPI(title="AI Code Review Assistant")

# Add CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # React dev server
        "http://127.0.0.1:5173",  # Alternate local URL
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include your analyzer routes
app.include_router(analyze.router)

@app.get("/")
def root():
    return {"message": "AI Code Review Assistant API is running 🚀"}
