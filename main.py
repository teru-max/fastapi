from typing import List, Dict, Any, Optional, Tuple
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
import uvicorn
import tempfile
import os
import io
import base64
import json

import numpy as np
import librosa
import soundfile as sf

# basic-pitch
from basic_pitch.inference import predict

app = FastAPI(title="Harmony Generation API", version="1.0.0")

# -----------------------------
# File handling / audio loading
# -----------------------------
def _save_upload_to_temp_wav(upload: UploadFile) -> str:
    """
    Save the uploaded file to a temporary WAV file and return the file path.
    Raises HTTPException if content type or extension is invalid.
    """
    filename = upload.filename or "input.wav"
    content_type = upload.content_type or ""
    if not (filename.lower().endswith(".wav") or "wav" in content_type.lower()):
        raise HTTPException(status_code=400, detail="Please upload a valid WAV file (.wav)")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            data = upload.file.read()
            tmp.write(data)
            temp_path = tmp.name
        return temp_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}") from e

def _ensure_wav_readable(path: str, target_sr: int = 22050) -> np.ndarray:
    """
    Load WAV as mono float32 numpy array at target_sr.
    Ensures the audio is in a format basic-pitch expects.
    """
    try:
        audio, sr = librosa.load(path, sr=target_sr, mono=True)
        if audio.ndim != 1:
            audio = librosa.to_mono(audio)
        return audio.astype(np.float32)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read WAV: {e}") from e

def decode_base64_audio(base64_data: str) -> bytes:
    """base64音声データをデコード"""
    try:
        # data:audio/wav;base64, プレフィックスを除去
        if base64_data.startswith('data:'):
            base64_data = base64_data.split(',')[1]
        
        return base64.b64decode(base64_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"base64デコードエラー: {str(e)}")

# -----------------------------
# Pitch analysis (basic-pitch)
# -----------------------------
def _analyze_pitch_with_basic_pitch(audio_path: str) -> List[Dict[str, Any]]:
    """
    Run basic-pitch's predict() to obtain note events.
    Returns note events as a list of dicts:
      [{start: float, end: float, midi: int, velocity: float}, ...]
    Sorted by start time.
    """
    try:
        model_output, midi_data, note_events = predict(audio_path)
        events: List[Dict[str, Any]] = []
        
        # note_events is a list of tuples: (start_time, end_time, midi_note, velocity, pitch_bends)
        for ev in note_events:
            start = float(ev[0])  # start_time
            end = float(ev[1])    # end_time
            midi = int(round(ev[2]))  # midi_note
            velocity = float(ev[3])    # velocity
            # Clamp to MIDI range
            midi = max(0, min(127, midi))
            events.append({"start": start, "end": end, "midi": midi, "velocity": velocity})
        
        events.sort(key=lambda x: x["start"])
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pitch analysis failed: {e}") from e

# -----------------------------
# Harmony generation utilities
# -----------------------------
_NOTE_NAME_TO_PC = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "E#": 5, "F": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}

_MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]       # Ionian
_NAT_MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 10]  # Aeolian (natural minor)

def _parse_key_to_scale_pcs(musical_key: str) -> List[int]:
    """
    Parse key string like 'C Major', 'A minor', 'F# major', 'Eb Minor' into a scale pitch-class set [0..11].
    Supports Major / Minor (natural minor).
    """
    if not musical_key or not isinstance(musical_key, str):
        raise HTTPException(status_code=400, detail="musical_key must be a non-empty string like 'C Major' or 'A minor'.")

    parts = musical_key.strip().replace("-", " ").split()
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid key format. Use e.g. 'C Major' or 'A minor'.")

    root_name = parts[0].upper().replace("♯", "#").replace("♭", "b")
    # Mode detection (case-insensitive)
    mode_word = "".join(parts[1:]).lower()  # join in case of variants like "maj or"
    is_major = "maj" in mode_word
    is_minor = "min" in mode_word

    if not (is_major or is_minor):
        raise HTTPException(status_code=400, detail="Key must specify Major or Minor (e.g., 'C Major', 'A minor').")

    if root_name not in _NOTE_NAME_TO_PC:
        raise HTTPException(status_code=400, detail=f"Unsupported key root '{root_name}'.")

    root_pc = _NOTE_NAME_TO_PC[root_name]
    intervals = _MAJOR_INTERVALS if is_major else _NAT_MINOR_INTERVALS
    return sorted({(root_pc + i) % 12 for i in intervals})

