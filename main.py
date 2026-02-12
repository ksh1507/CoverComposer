from fastapi import FastAPI, Request, Form, Response, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from midiutil import MIDIFile
from midi2audio import FluidSynth
import os, random, json
from datetime import datetime, timedelta

# --- DB IMPORTS ---
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt
from album_art import generate_cover_art
from sqlalchemy import text

app = FastAPI()

# --- DIRECTORIES ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUTPUT_DIR = os.path.join(STATIC_DIR, "output")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --- CONFIG ---
SECRET_KEY = "covercomposer_secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SQLALCHEMY_DATABASE_URL = "sqlite:///./covercomposer.db"

# --- CEREBRAS AI ---
from cerebras.cloud.sdk import Cerebras

# PASTE YOUR 5 KEYS HERE
CEREBRAS_API_KEYS = [
    "csk-tdjkyk942tf3j8rd43em5rftyph5xmw55f6855pr8nwktp3k",
    "csk-mrtxv8k2vjk349phm226n2p4m9hf38x5w5r4crew4pnewt46",
    "csk-86r8x25pen8xmt8htfn83n3v9f8n3fc25pxwk8w58xyt839j",
    "csk-8xpmc2nxntcjexf6ndmm3rphrhjntdrkmwkxe8tc2ex3fxx9",
    "csk-4dvdcynwe6kd2mk3kym9t9exwyxx3kj96wckd8kf45ej3xd4"
]

current_key_index = 0

def get_next_cerebras_key():
    global current_key_index
    key = CEREBRAS_API_KEYS[current_key_index]
    current_key_index = (current_key_index + 1) % len(CEREBRAS_API_KEYS)
    return key

def analyze_prompt_with_cerebras(prompt_text):
    """
    Uses Cerebras (Llama 3.1) with Key Rotation to analyze the prompt.
    """
    system_instruction = """
    You are an expert Musicologist and Producer AI. Analyze the user's story/prompt and output a JSON object.
    
    CRITICAL: Your "reasoning" must be a deep musical explanation (approx 2 sentences). 
    Explain WHY you chose the specific key, scale, or instrument based on music theory and the user's emotion.
    Example: "I selected the Phrygian Dominant scale to capture the 'ancient desert' vibe you described, paired with a Sitar to enhance the mystique."
    
    Output JSON format ONLY:
    {
        "mood": "string", "genre": "string", "tempo": int, "style": "string", "instrument": "string",
        "reasoning": "Deep musical explanation string", "lyrics": "4 lines of lyrics"
    }
    """
    
    # Try up to 5 times (once per key)
    # Valid models from user: llama-3.3-70b, llama3.1-8b, qwen-3-32b
    models = ["llama-3.3-70b", "llama3.1-8b", "qwen-3-32b"]
    
    for _ in range(len(CEREBRAS_API_KEYS)):
        try:
            api_key = get_next_cerebras_key()
            if "YOUR_KEY" in api_key: continue # Skip placeholders
            
            client = Cerebras(api_key=api_key)
            
            # Try models in order
            for model_name in models:
                try:
                    print(f"🤖 Sending prompt to Cerebras AI (Model: {model_name})...")
                    
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": prompt_text}
                        ],
                        response_format={"type": "json_object"}
                    )
                    
                    content = response.choices[0].message.content
                    data = json.loads(content)
                    
                    print(f"✅ Cerebras Success! Reasoning: {data.get('reasoning')}")
                    print(f"🎤 AI Lyrics: {data.get('lyrics')[:50]}...")
                    return data
                    
                except Exception as model_error:
                    if "404" in str(model_error) or "model_not_found" in str(model_error):
                        print(f"⚠️ Cerebras Model Not Found ({model_name}). Trying next...")
                        continue # Try next model with SAME key
                    else:
                        raise model_error # Re-raise if it's a key/rate limit issue to trigger key rotation
            
        except Exception as e:
            print(f"Cerebras Key Error (Key: {api_key[:5]}...): {e}")
            continue

    print("All Cerebras keys failed. Using Offline Magic Mode.")
    return simulate_ai_response(prompt_text)

