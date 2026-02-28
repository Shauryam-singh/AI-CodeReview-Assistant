from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import analyze, pr_analyze

app = FastAPI(title="AI-CodeReview-Assistant", version="1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-code-review-assistant-nine.vercel.app",
        "http://localhost:5174",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(pr_analyze.router)

@app.get("/")
def root():
    return {"status": "running"}