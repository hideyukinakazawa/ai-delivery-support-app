# ai-delivery-support-app

## 概要

配送に関する問い合わせメールをAIで分類し、配送担当者の確認・判断を支援するプロトタイプです。  

## 実装済み機能

- 問い合わせ本文の入力
- BERTで配送希望を4種類に分類
- 分類ラベルと確信度の表示
- StreamlitからFastAPI経由での分類実行

## 分類ラベル

- 希望配送日あり
- 希望配送時間帯あり
- 希望配送日時あり
- 希望日時なし

## データ・技術

- `generate_dummy_inquiries.py` からCSVを生成 
- Python,Streamlit,BERTを使用
- 公開版ではFastAPIで実装
- Re:lation API連携は、BERT分類の実装後に追加予定

※公開リポジトリには個人情報、APIトークンを含めません。