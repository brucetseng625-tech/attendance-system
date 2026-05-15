"""Download required AI models for the attendance system."""
import urllib.request
from pathlib import Path

MODELS = {
    "fingerprint": "Mini-FASNet V2 for Liveness Detection",
    "url": "https://huggingface.co/garciafido/minifasnet-v2-anti-spoofing-onnx/resolve/main/minifasnet_v2.onnx",
}

def download_model():
    """Downloads the Liveness Detection ONNX model."""
    
    # Using a reliable HuggingFace mirror for the ONNX model.
    url = MODELS["url"]
    
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
