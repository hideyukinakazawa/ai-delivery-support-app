import os
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
import requests
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


GOOGLE_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]
MOCK_OPERATOR = "mock-user"

CASE_HEADERS = [
    "case_id",
    "shipping_date",
    "case_status",
    "created_at",
    "updated_at",
    "closed_at",
]

ITEMS = {
    "day_before": [
        "社内修理BOXを見て、依頼シートと実際の修理品の一致を確認",
        "BOX2修理品のメールをRe:lationで確認し、担当案件へ返信",
        "BOX3修理品の配送日時を確認",
    ],
    "shipping_day": [
        "イレギュラー対応の確認（同梱・新品交換・同時回収など）",
        "ご自宅配送リストの情報に抜け漏れがないか確認",
        "倉庫会社との共有シートにヤマト送り状No.を入力",
        "送り状発行データにお届け予定日時を入力",
        "送り状発行データをヤマトのシステムへインポートし、エラーを確認",
        "ERPの共有欄とERPの合計金額が一致しているか確認",
        "StreamlitでWチェック（発行用データ・配送リスト・お手紙・ヤマト送り状）",
        "イレギュラー対応はチームリーダーまたは上司に確認",
        "修理IDと一致した修理品が段ボール箱に詰められているか確認",
        "お手紙をクリアファイルに人数分入れる",
        "発送日当日に倉庫会社宛ての発送完了連絡を送信",
    ],
    "relation": [
        "配送伝票番号を修理アプリに入力し、作業ステータスを「完了」に変更",
        "BOX管理表で連絡方法が「電話」または「メール」か確認",
        "Re:lationでやり取りをメールアドレスから検索",
        "メール送信前にお客様名・送り状番号を確認",
    ],
    "smaregi": [
        "登録時に代引きで「金券（釣りなし）」を選択",
        "銀行振込では「現金預り」を選択",
        "翌月1日以降に到着する修理品は、1日以降にスマレジ登録を行う",
        "倉庫会社担当者からのメールに返信し作業完了",
        "同時回収品が発送日から2週間以内に届いているか確認",
    ],
}

PHASE_COUNTS = {
    phase: len(labels)
    for phase, labels in ITEMS.items()
}

PHASE_NAMES = {
    "day_before": "発送日前日",
    "shipping_day": "発送日当日",
    "relation": "Re:lation連絡（2営業日後）",
    "smaregi": "スマレジ登録（2営業日後）",
}

def are_phase_checks_complete(phase: str, total_checks: int) -> bool:
    """指定フェーズの全項目がチェック済みかを返す。"""
    return all(
        st.session_state.get(f"{phase}_check_{i}", False)
        for i in range(1, total_checks + 1)
    )

def get_worksheet(sheet_name: str):
    """既存のローカルOAuth設定で接続する。"""
    spreadsheet_id = os.getenv("MOCK_HISTORY_SPREADSHEET_ID")
    oauth_client_file = os.getenv("GOOGLE_OAUTH_CLIENT_FILE")

    if not spreadsheet_id or not oauth_client_file:
        raise RuntimeError("Google Sheetsのローカル設定が未完了です。")

    client_path = Path(oauth_client_file)

    if not client_path.exists():
        raise RuntimeError(
            "Google OAuthクライアント設定ファイルが見つかりません。"
        )

    token_dir = (
        Path(os.getenv("LOCALAPPDATA", Path.home()))
        / "ai_delivery_support_app"
    )
    token_dir.mkdir(parents=True, exist_ok=True)
    token_path = token_dir / "google_token.json"

    credentials = None

    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(
            str(token_path),
            GOOGLE_SHEETS_SCOPES,
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_path),
            GOOGLE_SHEETS_SCOPES,
        )
        credentials = flow.run_local_server(port=0)

        token_path.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.worksheet(sheet_name)


def get_history_worksheet():
    return get_worksheet("作業履歴")


def get_cases_worksheet():
    return get_worksheet("案件一覧")


def checked_rows(worksheet, headers):
    """見出しを確認してからデータ行を返す。"""
    rows = worksheet.get_all_values()

    if not rows or rows[0][:len(headers)] != headers:
        raise ValueError("シートの見出しが想定と異なります。")

    return rows[1:]


def load_cases():
    rows = checked_rows(get_cases_worksheet(), CASE_HEADERS)
    return [
        dict(zip(CASE_HEADERS, row + [""] * (6 - len(row))))
        for row in rows
        if row and row[0]
    ]


