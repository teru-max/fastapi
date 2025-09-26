#!/usr/bin/env python3
import tempfile
import os
from basic_pitch.inference import predict

def test_basic_pitch_direct():
    """basic-pitchを直接テスト"""
    print("🔍 basic-pitch直接テスト...")
    
    try:
        # テストファイルで直接実行
        result = predict("test_melody.wav")
        model_output, midi_data, note_events = result
        
        print(f"✅ basic-pitch成功!")
        print(f"   ノートイベント数: {len(note_events)}")
        
        if note_events:
            print("   最初の5つのノート:")
            for i, ev in enumerate(note_events[:5]):
                print(f"     {i+1}: start={ev[0]:.2f}s, end={ev[1]:.2f}s, midi={ev[2]}, velocity={ev[3]:.2f}")
        
        return note_events
    except Exception as e:
        print(f"❌ basic-pitch失敗: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_basic_pitch_direct()
