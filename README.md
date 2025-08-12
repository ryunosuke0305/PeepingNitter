# Nitter Image Scraper with Resume

## 概要

このスクリプトは、指定した Nitter インスタンス経由で特定ユーザーの投稿に含まれる **画像** を自動収集・保存します。特徴として、既存のダウンロード履歴を JSON ファイルで管理し、途中中断からのレジューム（再開）が可能です。スクレイピング対象は画像のみで、動画や外部リンクは対象外です。

## 主な機能

- **特定アカウントの画像自動収集**（@なしのユーザー名を指定）
- **Nitterインスタンス指定可能**（`https://nitter.net` など）
- **原寸画像（**``**）取得対応**
- **取得ページ数上限指定**で古い投稿にも対応
- **レート制御**（ページ取得間隔、画像ダウンロード間隔）
- **既存ダウンロード履歴のJSON管理**でレジューム可能
- **重複保存回避**（URL単位で管理）
- **簡易リトライ機構**（HTTPエラー時）
- **保存ファイル名推定**（URL末尾、またはContent-Typeから拡張子推定）
- **仮想環境対応**（`venv`推奨）

## 前提条件

- Python 3.8以降
- 以下のライブラリ
  - `requests`
  - `beautifulsoup4`
  - `tqdm`（進捗バー表示、未インストールでも動作可）

## インストール

```bash
# 仮想環境作成（例: Windows）
python -m venv .venv
.venv\Scripts\activate

# 必要ライブラリインストール
pip install requests beautifulsoup4 tqdm
```

## 使い方

1. スクリプトファイルを配置
2. ファイル先頭の `CONFIG` を編集して対象ユーザー名・保存先・インスタンス等を設定
3. 実行

```bash
python nitter_image_scraper_resume.py
```

## CONFIG 設定例

```python
CONFIG = {
    "USERNAME": "jack",                      # Nitterユーザー名（@なし）
    "INSTANCE": "https://nitter.net",        # 使用するNitterインスタンス
    "OUT_DIR": "./downloads",               # 保存先ルートフォルダ
    "MAX_PAGES": 50,                          # 取得する最大ページ数
    "PAGE_DELAY": 1.0,                        # ページ取得間隔(秒)
    "DL_DELAY": 0.1,                          # 画像DL間隔(秒)
    "TIMEOUT": 30,                            # タイムアウト秒
    "LOG_FILENAME": "download_log.json",     # 履歴ファイル名（保存先に作成）
}
```

## 保存構造

```
<OUT_DIR>/
  └─ <USERNAME>/
       ├─ download_log.json  # ダウンロード履歴
       ├─ img1.jpg
       ├─ img2.png
       └─ ...
```

## 履歴ファイル仕様（download\_log.json）

```json
{
  "created_at": "2025-08-12T05:12:34Z",      // 履歴作成日時(UTC)
  "updated_at": "2025-08-12T05:45:00Z",      // 最終更新日時(UTC)
  "downloaded": {                             // 成功したURLとファイル名のマッピング
    "https://nitter.net/pic/...": "img1.jpg"
  },
  "errors": {                                 // 失敗したURLと回数
    "https://nitter.net/pic/...": 2
  }
}
```

- 実行時に `downloaded` にあるURLはスキップ
- `errors` にあるURLは再試行対象（無制限）

## 内部処理フロー

1. 設定読み込み
2. 保存先・履歴ファイルの準備
3. NitterタイムラインHTMLを取得（最大 `MAX_PAGES` ページ）
4. `<a href^="/pic/">` リンクを抽出 → `name=orig` パラメータ付与
5. 抽出URLのうち履歴未登録分のみを対象にダウンロード
6. 成功時は `downloaded` に記録、失敗・非画像は `errors` に記録
7. ページ取得/画像DLの間隔を `PAGE_DELAY` / `DL_DELAY` で制御

## 制限事項

- 動画（mp4等）は取得対象外（GIF静止画は取得可）
- NitterのHTML構造変更により動作しなくなる可能性あり

