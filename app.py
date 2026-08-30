import requests
import streamlit as st

@st.dialog("作業完了の確認")
def show_completion_dialog(
    phase_name: str,
    phase_key: str,
    total_checks: int,
) -> None:
    st.write(f"「{phase_name}」のチェックがすべて完了しています。")
    st.write(f"完了チェック数：{total_checks}/{total_checks}")
    st.write("作業完了として記録する前に、内容をもう一度確認してください。")

    cancel_col, confirm_col = st.columns(2)

    with cancel_col:
        if st.button("キャンセル", key=f"{phase_key}_cancel"):
            st.session_state[f"{phase_key}_dialog_closed"] = True
            st.rerun()

    with confirm_col:
        if st.button("OK", type="primary", key=f"{phase_key}_confirm"):
            st.session_state[f"{phase_key}_confirmed"] = True
            st.rerun()


def render_phase_completion(
    phase_name: str,
    phase_key: str,
    total_checks: int,
) -> None:
    """フェーズ内の全チェック完了を確認し、確認ダイアログを表示する。"""

    is_complete = all(
        st.session_state.get(f"{phase_key}_check_{i}", False)
        for i in range(1, total_checks + 1)
    )

    if not is_complete:
        st.session_state[f"{phase_key}_dialog_closed"] = False
        st.session_state[f"{phase_key}_confirmed"] = False
        return

    if st.session_state.get(f"{phase_key}_confirmed", False):
        st.success(f"「{phase_name}」は確認済みです。")
    elif not st.session_state.get(f"{phase_key}_dialog_closed", False):
        show_completion_dialog(phase_name, phase_key, total_checks)


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
                "確信度が低いため、分類結果を確認してください。  \n"
                "問い合わせ本文、抽出結果、返信下書きを確認してください。"
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

    st.divider()
st.header("発送業務チェックリスト")
st.caption("各業務フェーズを開き、作業完了後にチェックしてください。")

with st.expander("発送日前日", expanded=False):
    st.checkbox(
        "社内修理BOXを見て、依頼シートと実際の修理品の一致を確認",
        key="day_before_check_1",
    )
    st.checkbox(
        "BOX2修理品のメールをRe:lationで確認し、担当案件へ返信",
        key="day_before_check_2",
    )
    st.checkbox(
        "BOX3修理品の配送日時を確認",
        key="day_before_check_3",
    )
render_phase_completion("発送日前日", "day_before", 3)

with st.expander("発送日当日", expanded=False):
    st.subheader("配送準備")
    st.checkbox(
        "イレギュラー対応の確認（同梱・新品交換・同時回収など）",
        key="shipping_day_check_1",
    )
    st.checkbox(
        "ご自宅配送リストの情報に抜け漏れがないか確認",
        key="shipping_day_check_2",
    )
    st.checkbox(
        "倉庫会社との共有シートにヤマト送り状No.を入力",
        key="shipping_day_check_3",
    )
    st.checkbox(
        "送り状発行データにお届け予定日時を入力",
        key="shipping_day_check_4",
    )
    st.checkbox(
        "送り状発行データをヤマトのシステムへインポートし、エラーを確認",
        key="shipping_day_check_5",
    )
    st.checkbox(
        "ERPの共有欄とERPの合計金額が一致しているか確認",
        key="shipping_day_check_6",
    )

    st.subheader("梱包")
    st.checkbox(
        "StreamlitでWチェック（発行用データ・配送リスト・お手紙・ヤマト送り状）",
        key="shipping_day_check_7",
    )
    st.checkbox(
        "イレギュラー対応はチームリーダーまたは上司に確認",
        key="shipping_day_check_8",
    )
    st.checkbox(
        "修理IDと一致した修理品が段ボール箱に詰められているか確認",
        key="shipping_day_check_9",
    )
    st.checkbox(
        "お手紙をクリアファイルに人数分入れる",
        key="shipping_day_check_10",
    )
    st.checkbox(
        "発送日当日に倉庫会社宛ての発送完了連絡を送信",
        key="shipping_day_check_11",
    )
render_phase_completion("発送日当日", "shipping_day", 11)

with st.expander("Re:lation連絡（2営業日後）", expanded=False):
    st.checkbox(
        "配送伝票番号を修理アプリに入力し、作業ステータスを「完了」に変更",
        key="relation_check_1"
    )
    st.checkbox(
        "BOX管理表で連絡方法が「電話」または「メール」か確認",
        key="relation_check_2"
   )
    st.checkbox(
        "Re:lationでやり取りをメールアドレスから検索",
        key="relation_check_3"
    )
    st.checkbox(
        "メール送信前にお客様名・送り状番号を確認",
        key="relation_check_4"
    )
render_phase_completion("Re:lation連絡", "relation", 4)
with st.expander("スマレジ登録（2営業日後）", expanded=False):
    st.checkbox(
        "登録時に代引きで「金券（釣りなし）」を選択",
        key="smaregi_check_1",
    )
    st.checkbox(
        "銀行振込では「現金預り」を選択",
        key="smaregi_check_2",
    )
    st.checkbox(
        "翌月1日以降に到着する修理品は、1日以降にスマレジ登録を行う",
        key="smaregi_check_3",
    )
    st.checkbox(
        "倉庫会社担当者からのメールに返信し作業完了",
        key="smaregi_check_4",
    )
    st.checkbox(
        "同時回収品が発送日から2週間以内に届いているか確認",
        key="smaregi_check_5",
    )

render_phase_completion("スマレジ登録", "smaregi", 5)