def simulate_ai_response(text):
    text = text.lower()
    data = {
        "mood": "Happy", "genre": "Pop", "tempo": 120, "style": "Simple", 
        "instrument": "Grand Piano", 
        "reasoning": "I chose a bright Major scale to match the positive energy, using a Grand Piano for a classic, uplifting melody.",
        "lyrics": "The digital world is forcing a smile\nWe fake it 'til we make it for a while\nSystems down but the beat goes on\nSinging this simulated song"
    }
    
    if "sad" in text or "lonely" in text or "rain" in text or "dark" in text:
        data.update({
            "mood": "Sad", "tempo": 70, "genre": "Ambient", "instrument": "Cello", 
            "reasoning": "Selected a slow Minor scale with a Cello to evoke the melancholic and solitary atmosphere found in your request."
        })
    elif "cyber" in text or "future" in text or "neon" in text:
        data.update({
            "mood": "Energetic", "tempo": 130, "genre": "Electronic", "instrument": "Synth Lead", 
            "reasoning": "Opted for a high-tempo Electronic beat and Synth Leads to mirror the futuristic, neon-soaked cyberpunk aesthetic."
        })
    elif "rock" in text or "angry" in text or "fire" in text:
        data.update({
            "mood": "Energetic", "tempo": 150, "genre": "Rock", "instrument": "Electric Guitar", 
            "reasoning": "Chose an aggressive Electric Guitar riff and a driving Rock tempo to match the intensity and fiery emotion."
        })
    elif "jazz" in text or "smooth" in text or "bar" in text:
        data.update({
            "mood": "Calm", "tempo": 90, "genre": "Jazz", "instrument": "Saxophone", 
            "reasoning": "Selected a smooth Jazz progression with a Saxophone to create that smoky, relaxed lounge atmosphere."
        })
        
    return data
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    bio = Column(String, nullable=True, default="Music enthusiast 🎵")
    avatar_color = Column(String, default="#1db954")
    created_date = Column(String, default=datetime.now().strftime("%Y-%m-%d"))
    tracks = relationship("Track", back_populates="owner")

class Track(Base):
    __tablename__ = "tracks"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    wav_filename = Column(String, nullable=True)
    
    # Music Params
    mood = Column(String)
    genre = Column(String)
    tempo = Column(Integer, default=120)
    style = Column(String, default="Complex")
    instrument = Column(String, default="Grand Piano")
    
    # AI Metadata
    prompt = Column(Text, nullable=True) # The user's text
    ai_reasoning = Column(Text, nullable=True) # "Detected Sadness -> D Minor"
    
    created_at = Column(String)
    created_date = Column(String, default=datetime.now().strftime("%Y-%m-%d"))
    lyrics = Column(Text, nullable=True)
    
    # Social Params
    rating = Column(Integer, default=0) 
    is_favorite = Column(Integer, default=0)
    play_count = Column(Integer, default=0)
    duration = Column(Integer, default=0) 
    tags = Column(String, nullable=True)
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="tracks")
    cover_art = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# --- MIGRATION CHECK ---
def run_migrations():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE tracks ADD COLUMN cover_art VARCHAR"))
            print("✅ Migration: Added 'cover_art' column to tracks table.")
    except Exception as e:
        # Expected if column already exists
        pass

run_migrations()

# --- SECURITY ---
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: return None
    try:
        if token.startswith("Bearer "): token = token.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: return None
    except JWTError: return None
    return db.query(User).filter(User.username == username).first()

# --- MUSIC DATA ---
SCALES = {
    "Happy": [60, 62, 64, 65, 67, 69, 71, 72], # Major
    "Sad": [60, 62, 63, 65, 67, 68, 70, 72],   # Minor
    "Calm": [60, 62, 64, 67, 69],              # Pentatonic
    "Energetic": [60, 62, 63, 65, 67, 68, 71, 72], # Dorian-ish
    # We can expand this later with AI suggested scales
}

INSTRUMENTS = {
    "Grand Piano": 0, "Electric Piano": 4, "Acoustic Guitar": 24, "Electric Guitar": 29,
    "Violin": 40, "Cello": 42, "Trumpet": 56, "Saxophone": 65, "Flute": 73,
    "Synth Lead": 81, "Pad (Halo)": 94, "Orchestra Hit": 55, "Sitar": 104
}