def save_case(case_id: str, shipping_date: str) -> bool:
    """案件を保存する。同じIDでの再試行は再追加しない。"""
    try:
        worksheet = get_cases_worksheet()
        checked_rows(worksheet, CASE_HEADERS)

        if case_id in worksheet.col_values(1):
            return True

        now = datetime.now(
            ZoneInfo("Asia/Tokyo")
        ).isoformat(timespec="seconds")

        worksheet.append_row(
            [case_id, shipping_date, "未着手", now, now, ""],
            value_input_option="RAW",
        )
        return True

    except Exception:
        try:
            worksheet = get_cases_worksheet()
            return case_id in worksheet.col_values(1)
        except Exception:
            return False


def update_case_status(case_id, status):
    """対象案件の状態と日時だけを更新する。"""
    worksheet = get_cases_worksheet()
    rows = checked_rows(worksheet, CASE_HEADERS)

    matches = [
        (i, row)
        for i, row in enumerate(rows, 2)
        if row and row[0] == case_id
    ]

    if len(matches) != 1:
        raise ValueError("案件IDが存在しないか、重複しています。")

    index, row = matches[0]
    row = row + [""] * (6 - len(row))

    if row[2] == "クローズ":
        if status != "クローズ":
            raise ValueError("クローズ済み案件は変更できません。")
        return

    now = datetime.now(
        ZoneInfo("Asia/Tokyo")
    ).isoformat(timespec="seconds")

    worksheet.update(
        range_name=f"C{index}:F{index}",
        values=[
            [
                status,
                row[3],
                now,
                now if status == "クローズ" else "",
            ]
        ],
        value_input_option="RAW",
    )

def open_case(case):
    """作業履歴から確認済みフェーズを復元する。"""
    rows = get_history_worksheet().get_all_values()
    completed_phases = set()

    # 旧版と現行版のフェーズ名に対応する
    aliases = {
        "day_before": {
            PHASE_NAMES["day_before"],
            "発送日前日",
        },
        "shipping_day": {
            PHASE_NAMES["shipping_day"],
            "発送日当日",
        },
        "relation": {
            PHASE_NAMES["relation"],
            "Re:lation連絡",
        },
        "smaregi": {
            PHASE_NAMES["smaregi"],
            "スマレジ登録",
        },
    }

    for row in rows[1:]:
        if len(row) < 5 or row[1] != case["case_id"]:
            continue

        if row[2] == "フェーズ完了" and row[4] == "完了":
            for phase, names in aliases.items():
                if row[3] in names:
                    completed_phases.add(phase)

    # 前の案件の一時状態を消す
    for key in list(st.session_state):
        if key.startswith(
            tuple(PHASE_COUNTS) + ("history_event_id_",)
        ) or key in (
            "case_closed",
            "classification_result",
            "reply_draft",
            "email_body",
            "save_error",
            "progress_dirty",
            "progress_notice",
        ):
            del st.session_state[key]

    closed = case["case_status"] == "クローズ"

    for phase, count in PHASE_COUNTS.items():
        complete = closed or phase in completed_phases
        st.session_state[f"{phase}_confirmed"] = complete

        for i in range(1, count + 1):
            st.session_state[f"{phase}_check_{i}"] = complete

    st.session_state["active_case_id"] = case["case_id"]
    st.session_state["active_shipping_date"] = case["shipping_date"]
    st.session_state["case_closed"] = closed

def get_history_event_id(event_key: str) -> str:
    """案件と操作に対応する記録IDを、セッション内で再利用する。"""
    case_id = st.session_state["active_case_id"]
    session_key = f"history_event_id_{case_id}_{event_key}"

    if session_key not in st.session_state:
        st.session_state[session_key] = str(uuid.uuid4())

    return st.session_state[session_key]

def append_history(
    record_id: str,
    event_name: str,
    phase_name: str,
    status: str,
    note: str = "",
) -> bool:
    """選択中の案件IDで既存の作業履歴に追記する。"""
    try:
        worksheet = get_history_worksheet()

        if record_id in worksheet.col_values(1):
            return True

        recorded_at = datetime.now(
            ZoneInfo("Asia/Tokyo")
        ).strftime("%Y-%m-%d %H:%M:%S")

        worksheet.append_row(
            [
                record_id,
                st.session_state["active_case_id"],
                event_name,
                phase_name,
                status,
                MOCK_OPERATOR,
                recorded_at,
                note,
            ],
            value_input_option="RAW",
        )
        return True

    except Exception:
        try:
            worksheet = get_history_worksheet()
            return record_id in worksheet.col_values(1)
        except Exception:
            return False


