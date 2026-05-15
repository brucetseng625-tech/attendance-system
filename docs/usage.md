# Usage Guide — AI Face Attendance System

## 1. Install

### Prerequisites

- **Python 3.10+**
- A webcam or IP camera (RTSP URL)

### Setup

```bash
# Clone the repository
git clone https://github.com/brucetseng625-tech/attendance-system.git
cd attendance-system

# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify your setup
bash scripts/verify_setup.sh
```

---

## 2. Configure

Edit `config.yaml` to customize the system:

| Section | Key | Description | Default |
|---|---|---|---|
| `camera` | `source` | Webcam index (`0`) or RTSP URL | `0` |
| `camera` | `fps` | Target frames per second | `30` |
| `detection` | `model` | YOLOv8 model size | `yolov8n.pt` |
| `detection` | `confidence` | Detection confidence threshold | `0.5` |
| `tracking` | `track_thresh` | BYTETrack detection threshold | `0.5` |
| `face_recognition` | `model` | InsightFace model (`buffalo_l` / `buffalo_s`) | `buffalo_l` |
| `face_recognition` | `match_threshold` | Cosine distance threshold (lower = stricter) | `0.4` |
| `attendance` | `cooldown_seconds` | Min seconds between same-person check-ins | `1800` |
| `zones` | `checkin.points` | Polygon vertices (normalized 0–1). Leave `[]` for default center zone. | `[]` |

### Choosing a Face Model

- `buffalo_l` — Most accurate, slower. Best for production.
- `buffalo_s` — Faster, slightly less accurate. Best for low-power devices.

### Using an IP Camera

To use an IP camera (RTSP stream) instead of a USB webcam:

1. Find the RTSP URL of your camera. Common examples:
   - **Hikvision**: `rtsp://admin:password@192.168.1.100:554/h264/ch1/main/av_stream`
   - **Dahua**: `rtsp://admin:password@192.168.1.100:554/cam/realmonitor?channel=1`
   - **Generic**: `rtsp://username:password@IP_ADDRESS:PORT/path`
2. Edit `config.yaml` and replace the `source` value with your RTSP URL:
   ```yaml
   camera:
     source: "rtsp://admin:password@192.168.1.100:554/h264/ch1/main/av_stream"
   ```
3. Save and run the application. The system will automatically switch to the IP stream.

---

## 3. Register Employees

Use the Streamlit UI to enroll people into the face database:

```bash
streamlit run src/ui/streamlit_app.py
```

1. Open the Streamlit app in your browser.
2. Switch to the **Register** tab.
3. Enter the employee name.
4. Upload a clear, front-facing photo (or use the webcam to capture).
5. Click **Register**. A face embedding is extracted and saved to `data/faces.db`.

> **Tips for good registration:**
> - Use well-lit, front-facing photos
> - Avoid heavy occlusion (masks, large sunglasses)
> - Register multiple photos per person for better accuracy

---

## 4. Run the Attendance Pipeline

Start the real-time detection and check-in loop:

```bash
python main.py
```

### How It Works

1. **Detection** — YOLOv8 detects people in each frame.
2. **Tracking** — BYTETrack assigns persistent IDs to each person.
3. **Zone Check** — Only people inside the check-in zone polygon trigger recognition.
4. **Face Recognition** — InsightFace extracts embeddings and matches against the registered database.
5. **Logging** — Matched check-ins are recorded in `data/attendance.db` with a cooldown to prevent duplicates.

### Controls

- Press **`q`** to quit.
- Green bounding boxes = person inside the check-in zone.
- Red bounding boxes = person outside the zone.

### Logs

- Console output shows INFO-level events.
- Detailed logs are written to `logs/attendance.log` (rotated daily, kept for 7 days).

---

## 5. Export Attendance Data

### CSV Export via Streamlit

1. Open the Streamlit app: `streamlit run src/ui/streamlit_app.py`
2. Switch to the **Reports** tab.
3. Select a date range.
4. Click **Export CSV** to download the attendance log.

### Direct Database Access

Attendance records are stored in SQLite at `data/attendance.db`:

```bash
sqlite3 data/attendance.db "SELECT * FROM attendance ORDER BY timestamp DESC LIMIT 10;"
```

Schema:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | Auto-increment |
| `name` | TEXT | Employee name |
| `event_type` | TEXT | `checkin` |
| `timestamp` | TEXT | ISO 8601 timestamp |
| `confidence` | REAL | Match confidence (0–1) |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Camera not opening | Check `camera.source` in `config.yaml`. Try a different index or verify RTSP URL. |
| No detections | Lower `detection.confidence` or use a larger YOLO model (e.g., `yolov8s.pt`). |
| Poor recognition accuracy | Register higher-quality photos. Lower `face_recognition.match_threshold`. |
| Slow performance | Switch to `buffalo_s` face model or use `yolov8n.pt` detection model. |
| Duplicate check-ins | Increase `attendance.cooldown_seconds`. |
