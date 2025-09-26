#!/usr/bin/env python3
import requests
import json
import time

def test_api_debug():
    """APIをデバッグする関数"""
    base_url = "http://localhost:8000"
    
    print("🔍 APIデバッグを開始します...")
    
    # 1. ヘルスチェック
    print("\n1. ヘルスチェック...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ ヘルスチェック: {response.status_code}")
        print(f"   レスポンス: {response.json()}")
    except Exception as e:
        print(f"❌ ヘルスチェック失敗: {e}")
        return
    
    # 2. ファイルアップロードテスト（詳細デバッグ）
    print("\n2. ファイルアップロードテスト（詳細デバッグ）...")
    try:
        with open("test_melody.wav", "rb") as f:
            files = {"file": ("test_melody.wav", f, "audio/wav")}
            data = {"musical_key": "C Major"}
            
            print(f"   ファイルサイズ: {len(f.read())} bytes")
            f.seek(0)  # ファイルポインタをリセット
            
            response = requests.post(f"{base_url}/analyze-pitch", files=files, data=data, timeout=30)
            print(f"✅ ファイルアップロード: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   検出されたノート数: {len(result.get('notes', []))}")
                print(f"   メロディMIDI: {result.get('melody_midi', [])}")
                print(f"   長三度上: {result.get('harmonies', {}).get('major_third_up', [])}")
                print(f"   完全五度上: {result.get('harmonies', {}).get('perfect_fifth_up', [])}")
            else:
                print(f"❌ エラー: {response.text}")
                # より詳細なエラー情報を取得
                try:
                    error_detail = response.json()
                    print(f"   エラー詳細: {error_detail}")
                except:
                    print(f"   生のエラーレスポンス: {response.text}")
    except Exception as e:
        print(f"❌ ファイルアップロード失敗: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 デバッグ完了！")

if __name__ == "__main__":
    test_api_debug()
