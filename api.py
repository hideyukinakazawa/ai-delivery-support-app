from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AI配送業務支援API")


class Inquiry(BaseModel):
    body: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/classify")
def classify(inquiry: Inquiry):
    return {
        "label": "BERTモデル未接続",
        "confidence": 0.0,
        "body": inquiry.body,
    }