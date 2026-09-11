import re
from datetime import datetime
from zoneinfo import ZoneInfo


HEADER_ROW = 1

HEADERS = [
    "案件ID",
    "対象フェーズ",
    "状態",
    "実行者",
    "記録日時（JST）",
    "備考",
]


def case_number(case_id):
    """案件IDを確認し、連番部分を取り出す。"""
    match = re.fullmatch(
        r"([1-9][0-9]*)-([0-9]{8})",
        case_id,
    )

    if not match:
        raise ValueError(
            "案件IDは「1-20260911」の形式にしてください。"
        )

    datetime.strptime(match[2], "%Y%m%d")
    return int(match[1])


def make_case_id(shipping_date, existing_case_ids):
    """全案件の最大番号＋1と、発送日から案件IDを作る。"""
    date_text = datetime.strptime(
        shipping_date,
        "%Y-%m-%d",
    ).strftime("%Y%m%d")

    numbers = [
        case_number(case_id)
        for case_id in existing_case_ids
    ]

    next_number = max(numbers, default=0) + 1
    return f"{next_number}-{date_text}"


def load_history(worksheet):
    """新しい6列形式の作業履歴を読み込む。"""
    rows = worksheet.get_all_values()

    if len(rows) < HEADER_ROW:
        raise ValueError("作業履歴の見出しがありません。")

    if rows[HEADER_ROW - 1][:6] != HEADERS:
        raise ValueError(
            "作業履歴の1行目を、指定の6列にしてください。"
        )

    records = []

    for row in rows[HEADER_ROW:]:
        if not any(row):
            continue

        case_number(row[0])

        if any(row[6:]):
            raise ValueError("作業履歴の列数が6列を超えています。")

        padded_row = row[:6] + [""] * max(0, 6 - len(row))
        records.append(dict(zip(HEADERS, padded_row)))

    return records


def save_history(
    worksheet,
    case_id,
    phase_name,
    status,
    operator="mock-user",
    note="",
):
    """フェーズ完了またはクローズを、重複を避けて記録する。"""
    case_number(case_id)

    if not phase_name.strip():
        raise ValueError("対象フェーズを指定してください。")

    if status not in ("完了", "クローズ"):
        raise ValueError("状態は「完了」か「クローズ」です。")

    records = load_history(worksheet)

    already_saved = any(
        record["案件ID"] == case_id
        and record["対象フェーズ"] == phase_name
        and record["状態"] == status
        for record in records
    )

    if already_saved:
        return True

    recorded_at = datetime.now(
        ZoneInfo("Asia/Tokyo")
    ).strftime("%Y-%m-%d %H:%M:%S")

    worksheet.append_row(
        [
            case_id,
            phase_name,
            status,
            operator,
            recorded_at,
            note,
        ],
        value_input_option="RAW",
        table_range=f"A{HEADER_ROW}:F",
    )

    return True