def create_reply_draft(
    preferred_date: str | None,
    preferred_time: str | None,
) -> str:
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]

    if preferred_date:
        try:
            date_obj = datetime.strptime(
                preferred_date,
                "%Y-%m-%d",
            )
            delivery_date = (
                f"{date_obj.month}月{date_obj.day}日"
                f"（{weekdays[date_obj.weekday()]}）"
            )
        except ValueError:
            delivery_date = preferred_date
    else:
        delivery_date = ""

    if preferred_date and preferred_time:
        preference_text = (
            "受取希望日時につきまして、\n"
            f"【{delivery_date} {preferred_time}】を"
            "ご希望として伺っております。"
        )
    elif preferred_date:
        preference_text = (
            "受取希望日につきまして、\n"
            f"【{delivery_date}】をご希望として伺っております。"
        )
    elif preferred_time:
        preference_text = (
            "受取希望時間帯につきまして、\n"
            f"【{preferred_time}】をご希望として伺っております。"
        )
    else:
        preference_text = (
            "受取希望日時につきまして、\n"
            "内容を確認しております。"
        )

    return f"""●●様

ご返信いただきありがとうございます。
修理担当の五味でございます。

{preference_text}

配送可否を確認のうえ、発送時には改めてご案内いたします。
お品物のご到着まで今しばらくお待ちいただけますと幸いです。

引き続き何卒よろしくお願い申し上げます。

○○株式会社
五味

※土日祝日は休業日のため、ご連絡が遅くなる可能性がございます。あらかじめご了承ください。"""


@st.dialog("作業完了の確認")
def confirm_phase(phase):
    st.write(
        f"「{PHASE_NAMES[phase]}」の全項目を"
        "確認済みとして記録しますか？"
    )

    if st.button("確認して記録", key="confirm_phase_ok"):
        all_checked = are_phase_checks_complete(
            phase,
            PHASE_COUNTS[phase],
        )

        if not all_checked:
            st.error("すべての項目をチェックしてください。")
            return

        recorded = append_history(
            get_history_event_id(f"{phase}_complete"),
            "フェーズ完了",
            PHASE_NAMES[phase],
            "完了",
        )

        if not recorded:
            st.error(
                "作業履歴の保存を確認できません。"
                "時間をおいて再試行してください。"
            )
            return

        try:
            update_case_status(
                st.session_state["active_case_id"],
                "作業中",
            )
        except Exception as error:
            st.error(
                "作業履歴は記録済みですが、"
                "案件一覧の更新を確認できません"
                f"（{type(error).__name__}）。"
                "もう一度「確認して記録」を押してください。"
            )
            return

        st.session_state[f"{phase}_confirmed"] = True
        st.rerun()

@st.dialog("案件クローズの確認")
def confirm_close():
    st.write("この案件をクローズしますか？")

    if st.button("案件をクローズする", key="confirm_close_ok"):
        if st.session_state.get("save_error") or not all(
            st.session_state.get(f"{phase}_confirmed")
            for phase in ITEMS
        ):
            st.error("全フェーズの確認と保存を完了してください。")
            return

        case_id = st.session_state["active_case_id"]

        recorded = append_history(
            f"{case_id}:close",
            "案件クローズ",
            "スマレジ登録完了後",
            "クローズ",
        )

        if not recorded:
            st.error("履歴の保存を確認できません。再試行してください。")
            return

        try:
            update_case_status(case_id, "クローズ")
        except Exception as error:
            st.error(
                "履歴は記録済みですが、"
                "案件一覧の更新を確認できません"
                f"（{type(error).__name__}）。"
                "再試行してください。"
            )
            return

        st.session_state.pop("active_case_id", None)
        st.session_state["case_notice"] = (
            f"{case_id}をクローズしました。"
        )
        st.rerun()


# ---------- アプリ画面 ----------

st.set_page_config(page_title="AI配送業務支援アプリ")
st.title("AI配送業務支援アプリ")
st.caption("案件保存・再開対応版")


# ---------- 案件一覧画面 ----------

if "active_case_id" not in st.session_state:
    st.subheader("案件一覧")

    if "case_notice" in st.session_state:
        st.success(st.session_state.pop("case_notice"))

    try:
        cases = load_cases()
    except Exception as error:
        st.error(
            f"案件一覧を読めません（{type(error).__name__}）。"
            "接続設定と見出しを確認してください。"
        )
        st.stop()

    if cases:
        mapping = {
            case["case_id"]: case
            for case in cases
        }

        selected = st.selectbox(
            "再開する案件",
            list(mapping),
            format_func=lambda cid: (
                f"{cid} ｜ "
                f"{mapping[cid]['shipping_date']} ｜ "
                f"{mapping[cid]['case_status']}"
            ),
        )

        if st.button("選択した案件を開く", type="primary"):
            try:
                open_case(mapping[selected])
                st.rerun()
            except Exception as error:
                st.error(
                    f"案件を開けません（{type(error).__name__}）。"
                    "チェック状態シートと見出しを確認してください。"
                )
    else:
        st.info("保存済み案件はありません。")

    with st.expander("新しい案件を作成"):
        if "new_case_id" not in st.session_state:
            st.session_state["new_case_id"] = (
                f"CASE-{uuid.uuid4()}"
            )

        with st.form("new_case_form"):
            shipping_date = st.date_input(
                "発送予定日",
                value=datetime.now(
                    ZoneInfo("Asia/Tokyo")
                ).date(),
            )
            submitted = st.form_submit_button("案件を保存")

        if submitted:
            saved = save_case(
                st.session_state["new_case_id"],
                shipping_date.isoformat(),
            )

            if saved:
                st.session_state.pop("new_case_id", None)
                st.session_state["case_notice"] = (
                    "保存しました。"
                    "一覧から案件を選んで開いてください。"
                )
                st.rerun()

            st.error(
                "保存を確認できません。"
                "日付を変えずに再試行してください。"
            )

    st.stop()