# --- AI ENGINE ---
def generate_lyrics(mood, prompt=None):
    # Fallback only
    templates = {
        "Happy": ["The sun is shining bright today", "Walking down this golden way"],
        "Sad": ["The rain falls on the window pane", "Shadows whisper your name"],
        "Energetic": ["Feel the rhythm in your soul", "We are losing all control"],
        "Calm": ["Breathe the air, soft and deep", "Drifting into peaceful sleep"]
    }
    lines = templates.get(mood, templates["Happy"])
    random.shuffle(lines)
    return "\n".join(lines)

# --- MUSIC LOGIC ---
def markov_melody(scale, length=32):
    curr = random.choice(scale)
    melody = [curr]
    for _ in range(length - 1):
        if random.random() > 0.5: curr = random.choice(scale) # Simple randomness for now
        melody.append(curr)
    return melody

def apply_style(melody, style, mood):
    processed = []
    for note in melody:
        dur, vel = 1.0, 100
        if style == "Complex":
            if mood == "Energetic": dur, vel = 0.5, 120
            elif mood == "Calm": dur, vel = 2.0, 80
        processed.append((note, dur, vel))
    return processed

def add_drums(midi, duration, mood):
    track, channel = 2, 9
    pattern = [(35, 0), (38, 1.0)] # Kick Snare basic
    if mood == "Energetic": pattern = [(35, 0), (42, 0.5), (38, 1.0), (42, 1.5)]
    elif mood == "Sad": pattern = [(35, 0)] # Minimal
    
    time = 0
    while time < duration:
        for note, offset in pattern: midi.addNote(track, channel, note, time + offset, 0.5, 100)
        time += 2

