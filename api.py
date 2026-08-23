import json
from pathlib import Path

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_DIR = Path("delivery_bert_model")

if not MODEL_DIR.exists():
    raise FileNotFoundError("delivery_bert_model フォルダが見つかりません。")

with open(MODEL_DIR / "label_names.json", encoding="utf-8") as f:
    label_names = json.load(f)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
model.to(device)
model.eval()

app = FastAPI(title="AI配送業務支援API")


class Inquiry(BaseModel):
    body: str


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": True}


@app.post("/classify")
def classify(inquiry: Inquiry):
    inputs = tokenizer(
        inquiry.body,
        return_tensors="pt",
        truncation=True,
        max_length=128,
    )

    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.no_grad():
        logits = model(**inputs).logits
        probabilities = torch.softmax(logits, dim=1)[0]

    label_id = int(torch.argmax(probabilities).item())

    return {
        "label": label_names[label_id],
        "confidence": round(float(probabilities[label_id]), 3),
        "body": inquiry.body,
    }