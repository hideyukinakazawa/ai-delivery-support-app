import random
import pandas as pd

templates = {
    "配送日時確定": [
        "午前中の受け取りを希望します",
        "都合が悪くなったため、配送日時の変更をお願いします。"
        ]
}

rows = []

for label, patterns in templates.items():
    for _ in range(10):
        body = random.choice(patterns).format(
            date=random.choice(["来週火曜日", "来週金曜日", "今週末"]),
            time_slot=random.choice(["午前中", "14時〜16時", "16時～18時", "18時～20時", "19時～21時"])
        )

        rows.append({
            "subject": f"{label}について",
            "body": body,
            "label": label
        })

df = pd.DataFrame(rows)
df.to_csv("dummy_inquiries.csv", index=False, encoding="utf-8-sig")

print("dummy_inquiries.csv を作成しました。")