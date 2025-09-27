from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
import uvicorn
import tempfile
import os
import io
import base64
import json
import numpy as np

app = FastAPI(title="Harmony Generation API (Light)", version="1.0.0")

# -----------------------------
# File handling / audio loading
# -----------------------------
def _save_upload_to_temp_wav(upload: UploadFile) -> str:
    """Save the uploaded file to a temporary WAV file and return the file path."""
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

def decode_base64_audio(base64_data: str) -> bytes:
    """base64音声データをデコード"""
    try:
        if base64_data.startswith('data:'):
            base64_data = base64_data.split(',')[1]
        return base64.b64decode(base64_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"base64デコードエラー: {str(e)}")

# -----------------------------
# Mock pitch analysis (for testing)
# -----------------------------
def _analyze_pitch_mock(audio_path: str) -> List[Dict[str, Any]]:
    """Mock pitch analysis for testing"""
    # テスト用の固定メロディ（ドレミファソラシド）
    melody_notes = [60, 62, 64, 65, 67, 69, 71, 72]
    note_duration = 0.25  # 各ノート0.25秒
    
    events = []
    for i, note in enumerate(melody_notes):
        start = i * note_duration
        end = start + note_duration
        events.append({
            "start": start,
            "end": end,
            "midi": note,
            "velocity": 0.8
        })
    
    return events

# -----------------------------
# Harmony generation utilities
# -----------------------------
_NOTE_NAME_TO_PC = {
    "C": 0, "B#": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6, "G": 7,
    "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11,
}

_MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]
_NAT_MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 10]

def _parse_key_to_scale_pcs(musical_key: str) -> List[int]:
    """Parse key string into scale pitch-class set"""
    if not musical_key or not isinstance(musical_key, str):
        raise HTTPException(status_code=400, detail="musical_key must be a non-empty string")

    parts = musical_key.strip().replace("-", " ").split()
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid key format. Use e.g. 'C Major' or 'A minor'.")

    root_name = parts[0].upper().replace("♯", "#").replace("♭", "b")
    mode_word = "".join(parts[1:]).lower()
    is_major = "maj" in mode_word
    is_minor = "min" in mode_word

    if not (is_major or is_minor):
        raise HTTPException(status_code=400, detail="Key must specify Major or Minor")

    if root_name not in _NOTE_NAME_TO_PC:
        raise HTTPException(status_code=400, detail=f"Unsupported key root '{root_name}'")

    root_pc = _NOTE_NAME_TO_PC[root_name]
    intervals = _MAJOR_INTERVALS if is_major else _NAT_MINOR_INTERVALS
    return sorted({(root_pc + i) % 12 for i in intervals})

def _nearest_scale_note(target: int, scale_pcs: List[int]) -> int:
    """Find nearest MIDI note that belongs to the scale"""
    if not (0 <= target <= 127):
        target = max(0, min(127, target))

    best_note = target
    best_dist = 128
    target_oct = target // 12

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
    """Generate harmony parts from melody MIDI list"""
    # Build per-note keys
    keys_per_note = []
    
    if musical_keys and notes:
        ranges = musical_keys
        for i, note in enumerate(notes):
            start_time = note.get("start", 0)
            chosen_key = None
            
            for r in ranges:
                if start_time >= r["start"] and start_time < r["end"]:
                    chosen_key = r["key"]
                    break
            
            if not chosen_key:
                best_dist = float('inf')
                for r in ranges:
                    dist = abs(start_time - r["start"])
                    if dist < best_dist:
                        chosen_key = r["key"]
                        best_dist = dist
            
            keys_per_note.append(chosen_key or musical_key)
            
    elif musical_keys_by_index:
        for i in range(len(melody_midi)):
            if i < len(musical_keys_by_index):
                keys_per_note.append(musical_keys_by_index[i])
            else:
                keys_per_note.append(musical_keys_by_index[-1] if musical_keys_by_index else musical_key)
    else:
        keys_per_note = [musical_key] * len(melody_midi)

    third_up: List[int] = []
    fifth_up: List[int] = []

    for i, n in enumerate(melody_midi):
        if n is None:
            third_up.append(None)
            fifth_up.append(None)
            continue

        base = int(n)
        current_key = keys_per_note[i] if i < len(keys_per_note) else musical_key
        scale_pcs = _parse_key_to_scale_pcs(current_key)
        
        raw_maj_third = max(0, min(127, base + 4))
        raw_perfect_fifth = max(0, min(127, base + 7))

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

@app.get("/")
async def root():
    return {"message": "Harmony Generation API (Light) へようこそ！"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/analyze-pitch")
async def analyze_pitch(
    file: UploadFile = File(...),
    musical_key: str = Form(..., description="Key like 'C Major' or 'A minor'"),
) -> JSONResponse:
    """POST /analyze-pitch - Mock version for testing"""
    temp_path: Optional[str] = None
    try:
        temp_path = _save_upload_to_temp_wav(file)
        note_events = _analyze_pitch_mock(temp_path)
        melody_midi: List[int] = [ev["midi"] for ev in note_events]
        harmonies = generate_harmonies(melody_midi, musical_key, notes=note_events)

        response = {
            "model": "mock-pitch",
            "sample_rate": 22050,
            "key": musical_key,
            "notes": note_events,
            "melody_midi": melody_midi,
            "harmonies": harmonies,
        }
        return JSONResponse(content=response)
    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

@app.post("/analyze-pitch-json")
async def analyze_pitch_json(request: dict) -> JSONResponse:
    """SIM AI用のJSON形式で音声解析（base64対応）"""
    temp_path: Optional[str] = None
    try:
        if not isinstance(request, dict):
            raise HTTPException(status_code=400, detail="Request must be a JSON object")
        
        audio_data = None
        if request.get("wav_base64"):
            audio_data = decode_base64_audio(request["wav_base64"])
        else:
            raise HTTPException(status_code=400, detail="wav_base64が必要です")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_data)
            temp_path = tmp.name
        
        note_events = _analyze_pitch_mock(temp_path)
        melody_midi: List[int] = [ev["midi"] for ev in note_events]
        
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
            "model": "mock-pitch",
            "sample_rate": 22050,
            "key": musical_key,
            "musical_keys": musical_keys,
            "musical_keys_by_index": musical_keys_by_index,
            "notes": note_events,
            "melody_midi": melody_midi,
            "harmonies": harmonies,
        }
        return JSONResponse(content=response)
    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
