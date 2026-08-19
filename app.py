import streamlit as st
st.set_page_config(
    page_title="AI発送業務支援アプリ",
    layout="centered"
)

st.title("AI発送業務支援アプリ")

st.write("初期画面")

import streamlit as st
from datetime import date

# -----------------------------
# ページ設定
# -----------------------------
st.set_page_config(
    page_title="AI発送業務支援アプリ",
    layout="centered"
)

# -----------------------------
# タイトル
# -----------------------------

# -----------------------------
# 検索欄
# -----------------------------
col1, col2 = st.columns([3, 1])

with col1:
    email = st.text_input(
        "",
        placeholder="メールアドレスを入力",
        label_visibility="collapsed"
    )

with col2:
    st.button("検索")

# -----------------------------
# 発送日
# -----------------------------
st.write("### 発送日")

col1, col2 = st.columns([1.5, 5])

with col1:
    work_date = st.date_input(
    "",
    value=date.today(),
    label_visibility="collapsed"
)

# -----------------------------
# メニュー
# -----------------------------
menu = [
    "問い合わせ取得",
    "発送前・事前準備(前日)",
    "発送前・配送準備(当日)",
    "発送前・梱包(当日)",
    "倉庫会社から発送・リレーション連絡(2営業日後)",
    "倉庫会社から発送・スマレジ登録(2営業日後)"
]

for item in menu:
    with st.expander(item):

        if item == "問い合わせ取得":

            # モックデータ
            category = "発送前・配送準備"

            st.subheader("問い合わせ情報")

            st.markdown("**メールアドレス**")
            st.write("hideyuki.nakazawa@example.com")

            st.markdown("**件名**")
            st.write("Re: ご連絡ありがとうございます【○○】")

            st.markdown("**受信日時**")
            st.write("2026/08/06 10:12")

            st.markdown("**AI分類（モック）**")
            st.success(category)

            st.caption("※現在はモック表示です。今後BERTによる分類結果を表示します。")

        elif item == "発送前・事前準備(前日)":

            st.checkbox("社内修理BOXを見て、依頼シートと実際の修理品の一致を確認")

            st.checkbox("BOX2修理品のメールをRe:lationで確認、担当の案件につき返信")

            st.checkbox("BOX3修理品の配送日時を確認")

        elif item == "発送前・配送準備(当日)":

            st.checkbox("イレギュラー対応の確認（同梱・新品交換・同時回収など）")

            st.checkbox("ご自宅配送リストの情報に抜け漏れ無し")
 
            st.checkbox("倉庫会社との共有シートにヤマト送り状No.を入力")

            st.checkbox("送り状発行データにお届け予定日時を入力")

            st.checkbox("送り状発行データをヤマトのシステムへインポートしてエラー無し")

            st.checkbox("ERPの共有欄とERPの合計金額が一致している")

            st.checkbox("お手紙へ書く内容にイレギュラー項目はあるか？")

            st.checkbox("ご自宅配送リスト「預かり品」の有無を実物と突き合わせてチェック")

        elif item == "発送前・梱包(当日)":

            st.checkbox("StreamlitでWチェック（発行用データ・配送リスト・お手紙・ヤマト送り状をアップ）")

            st.checkbox("イレギュラー対応はチームリーダーor上司に確認")

            st.checkbox("修理IDと一致した修理品が段ボール箱に詰められているか？")

            st.checkbox("クレンジング＆プロテクション以外の修理品にラナパー実施（推奨）")

            st.checkbox("お手紙をクリアファイルに人数分入れる")

            st.checkbox("発送日当日に倉庫会社宛て発送完了連絡を送信")

        elif item == "倉庫会社から発送・リレーション連絡(2営業日後)":

            st.checkbox("配送伝票番号をERPに入力、作業ステータスを「完了」に変更")

            st.checkbox("BOX管理表で連絡方法が「電話」もしくは「メール」か確認")

            st.checkbox("リレーションでやり取りがあるかメールアドレスで検索（無ければ新規作成）")

            st.checkbox("メール送信前にお客様のお名前・送り状番号が正しいか確認")

        elif item == "倉庫会社から発送・スマレジ登録(2営業日後)":

            st.checkbox("登録する際に代引きで「金券（釣りなし）」を選択")

            st.checkbox("銀行振込では「現金預り」を選択")

            st.checkbox("翌月1日以降に到着する修理品は、1日以降に登録したか？")

            st.checkbox("倉庫会社の担当者からのメールに返信して作業完了")

            st.checkbox("同時回収は発送日から2週間以内で届いているか確認（届いていない場合は報告）")

st.markdown("---")
