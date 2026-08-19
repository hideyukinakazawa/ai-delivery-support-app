import random
import pandas as pd

templates = {
    "希望配送日あり": [
        "平日の受け取りを希望します。お願いいたします。",
        "週末に受け取れると助かります。",
        "水曜日の配送をお願いできますか。",
        "月曜日以外でしたら都合がよいです。可能でしょうか。",
        "できるだけ早い日の受け取りを希望します。"
    ]
}

rows = []

for label, bodies in templates.items():
    for body in bodies:
        rows.append({
            "subject": random.choice([
                "配送希望について",
                "受取日のご相談",
                "配送日の確認"
            ]),
            "body": body,
            "label": label
        })

df = pd.DataFrame(rows)
df.to_csv("dummy_inquiries.csv", index=False, encoding="utf-8-sig")

print("dummy_inquiries.csv を作成しました。")