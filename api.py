import unicodedata
import json
from pathlib import Path
import re

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

DATE_PATTERN = r"\d{1,2}月\d{1,2}日|月曜日|火曜日|水曜日|木曜日|金曜日|土曜日|日曜日|平日|週末|月曜日以外|月・火・水のいずれか|できるだけ早い日"

YAMATO_TIME_SLOTS = [
    ("14:00-16:00", "14", "16"),
    ("16:00-18:00", "16", "18"),
    ("18:00-20:00", "18", "20"),
    ("19:00-21:00", "19", "21"),
]

def extract_yamato_time_slot(body: str) -> str | None:
    """本文からヤマト運輸の時間帯だけを抽出し正式表記へ統一"""

    normalized_body = unicodedata.normalize("NFKC", body)
    normalized_body = (
        normalized_body
        .replace("〜", "~")
        .replace("～", "~")
        .replace("－", "-")
        .replace("−", "-")
    )

    if "午前中" in normalized_body:
        return "午前中"

    for canonical_time, start_hour, end_hour in YAMATO_TIME_SLOTS:
        pattern = (
            rf"{start_hour}(?::00)?(?:時)?\s*"
            rf"(?:~|-|から)\s*"
            rf"{end_hour}(?::00)?(?:時)?"
        )

        if re.search(pattern, normalized_body):
            return canonical_time

    # 「午後」だけではヤマトの時間帯を特定できないため返さない
    return None

def extract_preferences(body: str) -> tuple[str | None, str | None]:
    date_match = re.search(DATE_PATTERN, body)

    preferred_date = date_match.group() if date_match else None
    preferred_time = extract_yamato_time_slot(body)

    return preferred_date, preferred_time

TIME_PATTERN = (
    r"\d{1,2}時(?:[〜～\-]|から)\d{1,2}時(?:の間)?"
    r"|\d{1,2}:\d{2}[〜～\-]\d{1,2}:\d{2}"
    r"|19時以降"
    r"|(?:午前|午後)\d{1,2}時"
    r"|午前中|午後"
    r"|\d{1,2}時"
    r"|\d{1,2}:\d{2}"
)

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
    label = label_names[label_id]
    confidence = float(probabilities[label_id].item())
    
    preferred_date, preferred_time = extract_preferences(inquiry.body)

    return {
        "label": label,
        "confidence": confidence,
        "body": inquiry.body,
        "preferred_date": preferred_date,
        "preferred_time": preferred_time,
        }