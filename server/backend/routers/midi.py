from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
import os
import json
import unicodedata
import re

router = APIRouter(
    prefix="/midi",
    tags=["midi"]
)


def remove_vietnamese_diacritics(text):
    """
    Remove Vietnamese diacritics from text
    Example: "Lạc Trôi" -> "Lac Troi"
    """
    # Normalize to NFD (decomposed form)
    nfd = unicodedata.normalize('NFD', text)
    # Remove combining characters (diacritics)
    without_diacritics = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    # Additional Vietnamese character replacements
    replacements = {
        'Đ': 'D', 'đ': 'd',
        'Ð': 'D', 'ð': 'd'
    }
    for viet_char, latin_char in replacements.items():
        without_diacritics = without_diacritics.replace(viet_char, latin_char)
    return without_diacritics


def sanitize_filename(filename):
    """Sanitize filename for safe filesystem use"""
    # Remove extension temporarily
    name, ext = os.path.splitext(filename)
    
    # Remove diacritics
    name = remove_vietnamese_diacritics(name)
    
    # Remove invalid characters, keep only alphanumeric, spaces, hyphens, underscores
    name = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces with hyphens
    name = re.sub(r'\s+', '-', name)
    # Remove leading/trailing hyphens
    name = name.strip('-')
    # Lowercase
    name = name.lower()
    
    # Ensure .mid extension
    if ext.lower() not in ['.mid', '.midi']:
        ext = '.mid'
    
    return name + ext


