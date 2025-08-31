from ultralytics import YOLO

model = YOLO("yolo11n.pt")  # Make sure this file is in your backend folder
results = model("captured.jpg")  # Replace with your actual image path

for box in results[0].boxes:
    cls_id = int(box.cls[0])
    label = model.names[cls_id]
    conf = box.conf[0]
    print(f"Detected {label} with confidence {conf:.2f}")