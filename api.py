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

DATE_PATTERN = r"\d{1,2}月\d{1,2}日|[月火水木金土日]曜日|平日|週末|できるだけ早い日"

TIME_PATTERN = re.compile(
    r"午前中|(?<![\d:])(?:14:00-16:00|16:00-18:00|"
    r"18:00-20:00|19:00-21:00)(?![\d:])"
)

NEGATIVE_PATTERN = re.compile(
    r"以外|除[くきい]|避け|不可|無理|難し|不要|不在|"
    r"でき(?:ない|ません)|出来(?:ない|ません)|"
    r"受け取れ(?:ない|ません)|希望し(?:ない|ません)|"
    r"では(?:なく|ない|ありません)|じゃ(?:なく|ない)|"
    r"しないで|都合が(?:悪|つか|つきません)|ダメ|だめ|NG",
    re.IGNORECASE,
)


def extract_preferences(body: str) -> tuple[str | None, str | None]:
    """否定を含む区切りを除外し、候補が1種類の場合だけ返す。"""
    text = unicodedata.normalize("NFKC", body)
    text = re.sub(r"[〜～~－−]", "-", text)
    text = re.sub(
        r"(?<![\d:])(\d{1,2})(?::00)?時?\s*(?:-|から)\s*"
        r"(\d{1,2})(?::00)?時?(?![\d:])",
        r"\1:00-\2:00",
        text,
    )

    dates, times = set(), set()
    for clause in re.split(r"[、,。.!！?？\n;；]+", text):
        if NEGATIVE_PATTERN.search(clause):
            continue
        dates.update(re.findall(DATE_PATTERN, clause))
        times.update(TIME_PATTERN.findall(clause))

    # 否定後の別候補は別の区切りにあれば採用。複数候補は担当者確認。
    preferred_date = next(iter(dates)) if len(dates) == 1 else None
    preferred_time = next(iter(times)) if len(times) == 1 else None
    return preferred_date, preferred_time


def extract_yamato_time_slot(body: str) -> str | None:
    return extract_preferences(body)[1]


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