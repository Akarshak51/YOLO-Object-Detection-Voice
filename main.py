from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import base64, re, cv2, numpy as np
from ultralytics import YOLO
import pyttsx3, threading

lock = threading.Lock()

def speak(text):
    with lock:
        tts_engine.say(text)
        tts_engine.runAndWait()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model = YOLO("yolo11n.pt")
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 160)

def estimate_distance(box_coords, frame_height):
    box_height = box_coords[3] - box_coords[1]
    if box_height <= 0:
        return "-"
    return round((frame_height / box_height) * 0.5, 2)

def narrate_analysis(analysis):
    narration = []
    for item in analysis:
        obj = item["object"]
        dist = item["distance_m"]
        if dist == "-":
            narration.append(f"{obj} detected, but distance could not be estimated.")
        else:
            narration.append(f"{obj} detected approximately {dist} meters ahead.")
    full_text = " ".join(narration)

    def speak():
        tts_engine.say(full_text)
        tts_engine.runAndWait()

    threading.Thread(target=speak, daemon=True).start()

@app.post("/upload")
async def upload_image(request: Request):
    try:
        data = await request.json()
        image_data = re.sub('^data:image/.+;base64,', '', data['image'])
        image_bytes = base64.b64decode(image_data)
        np_img = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Image decoding failed")

        results = model(img)
        frame_height = img.shape[0]
        analysis = []

        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            coords = box.xyxy[0].tolist()
            distance = estimate_distance(coords, frame_height)
            analysis.append({
                "object": label,
                "distance_m": distance,
                "bbox": [round(c, 2) for c in coords]
            })

        if analysis:
            narrate_analysis(analysis)
        else:
            threading.Thread(target=lambda: tts_engine.say("No objects detected.") or tts_engine.runAndWait(), daemon=True).start()

        return {"analysis": analysis}

    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "trace": traceback.format_exc(),
            "analysis": [{"object": "Error during analysis", "distance_m": "-", "bbox": []}]
        }