# ---------- 選択した案件の作業画面 ----------

closed = st.session_state.get("case_closed", False)

st.caption(
    "保存するのはフェーズ完了と案件クローズです。"
    "フェーズ途中のチェックは、案件を開き直すとリセットされます。"
)

if st.button("案件一覧へ戻る"):
    st.session_state.pop("active_case_id", None)
    st.rerun()

completed = sum(
    bool(st.session_state.get(f"{phase}_confirmed"))
    for phase in ITEMS
)

with st.container(border=True):
    st.write(
        f"**配送案件：** {st.session_state['active_case_id']}"
    )
    st.write(
        f"**発送日：** {st.session_state['active_shipping_date']}"
    )

    if closed:
        status = "クローズ済み"
    elif completed == 4:
        status = "全作業完了・クローズ待ち"
    else:
        status = "作業受付中"

    st.write(
        f"**状態：** {status}　／　"
        f"確認済み：{completed}/4フェーズ"
    )


# ---------- BERT分類と返信下書き ----------

with st.expander("問い合わせの分類・返信下書き"):
    body = st.text_area(
        "問い合わせメール本文",
        key="email_body",
        height=180,
    )

    if st.button("配送希望を分類する"):
        if not body.strip():
            st.warning("メール本文を入力してください。")
        else:
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/classify",
                    json={"body": body},
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()

                st.session_state["classification_result"] = result
                st.session_state["reply_draft"] = create_reply_draft(
                    result.get("preferred_date"),
                    result.get("preferred_time"),
                )

            except (
                requests.exceptions.RequestException,
                ValueError,
            ):
                st.error(
                    "分類APIを呼び出せません。"
                    "api.pyの起動と応答を確認してください。"
                )

    if "classification_result" in st.session_state:
        result = st.session_state["classification_result"]

        st.write(
            f"**分類：** {result['label']} ／ "
            f"**確信度：** {result['confidence']:.1%}"
        )

        if result["confidence"] < 0.5:
            st.warning(
                "確信度が低いため、"
                "本文・抽出結果・下書きを確認してください。"
            )

        st.write(
            f"希望日：{result.get('preferred_date') or '指定なし'}"
        )
        st.write(
            f"希望時間帯：{result.get('preferred_time') or '指定なし'}"
        )

        st.text_area(
            "返信メール下書き（編集可能）",
            key="reply_draft",
            height=180,
        )

    st.caption(
        "本文・下書きは保存しません。"
        "自動送信はせず、担当者が確認・修正して送信します。"
    )


# ---------- チェックリスト ----------

st.header("発送業務チェックリスト")

for phase, labels in ITEMS.items():
    confirmed = st.session_state.get(
        f"{phase}_confirmed",
        False,
    )
    title = PHASE_NAMES[phase] + (
        " ✓確認済み" if confirmed else ""
    )

    with st.expander(title):
        for i, label in enumerate(labels, 1):
            if phase == "shipping_day" and i in (1, 7):
                st.subheader(
                    "配送準備" if i == 1 else "梱包"
                )

            st.checkbox(
                label,
                key=f"{phase}_check_{i}",
                disabled=closed or confirmed,
            )

        all_checked = are_phase_checks_complete(
            phase,
            len(labels),
        )

        if confirmed:
            st.success("確認済みです。")
        elif all_checked and not closed:
            if st.button(
                "このフェーズの完了を確認",
                key=f"confirm_{phase}",
            ):
                confirm_phase(phase)


# ---------- クローズ ----------

if closed:
    st.success("この案件はクローズ済みです。")
elif completed == 4:
    if st.button(
        "この案件をクローズする",
        type="primary",
        disabled=bool(st.session_state.get("save_error")),
    ):
        confirm_close()


history_url = os.getenv(
    "MOCK_HISTORY_SPREADSHEET_URL",
    "",
).strip()

if history_url.startswith(
    "https://docs.google.com/spreadsheets/"
):
    st.link_button("作業履歴を開く", history_url)