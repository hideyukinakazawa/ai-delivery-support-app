import requests
import streamlit as st


def create_reply_draft(
    preferred_date: str | None,
    preferred_time: str | None,
) -> str:
    """抽出した希望日時から返信メール下書きを作る。"""

    if preferred_date and preferred_time:
        preference_text = (
            f"配送日は「{preferred_date}」、"
            f"時間帯は「{preferred_time}」をご希望として伺っております。"
        )
    elif preferred_date:
        preference_text = (
            f"配送日は「{preferred_date}」をご希望として伺っております。"
        )
    elif preferred_time:
        preference_text = (
            f"配送時間帯は「{preferred_time}」をご希望として伺っております。"
        )
    else:
        preference_text = (
            "配送に関するお問い合わせについて、内容を確認しております。"
        )

    return (
        "お問い合わせありがとうございます。\n\n"
        f"{preference_text}\n"
        "発送時には改めてご案内いたします。\n\n"
        "よろしくお願いいたします。\n"
    )

st.set_page_config(page_title="AI配送業務支援アプリ")
st.title("AI配送業務支援アプリ")
st.caption("問い合わせメール本文から配送希望を4分類します。")

body = st.text_area(
    "問い合わせメール本文",
    placeholder="例：平日の14:00-16:00に配送をお願いします。",
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

        except requests.exceptions.ConnectionError:
            st.error(
                "BERT分類APIに接続できません。"
                "api.pyを起動してください。"
            )

        except requests.exceptions.RequestException as error:
            st.error(f"API呼び出しエラー：{error}")

if "classification_result" in st.session_state:
    result = st.session_state["classification_result"]

    st.subheader("分類結果")
    st.write(f"**ラベル：** {result['label']}")
    st.write(f"**確信度：** {result['confidence']:.1%}")
    if result["confidence"] < 0.5:
        st.warning(
        "確信度が低いため、分類結果を確認してください。"
        )
    st.write(
        f"**希望日：** "
        f"{result.get('preferred_date') or '指定なし'}"
    )
    st.write(
        f"**希望時間帯：** "
        f"{result.get('preferred_time') or '指定なし'}"
    )

    st.subheader("返信メール下書き")
    st.text_area(
        "内容を確認し、必要に応じて修正してください。",
        key="reply_draft",
        height=160,
    )
    st.caption(
        "この下書きは自動送信されません。"
        "担当者が確認・修正したうえで送信します。"
    )