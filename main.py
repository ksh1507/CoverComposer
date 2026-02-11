from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from midiutil import MIDIFile
import os, random
from datetime import datetime

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUTPUT_DIR = os.path.join(STATIC_DIR, "output")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Global list to track history (in-memory)
HISTORY = []

SCALES = {
    "Happy": [60, 62, 64, 67, 69],
    "Sad": [60, 62, 63, 67, 68],
    "Calm": [60, 62, 65, 67, 69],
    "Energetic": [60, 64, 67, 69, 72]
}

INSTRUMENTS = {
    "Pop": 0,
    "Rock": 29,
    "Jazz": 26,
    "Electronic": 81
}

def generate_melody(scale):
    melody = [random.choice(scale)]
    for _ in range(31):
        melody.append(random.choice(scale))
    return melody

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
def generate(request: Request, mood: str = Form(...), genre: str = Form(...), tempo: int = Form(...), style: str = Form(...)):
    melody = generate_melody(SCALES[mood])
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    # Clean timestamp for display
    display_time = datetime.now().strftime("%H:%M")
    
    midi_file = f"track_{ts}.mid"
    midi_path = os.path.join(OUTPUT_DIR, midi_file)

    midi = MIDIFile(3)
    midi.addTempo(0, 0, tempo)
    midi.addProgramChange(0, 0, 0, INSTRUMENTS[genre])

    time = 0
    for note in melody:
        midi.addNote(0, 0, note, time, 0.5, 100)
        midi.addNote(1, 1, note - 12, time, 0.5, 80)
        midi.addNote(2, 9, 35, time, 0.25, 100)
        time += 0.5

    with open(midi_path, "wb") as f:
        midi.writeFile(f)

    # Add to history (Insert at beginning)
    track_info = {
        "mood": mood,
        "genre": genre, 
        "tempo": tempo,
        "style": style,
        "filename": midi_file,
        "time": display_time
    }
    HISTORY.insert(0, track_info)
    
    # Keep only last 5 tracks
    if len(HISTORY) > 5:
        HISTORY.pop()

    return templates.TemplateResponse("result.html", {
        "request": request,
        "mood": mood,
        "genre": genre,
        "tempo": tempo,
        "style": style,
        "audio": f"/static/output/{midi_file}",
        "filename": midi_file,
        "history": HISTORY
    })

@app.get("/download/{filename}")
def download(filename: str):
    return FileResponse(os.path.join(OUTPUT_DIR, filename))