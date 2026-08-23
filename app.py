import requests
import streamlit as st

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

            st.subheader("分類結果")
            st.write(f"**ラベル：** {result['label']}")
            st.write(f"**確信度：** {result['confidence']:.1%}")

        except requests.exceptions.ConnectionError:
            st.error("BERT分類APIに接続できません。api.pyを起動してください。")

        except requests.exceptions.RequestException as error:
            st.error(f"API呼び出しエラー：{error}")