#!/usr/bin/env python3
import requests
import json
import time

def test_api():
    """APIをテストする関数"""
    base_url = "http://localhost:8000"
    
    print("🧪 APIテストを開始します...")
    
    # 1. ヘルスチェック
    print("\n1. ヘルスチェック...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ ヘルスチェック: {response.status_code}")
        print(f"   レスポンス: {response.json()}")
    except Exception as e:
        print(f"❌ ヘルスチェック失敗: {e}")
        return
    
    # 2. ファイルアップロードテスト
    print("\n2. ファイルアップロードテスト...")
    try:
        with open("test_melody.wav", "rb") as f:
            files = {"file": ("test_melody.wav", f, "audio/wav")}
            data = {"musical_key": "C Major"}
            
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
    except Exception as e:
        print(f"❌ ファイルアップロード失敗: {e}")
    
    # 3. JSON形式テスト（base64）
    print("\n3. JSON形式テスト（base64）...")
    try:
        # テストファイルをbase64に変換
        with open("test_melody.wav", "rb") as f:
            import base64
            audio_data = f.read()
            base64_data = base64.b64encode(audio_data).decode('utf-8')
        
        payload = {
            "wav_base64": f"data:audio/wav;base64,{base64_data}",
            "musical_key": "C Major"
        }
        
        response = requests.post(f"{base_url}/analyze-pitch-json", json=payload, timeout=30)
        print(f"✅ JSON形式: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   検出されたノート数: {len(result.get('notes', []))}")
            print(f"   メロディMIDI: {result.get('melody_midi', [])}")
            print(f"   長三度上: {result.get('harmonies', {}).get('major_third_up', [])}")
            print(f"   完全五度上: {result.get('harmonies', {}).get('perfect_fifth_up', [])}")
        else:
            print(f"❌ エラー: {response.text}")
    except Exception as e:
        print(f"❌ JSON形式失敗: {e}")
    
    print("\n🎉 テスト完了！")

if __name__ == "__main__":
    test_api()