# --- ROUTES ---
@app.post("/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == username).first(): return RedirectResponse(url="/register", status_code=303)
    new_user = User(username=username, hashed_password=pwd_context.hash(password))
    db.add(new_user); db.commit()
    return RedirectResponse(url="/login", status_code=303)

@app.post("/login")
def login(response: Response, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.hashed_password): return RedirectResponse(url="/login?error=Invalid", status_code=303)
    token = jwt.encode({"sub": user.username}, SECRET_KEY, algorithm=ALGORITHM)
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return resp

@app.get("/logout")
def logout(response: Response):
    resp = RedirectResponse(url="/login", status_code=303); resp.delete_cookie("access_token"); return resp

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request): return templates.TemplateResponse("login.html", {"request": request})
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request): return templates.TemplateResponse("register.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
def home(request: Request, user: User = Depends(get_current_user)):
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("index.html", {"request": request, "user": user, "instruments": INSTRUMENTS})

@app.post("/", response_class=HTMLResponse)
def generate(
    request: Request,
    prompt: str = Form(None), # Text prompt for AI
    mood: str = Form(None), genre: str = Form(None), tempo: int = Form(120),
    style: str = Form("Complex"), instrument: str = Form(None), 
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not user: return RedirectResponse(url="/login")

    ai_data = {}
    
    # 1. AI Logic
    if prompt and len(prompt) > 5:
        # Use Cerebras
        ai_data = analyze_prompt_with_cerebras(prompt)
        mood = ai_data.get("mood", "Happy")
        genre = ai_data.get("genre", "Pop")
        tempo = ai_data.get("tempo", 120)
        style = ai_data.get("style", "Complex")
        inst_name = ai_data.get("instrument", "Grand Piano")
        
        # Validations
        if inst_name not in INSTRUMENTS: inst_name = "Grand Piano"
        instrument = str(INSTRUMENTS[inst_name])
        
        # If manual instrument ID was passed, convert back? No, AI takes precedence if prompt exists.
    else:
        # Manual Fallback
        if not mood: mood = "Happy"
        if not instrument: instrument = "0"
        ai_data["reasoning"] = "Manual creation"

    # 2. Generation Logic
    scale = SCALES.get(mood, SCALES["Happy"])
    melody = markov_melody(scale)
    styled_melody = apply_style(melody, style, mood)
    
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    midi_file = f"{ts}.mid"
    wav_file = f"{ts}.wav"
    midi_path = os.path.join(OUTPUT_DIR, midi_file)
    wav_path = os.path.join(OUTPUT_DIR, wav_file)

    midi = MIDIFile(3)
    midi.addTempo(0, 0, tempo)
    midi.addProgramChange(0, 0, 0, int(instrument))
    
    time = 0
    for note, dur, vel in styled_melody:
        midi.addNote(0, 0, note, time, dur, vel)
        if time % 2 == 0: midi.addNote(1, 1, note - 12, time, 2.0, vel - 20) # Bass
        time += dur
    add_drums(midi, time, mood)

    with open(midi_path, "wb") as f: midi.writeFile(f)
    
    # WAV Conversion
    wav_ready = False
    try: FluidSynth(os.path.join(BASE_DIR, "soundfont.sf2")).midi_to_audio(midi_path, wav_path); wav_ready = True
    except: pass

    # Use AI lyrics if available, else fallback
    song_lyrics = ai_data.get("lyrics")
    if not song_lyrics:
        song_lyrics = generate_lyrics(mood)

    # 4. Generate Album Art
    cover_filename = f"{ts}.png"
    cover_path = os.path.join(OUTPUT_DIR, cover_filename)
    try:
        generate_cover_art(mood, genre, tempo, cover_path)
    except Exception as e:
        print(f"Album Art Error: {e}")
        cover_filename = None

    # 3. DB Save
    new_track = Track(
        filename=midi_file, wav_filename=wav_file if wav_ready else None,
        mood=mood, genre=genre, tempo=tempo, style=style,
        instrument=list(INSTRUMENTS.keys())[list(INSTRUMENTS.values()).index(int(instrument))],
        prompt=prompt,
        ai_reasoning=ai_data.get("reasoning", "Manual"),
        created_at=datetime.now().strftime("%H:%M"),
        created_date=datetime.now().strftime("%Y-%m-%d"),
        lyrics=song_lyrics, duration=int(time), owner_id=user.id,
        cover_art=cover_filename
    )
    db.add(new_track); db.commit()
    
    history = db.query(Track).filter(Track.owner_id == user.id).order_by(Track.id.desc()).limit(5).all()

    return templates.TemplateResponse("result.html", {
        "request": request, "mood": mood, "genre": genre, 
        "ai_reasoning": ai_data.get("reasoning"), "prompt": prompt,
        "audio": f"/static/output/{midi_file}", "wav_filename": wav_file if wav_ready else None,
        "lyrics": song_lyrics, "history": history, "user": user,
        "cover_art": cover_filename
    })

@app.get("/download/{filename}")
def download(filename: str): return FileResponse(os.path.join(OUTPUT_DIR, filename))

# --- DASHBOARD & PROFILE (Simplified) ---
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user: return RedirectResponse("/login")
    all_tracks = db.query(Track).filter(Track.owner_id == user.id).order_by(Track.id.desc()).all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": user, 
        "tracks": all_tracks, 
        "total_tracks": len(all_tracks),
        "total_plays": sum(t.play_count for t in all_tracks), 
        "favorites_count": sum(1 for t in all_tracks if t.is_favorite),
        "activity_data": [] # Simplified for now
    })

@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user: return RedirectResponse("/login")
    tracks = db.query(Track).filter(Track.owner_id == user.id).all()
    return templates.TemplateResponse("profile.html", {
        "request": request, "user": user, 
        "total_tracks": len(tracks), "total_duration": sum(t.duration for t in tracks),
        "member_since": user.created_date
    })

# --- ACTION ROUTES ---
@app.post("/profile/update")
def update_profile(bio: str = Form(...), avatar_color: str = Form(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user: user.bio = bio; user.avatar_color = avatar_color; db.commit()
    return RedirectResponse("/profile", status_code=303)

@app.post("/track/{track_id}/play")
def play_track(track_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(Track).filter(Track.id == track_id).first()
    if t: t.play_count += 1; db.commit()
    return {"success": True}

@app.post("/track/{track_id}/delete")
def delete_track(track_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(Track).filter(Track.id == track_id).first()
    if t: db.delete(t); db.commit()
    return RedirectResponse("/dashboard", status_code=303)