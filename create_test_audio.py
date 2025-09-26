import numpy as np
import soundfile as sf
import librosa

# テスト用のシンプルなメロディ（ドレミファソラシド）
sample_rate = 22050
duration = 2.0  # 2秒

# MIDIノートを周波数に変換
def midi_to_freq(midi_note):
    return 440.0 * (2 ** ((midi_note - 69) / 12))

# メロディのMIDIノート
melody_notes = [60, 62, 64, 65, 67, 69, 71, 72]  # ドレミファソラシド
note_duration = duration / len(melody_notes)

# 音声を生成
audio = np.array([])
for note in melody_notes:
    freq = midi_to_freq(note)
    t = np.linspace(0, note_duration, int(sample_rate * note_duration))
    # サイン波で生成
    note_audio = 0.3 * np.sin(2 * np.pi * freq * t)
    audio = np.concatenate([audio, note_audio])

# WAVファイルとして保存
sf.write('test_melody.wav', audio, sample_rate)
print("テスト用音声ファイル 'test_melody.wav' を作成しました")
print(f"メロディ: {melody_notes}")
print(f"長さ: {duration}秒")
