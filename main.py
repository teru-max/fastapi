from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI(
    title="Simple API",
    description="FastAPIで作成した簡単なAPI",
    version="1.0.0"
)

# データモデルの定義
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    is_available: bool = True

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    is_available: bool = True

# メモリ内のデータストレージ（実際のアプリケーションではデータベースを使用）
items_db = []
next_id = 1

# ルートエンドポイント
@app.get("/")
async def root():
    return {"message": "FastAPI Simple API へようこそ！"}

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# アイテム一覧取得
@app.get("/items", response_model=List[Item])
async def get_items():
    return items_db

# 特定のアイテム取得
@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="アイテムが見つかりません")

# アイテム作成
@app.post("/items", response_model=Item)
async def create_item(item: ItemCreate):
    global next_id
    new_item = {
        "id": next_id,
        "name": item.name,
        "description": item.description,
        "price": item.price,
        "is_available": item.is_available
    }
    items_db.append(new_item)
    next_id += 1
    return new_item

# アイテム更新
@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemCreate):
    for i, existing_item in enumerate(items_db):
        if existing_item["id"] == item_id:
            updated_item = {
                "id": item_id,
                "name": item.name,
                "description": item.description,
                "price": item.price,
                "is_available": item.is_available
            }
            items_db[i] = updated_item
            return updated_item
    raise HTTPException(status_code=404, detail="アイテムが見つかりません")

# アイテム削除
@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            deleted_item = items_db.pop(i)
            return {"message": f"アイテム '{deleted_item['name']}' が削除されました"}
    raise HTTPException(status_code=404, detail="アイテムが見つかりません")

# アプリケーションの実行
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
