# AI Face Attendance System

Real-time face recognition attendance system powered by YOLOv8 detection, BYTETrack tracking, and InsightFace recognition.

## Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.10+**: Recommended version is **Python 3.11** (tested).
* **Webcam**: Built-in laptop camera or external USB webcam (tested with FaceTime HD Camera).
* **IP Camera (Optional)**: Supports RTSP protocol (e.g., Hikvision, Dahua).
* **Operating System**: macOS (tested), Linux, Windows (OpenCV support required).

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Camera    │────>│   Detector   │────>│   Zone Checker   │
│  (OpenCV)   │     │ YOLOv8 + BT  │     │  (Polygon ROI)   │
└─────────────┘     └──────┬───────┘     └────────┬─────────┘
                           │                      │
                    ┌──────▼───────┐     ┌────────▼─────────┐
                    │   Persons    │────>│  FaceRecognizer  │
                    │  in Zone     │     │  (InsightFace)   │
                    └──────────────┘     └────────┬─────────┘
                                                  │
                                           ┌──────▼───────┐
                                           │  FaceDatabase │
                                           │  (SQLite)     │
                                           └──────┬───────┘
                                                  │
                                           ┌──────▼───────┐
                                           │ AttendanceLog │
                                           │  (SQLite)     │
                                           └──────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| **Detection** | Ultralytics YOLOv8 + Supervision (BYTETrack) |
| **Recognition** | InsightFace ArcFace (buffalo_l / buffalo_s) |
| **Storage** | SQLite (face embeddings + attendance records) |
| **UI** | Streamlit (employee registration & reports) |
| **Video** | OpenCV (camera capture + rendering) |
| **Logging** | Loguru (console + rotating file logs) |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Register employees via Streamlit UI
streamlit run src/ui/streamlit_app.py

# 3. Run the attendance pipeline
python main.py
```

Press **`q`** to quit. See the [full usage guide](docs/usage.md) for configuration, export, and troubleshooting.

## IP Camera (RTSP) Setup

To use an IP camera instead of a USB webcam, update the `source` in `config.yaml`:

```yaml
camera:
  source: "rtsp://admin:12345@192.168.1.50:554/h264/ch1/main/av_stream"
```

**Supported Protocols:** RTSP (Real Time Streaming Protocol).
**Common Formats:**
- **Hikvision:** `rtsp://admin:password@IP:554/h264/ch1/main/av_stream`
- **Dahua:** `rtsp://admin:password@IP:554/cam/realmonitor?channel=1`
- **Axis:** `rtsp://root:pass@IP/axis-media/media.amp`

> **Tip:** Ensure your Mac and the IP camera are on the same network.

## Project Structure

```
attendance-system/
├── main.py                      # Entry point — real-time pipeline loop
├── config.yaml                  # Configuration (camera, models, zones)
├── requirements.txt             # Python dependencies
├── scripts/
│   └── verify_setup.sh          # Setup verification smoke test
├── src/
│   ├── config.py                # Config loader + project root resolver
│   ├── detector.py              # YOLOv8 detection + BYTETrack tracking
│   ├── face_recognizer.py       # InsightFace detection + embedding
│   ├── face_db.py               # SQLite face embedding storage & matching
│   ├── attendance_logger.py     # Attendance logging with cooldown
│   └── ui/
│       └── streamlit_app.py     # Streamlit UI (register + reports)
├── docs/
│   └── usage.md                 # Comprehensive usage guide
├── tests/                       # 74 unit + integration tests
└── data/                        # SQLite databases (gitignored)
```

## Configuration

All settings live in `config.yaml`:

- **Camera:** source (`0` for webcam, or RTSP URL), FPS
- **Detection:** YOLOv8 model, confidence threshold
- **Face Recognition:** model size, match threshold
- **Attendance:** database path, cooldown duration
- **Zones:** check-in polygon coordinates

See [docs/usage.md](docs/usage.md) for detailed configuration options.

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run integration tests only
pytest tests/test_integration.py -v

# Verify full setup
bash scripts/verify_setup.sh
```