def get_midi_directory():
    """Get the midi_files directory path"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    return os.path.join(root_dir, "midi_files")


def post_process_midi(midi_data, min_note_duration=0.08, max_polyphony=2):
    """
    Post-process MIDI for keyboard playback.
    DOES NOT change timing - only filters notes and limits polyphony.
    
    Args:
        midi_data: PrettyMIDI object
        min_note_duration: Minimum note duration in seconds (80ms)
        max_polyphony: Maximum simultaneous notes (2 = melody + harmony)
    
    Returns:
        PrettyMIDI object with filtered notes
    """
    import pretty_midi
    
    for instrument in midi_data.instruments:
        if instrument.is_drum:
            continue
        
        original_count = len(instrument.notes)
        if original_count == 0:
            continue
        
        # Step 1: Filter short notes and constrain pitch range
        filtered_notes = []
        for note in instrument.notes:
            duration = note.end - note.start
            if duration < min_note_duration:
                continue
            
            # Constrain pitch to playable range (C3=48 to B5=83)
            pitch = note.pitch
            while pitch < 48:
                pitch += 12
            while pitch > 83:
                pitch -= 12
            
            # Keep original timing! Only change pitch if needed
            if pitch != note.pitch:
                new_note = pretty_midi.Note(
                    velocity=note.velocity,
                    pitch=pitch,
                    start=note.start,
                    end=note.end
                )
                filtered_notes.append(new_note)
            else:
                filtered_notes.append(note)
        
        # Step 2: Limit polyphony - group by time (10ms window)
        filtered_notes.sort(key=lambda n: n.start)
        
        final_notes = []
        time_slots = {}
        
        for note in filtered_notes:
            # Group notes within 10ms window
            slot = round(note.start * 100) / 100
            if slot not in time_slots:
                time_slots[slot] = []
            time_slots[slot].append(note)
        
        for slot in sorted(time_slots.keys()):
            notes_at_slot = time_slots[slot]
            # Keep highest pitched notes (melody) with highest velocity
            notes_at_slot.sort(key=lambda n: (-n.velocity, -n.pitch))
            final_notes.extend(notes_at_slot[:max_polyphony])
        
        instrument.notes = sorted(final_notes, key=lambda n: n.start)
        print(f"[PostProcess] {original_count} -> {len(instrument.notes)} notes")
    
    return midi_data








@router.get("/list")
async def list_midi_files():
    """
    List all MIDI files available on server for sync.
    Returns list of files with filename, url, and size.
    """
    try:
        midi_dir = get_midi_directory()
        
        if not os.path.exists(midi_dir):
            return {"files": [], "count": 0}
        
        files = []
        for filename in os.listdir(midi_dir):
            if filename.lower().endswith(('.mid', '.midi')):
                file_path = os.path.join(midi_dir, filename)
                files.append({
                    "filename": filename,
                    "url": f"/midi/{filename}",
                    "size": os.path.getsize(file_path)
                })
        
        return {
            "files": files,
            "count": len(files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_midi_file(file: UploadFile = File(...)):
    """
    Upload a MIDI file to server
    
    Args:
        file: MIDI file to upload
        
    Returns:
        dict with success status, display_name, and url
    """
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        if not file.filename.lower().endswith(('.mid', '.midi')):
            raise HTTPException(status_code=400, detail="Only MIDI files (.mid, .midi) are allowed")
        
        # Extract display name (original with diacritics) and sanitized filename
        display_name = os.path.splitext(file.filename)[0]  # Remove extension for display
        sanitized_filename = sanitize_filename(file.filename)
        
        # Find midi_files directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        midi_dir = os.path.join(root_dir, "midi_files")
        update_info_path = os.path.join(root_dir, "update_info.json")
        
        # Create midi_files directory if it doesn't exist
        os.makedirs(midi_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(midi_dir, sanitized_filename)
        
        # Read and write file content
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Update update_info.json
        if os.path.exists(update_info_path):
            with open(update_info_path, 'r', encoding='utf-8') as f:
                update_info = json.load(f)
            
            # Check if already exists in library
            midi_library = update_info.get("midi_library", [])
            existing = next((item for item in midi_library if item.get("name") == display_name), None)
            
            if not existing:
                # Add new entry
                midi_library.append({
                    "name": display_name,
                    "url": f"midi_files/{sanitized_filename}"
                })
                update_info["midi_library"] = midi_library
                
                # Write back
                with open(update_info_path, 'w', encoding='utf-8') as f:
                    json.dump(update_info, f, indent=4, ensure_ascii=False)
        
        return {
            "success": True,
            "display_name": display_name,
            "filename": sanitized_filename,
            "url": f"midi_files/{sanitized_filename}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{filename}")
async def get_midi_file(filename: str):
    """Serve a MIDI file"""
    try:
        # Find midi_files directory
        # backend/routers/midi.py -> backend/routers -> backend -> root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        midi_dir = os.path.join(root_dir, "midi_files")
        
        file_path = os.path.join(midi_dir, filename)
        
        if not os.path.exists(file_path):
            # Try looking in current directory if running differently
            if os.path.exists(os.path.join("midi_files", filename)):
                file_path = os.path.join("midi_files", filename)
            else:
                raise HTTPException(status_code=404, detail="MIDI file not found")
        
        return FileResponse(file_path, media_type="audio/midi", filename=filename)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert")
async def convert_mp3_to_midi(file: UploadFile = File(...)):
    """
    Convert MP3/audio file to MIDI on server.
    Client uploads audio, server converts to MIDI and saves to midi_files.
    
    Args:
        file: Audio file (MP3, WAV, etc.)
    
    Returns:
        - success: bool
        - filename: MIDI filename for sync
        - message: status message
    """
    import tempfile
    import shutil
    
    # Validate file extension
    allowed_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.m4a']
    original_name = file.filename or "unknown.mp3"
    ext = os.path.splitext(original_name)[1].lower()
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported format. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        # Sanitize filename for console output (avoid encoding errors)
        safe_print_name = original_name.encode('ascii', 'replace').decode('ascii')
        print(f"[MIDI Convert] Received: {safe_print_name} ({len(content)} bytes)")
        
        try:
            # Import basic-pitch for conversion
            from basic_pitch.inference import predict
            from basic_pitch import ICASSP_2022_MODEL_PATH
            
            print("[MIDI Convert] Running Basic Pitch conversion...")
            
            # Run prediction with stricter thresholds
            model_output, midi_data, note_events = predict(
                tmp_path,
                ICASSP_2022_MODEL_PATH,
                onset_threshold=0.6,  # Higher = less sensitive (was 0.5)
                frame_threshold=0.4,  # Higher = cleaner notes (was 0.3)
                minimum_note_length=127,  # Longer min note length (was 58)
                minimum_frequency=65.0,  # Skip very low frequencies (was 32)
                maximum_frequency=1500.0,  # Skip very high frequencies (was 2000)
            )
            
            # Post-process MIDI to improve quality
            midi_data = post_process_midi(midi_data)
            
            # Generate output filename
            base_name = os.path.splitext(original_name)[0]
            safe_name = remove_vietnamese_diacritics(base_name)
            safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in safe_name)
            safe_name = safe_name.strip().replace(" ", "-").lower()
            midi_filename = f"{safe_name}.mid"
            
            # Save to midi_files directory
            midi_dir = get_midi_directory()
            os.makedirs(midi_dir, exist_ok=True)
            output_path = os.path.join(midi_dir, midi_filename)
            
            midi_data.write(output_path)
            
            # Count notes after processing
            note_count = sum(len(inst.notes) for inst in midi_data.instruments)
            print(f"[MIDI Convert] Success: {midi_filename} ({note_count} notes after processing)")
            
            return {
                "success": True,
                "filename": midi_filename,
                "url": f"/midi/{midi_filename}",
                "note_count": note_count,
                "message": f"Converted successfully ({note_count} notes)"
            }
            
        except ImportError as e:
            raise HTTPException(
                status_code=500,
                detail="basic-pitch not installed on server. Run: pip install basic-pitch"
            )
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        # Safe print to avoid encoding errors with Vietnamese
        error_msg = str(e).encode('ascii', 'replace').decode('ascii')
        tb = traceback.format_exc().encode('ascii', 'replace').decode('ascii')
        print(f"[MIDI Convert] Error: {error_msg}\n{tb}")
        raise HTTPException(status_code=500, detail=str(e))
