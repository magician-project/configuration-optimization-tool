import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import deployment, modules, questionnaire, use_cases

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Configuration Optimization Tool API",
    description="COT — decision-support layer between use-case descriptions and MAGICIAN modules.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questionnaire.router, prefix="/questionnaire", tags=["Questionnaire"])
app.include_router(use_cases.router,     prefix="/use-cases",    tags=["Use Cases"])
app.include_router(modules.router,       prefix="/use-cases",    tags=["Modules"])
app.include_router(deployment.router,    prefix="/use-cases",    tags=["Deployment"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "COT API"}
