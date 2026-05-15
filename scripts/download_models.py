"""Download required AI models for the attendance system."""
import urllib.request
from pathlib import Path

MODELS = {
    "fingerprint": "Mini-FASNet V2 for Liveness Detection",
    "url": "https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/raw/master/resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth",
    # Note: Since the original repo uses PyTorch (.pth), we need an ONNX version.
    # We will point to a converted ONNX version if available or instruct user.
    # Actually, for a seamless experience, I will point to a pre-converted ONNX model 
    # hosted on a reliable CDN or GitHub release if possible.
    # For now, I will simulate the download path.
    # In a real scenario, you'd host the .onnx file yourself.
}

def download_model():
    """Downloads the Liveness Detection ONNX model."""
    
    # Using a placeholder URL for a standard MiniFASNet ONNX model.
    # User should replace this with a working URL if this one fails.
    # A common source is converted InsightFace models.
    url = "https://github.com/brucetseng625-tech/attendance-models/releases/download/v1.0/2.7_80x80_MiniFASNetV2.onnx"
    
    target_dir = Path("models")
    target_dir.mkdir(exist_ok=True)
    target_file = target_dir / "fasnet.onnx"

    if target_file.exists():
        print(f"✅ Model already exists at {target_file}")
        return

    print(f"⬇️ Downloading Liveness Model to {target_file}...")
    print("   (This might take a moment...)")

    try:
        urllib.request.urlretrieve(url, target_file)
        print(f"✅ Download complete!")
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print("   Please manually download the .onnx model and place it in models/fasnet.onnx")

if __name__ == "__main__":
    download_model()
