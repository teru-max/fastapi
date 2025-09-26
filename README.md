# FastAPI Simple API

FastAPIで作成した簡単なAPIです。アイテムのCRUD操作（作成、読み取り、更新、削除）を提供します。

## 機能

- アイテムの一覧取得
- 特定のアイテムの取得
- 新しいアイテムの作成
- 既存のアイテムの更新
- アイテムの削除
- ヘルスチェック

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. アプリケーションの起動

```bash
python main.py
```

または

```bash
uvicorn main:app --reload
```

アプリケーションは `http://localhost:8000` で起動します。

## API エンドポイント

### 基本エンドポイント

- `GET /` - ウェルカムメッセージ
- `GET /health` - ヘルスチェック

### アイテム管理

- `GET /items` - 全アイテムの取得
- `GET /items/{item_id}` - 特定のアイテムの取得
- `POST /items` - 新しいアイテムの作成
- `PUT /items/{item_id}` - アイテムの更新
- `DELETE /items/{item_id}` - アイテムの削除

## API ドキュメント

アプリケーション起動後、以下のURLでAPIドキュメントを確認できます：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 使用例

### アイテムの作成

```bash
curl -X POST "http://localhost:8000/items" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "サンプルアイテム",
       "description": "これはサンプルです",
       "price": 1000.0,
       "is_available": true
     }'
```

### アイテムの取得

```bash
curl -X GET "http://localhost:8000/items"
```

### 特定のアイテムの取得

```bash
curl -X GET "http://localhost:8000/items/1"
```

### アイテムの更新

```bash
curl -X PUT "http://localhost:8000/items/1" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "更新されたアイテム",
       "description": "更新された説明",
       "price": 1500.0,
       "is_available": true
     }'
```

### アイテムの削除

```bash
curl -X DELETE "http://localhost:8000/items/1"
```

## データモデル

### Item

```json
{
  "id": 1,
  "name": "アイテム名",
  "description": "アイテムの説明",
  "price": 1000.0,
  "is_available": true
}
```

## 公開デプロイ

### Railway（推奨）

1. [Railway](https://railway.app)にアカウントを作成
2. GitHubリポジトリを接続
3. 自動的にデプロイされます

### Heroku

1. [Heroku](https://heroku.com)にアカウントを作成
2. Heroku CLIをインストール
3. 以下のコマンドでデプロイ：

```bash
heroku create your-app-name
git push heroku main
```

### Docker

```bash
# イメージをビルド
docker build -t fastapi-app .

# コンテナを実行
docker run -p 8000:8000 fastapi-app
```

### その他のプラットフォーム

- **Render**: `render.yaml`ファイルを作成
- **Vercel**: `vercel.json`ファイルを作成
- **Google Cloud Run**: Dockerfileを使用
- **AWS Lambda**: Mangumを使用

## 注意事項

- このAPIはメモリ内にデータを保存するため、アプリケーションを再起動するとデータは失われます
- 本番環境では適切なデータベースを使用してください
- 公開時は適切な認証とセキュリティ設定を追加してください