def _nearest_scale_note(target: int, scale_pcs: List[int]) -> int:
    """
    Given a target MIDI note and a scale pitch-class set, return the nearest MIDI note that belongs to the scale.
    Tie-breaking favors the lower note for stability.
    """
    if not (0 <= target <= 127):
        target = max(0, min(127, target))

    best_note = target
    best_dist = 128  # large
    target_oct = target // 12

    # Check a reasonable window around the target (two octaves up/down to be safe)
    for oct_shift in range(target_oct - 2, target_oct + 3):
        for pc in scale_pcs:
            cand = pc + 12 * oct_shift
            if 0 <= cand <= 127:
                dist = abs(cand - target)
                if dist < best_dist or (dist == best_dist and cand < best_note):
                    best_note = cand
                    best_dist = dist
    return best_note

def generate_harmonies(melody_midi: List[int], musical_key: str, musical_keys: Optional[List[Dict]] = None, musical_keys_by_index: Optional[List[str]] = None, notes: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """
    Generate basic harmony parts from a melody MIDI list for a given key.

    - major_third_up: nom + 4 semitones, then corrected to nearest scale degree
    - perfect_fifth_up: nom + 7 semitones, then corrected to nearest scale degree

    Scale correction ensures notes remain within the specified key (similar to Cubase chord/scale snapping).
    """
    # Build per-note keys
    keys_per_note = []
    
    if musical_keys and notes:
        # time-range assignment
        ranges = musical_keys
        for i, note in enumerate(notes):
            start_time = note.get("start", 0)
            chosen_key = None
            
            # Find matching range
            for r in ranges:
                if start_time >= r["start"] and start_time < r["end"]:
                    chosen_key = r["key"]
                    break
            
            if not chosen_key:
                # choose nearest range by start distance
                best_dist = float('inf')
                for r in ranges:
                    dist = abs(start_time - r["start"])
                    if dist < best_dist:
                        chosen_key = r["key"]
                        best_dist = dist
            
            keys_per_note.append(chosen_key or musical_key)
            
    elif musical_keys_by_index:
        # index-based assignment
        for i in range(len(melody_midi)):
            if i < len(musical_keys_by_index):
                keys_per_note.append(musical_keys_by_index[i])
            else:
                keys_per_note.append(musical_keys_by_index[-1] if musical_keys_by_index else musical_key)
    else:
        # single key for all notes
        keys_per_note = [musical_key] * len(melody_midi)

    third_up: List[int] = []
    fifth_up: List[int] = []

    for i, n in enumerate(melody_midi):
        if n is None:
            third_up.append(None)  # preserve rests if present
            fifth_up.append(None)
            continue

        base = int(n)
        current_key = keys_per_note[i] if i < len(keys_per_note) else musical_key
        scale_pcs = _parse_key_to_scale_pcs(current_key)
        
        # Raw shifts
        raw_maj_third = max(0, min(127, base + 4))
        raw_perfect_fifth = max(0, min(127, base + 7))

        # Snap to scale
        third_note = _nearest_scale_note(raw_maj_third, scale_pcs)
        fifth_note = _nearest_scale_note(raw_perfect_fifth, scale_pcs)

        third_up.append(third_note)
        fifth_up.append(fifth_note)

    return {
        "major_third_up": third_up,
        "perfect_fifth_up": fifth_up,
        "keys_assigned": keys_per_note,
    }

# -----------------------------
# FastAPI endpoints
# -----------------------------

# ルートエンドポイント
@app.get("/")
async def root():
    return {"message": "Harmony Generation API へようこそ！"}

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 音声解析エンドポイント（ファイルアップロード）
@app.post("/analyze-pitch")
async def analyze_pitch(
    file: UploadFile = File(...),
    musical_key: str = Form(..., description="Key like 'C Major' or 'A minor'"),
) -> JSONResponse:
    """
    POST /analyze-pitch
    - Accepts a WAV file upload and musical_key form field
    - Extracts melody (MIDI note events) using basic-pitch
    - Generates harmony parts (major third up, perfect fifth up) snapped to the key scale
    - Returns JSON with original notes and harmony MIDI lists
    """
    temp_path: Optional[str] = None
    try:
        # Save and load
        temp_path = _save_upload_to_temp_wav(file)
        target_sr = 22050
        audio = _ensure_wav_readable(temp_path, target_sr)

        # Analyze pitch
        note_events = _analyze_pitch_with_basic_pitch(temp_path)  # [{start, end, midi, velocity}...]

        # Extract a simple melody MIDI list aligned by event order (common for monophonic vocal lines)
        melody_midi: List[int] = [ev["midi"] for ev in note_events]

        # Generate harmonies
        harmonies = generate_harmonies(melody_midi, musical_key, notes=note_events)

        response = {
            "model": "basic-pitch",
            "sample_rate": target_sr,
            "key": musical_key,
            "notes": note_events,                     # original detected events with timing
            "melody_midi": melody_midi,               # convenience: melody as a simple list
            "harmonies": harmonies,                   # {'major_third_up': [...], 'perfect_fifth_up': [...], 'keys_assigned': [...]}
        }
        return JSONResponse(content=response)
    finally:
        # Cleanup temporary file
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

# SIM AI用のJSON形式エンドポイント（base64対応）
@app.post("/analyze-pitch-json")
async def analyze_pitch_json(request: dict) -> JSONResponse:
    """
    SIM AI用のJSON形式で音声解析（base64対応）
    入力例:
    {
        "api_url": "https://your-api-host",
        "wav_base64": "data:audio/wav;base64,...",
        "musical_key": "C Major",
        "musical_keys": [{"start": 0.0, "end": 15.0, "key": "C Major"}],
        "musical_keys_by_index": ["C Major", "G Major"]
    }
    """
    temp_path: Optional[str] = None
    try:
        # 入力検証
        if not isinstance(request, dict):
            raise HTTPException(status_code=400, detail="Request must be a JSON object")
        
        # base64データを優先
        audio_data = None
        if request.get("wav_base64"):
            audio_data = decode_base64_audio(request["wav_base64"])
        elif request.get("wav_url"):
            # URLから音声データを取得（実装は簡略化）
            raise HTTPException(status_code=400, detail="URLからの音声取得は未実装です")
        else:
            raise HTTPException(status_code=400, detail="wav_base64またはwav_urlが必要です")
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_data)
            temp_path = tmp.name
        
        # 音声解析
        target_sr = 22050
        audio = _ensure_wav_readable(temp_path, target_sr)
        note_events = _analyze_pitch_with_basic_pitch(temp_path)
        melody_midi: List[int] = [ev["midi"] for ev in note_events]
        
        # ハモリ生成
        musical_key = request.get("musical_key", "C Major")
        musical_keys = request.get("musical_keys")
        musical_keys_by_index = request.get("musical_keys_by_index")
        
        harmonies = generate_harmonies(
            melody_midi, 
            musical_key, 
            musical_keys=musical_keys,
            musical_keys_by_index=musical_keys_by_index,
            notes=note_events
        )
        
        response = {
            "model": "basic-pitch",
            "sample_rate": target_sr,
            "key": musical_key,
            "musical_keys": musical_keys,
            "musical_keys_by_index": musical_keys_by_index,
            "notes": note_events,
            "melody_midi": melody_midi,
            "harmonies": harmonies,
        }
        return JSONResponse(content=response)
    finally:
        # Cleanup temporary file
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

# アプリケーションの実行
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)