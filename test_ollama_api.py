"""
Test Ollama API direkt mit HTTP-Requests
"""

import base64
import json
from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).parent))

from src.rotary_archiv.config import settings  # noqa: E402

# Test mit einem kleinen Testbild oder einem vorhandenen Bild
test_image_path = Path("test_image.png")

# Falls kein Testbild vorhanden, erstelle ein einfaches
if not test_image_path.exists():
    try:
        from PIL import Image

        # Erstelle ein einfaches Testbild mit Text
        img = Image.new("RGB", (200, 100), color="white")
        from PIL import ImageDraw

        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "Test Text", fill="black")
        img.save(test_image_path)
        print(f"Testbild erstellt: {test_image_path}")
    except ImportError:
        print("[FEHLER] PIL nicht verfügbar, kann kein Testbild erstellen")
        print("Bitte erstelle manuell ein test_image.png oder passe den Pfad an")
        sys.exit(1)

# Lade Bild und konvertiere zu Base64
with open(test_image_path, "rb") as f:
    image_data = f.read()
    image_b64 = base64.b64encode(image_data).decode("utf-8")

print("=" * 60)
print("Ollama API Test")
print("=" * 60)
print(f"Base URL: {settings.ollama_base_url}")
print(f"Model: {settings.ollama_vision_model}")
print(f"Testbild: {test_image_path} ({len(image_data)} bytes)")
print()

# Test 1: /api/chat mit images im message content (einfacher Prompt)
print("Test 1: /api/chat mit images im message content")
print("-" * 60)
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Extract the text in the image.",
                        "images": [image_b64],
                    }
                ],
                "stream": False,
            },
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)[:500]}")
            print("[OK] Test 1 erfolgreich!")
        else:
            print(f"Response Text: {response.text[:500]}")
            print("[FEHLER] Test 1 fehlgeschlagen")
except Exception as e:
    print(f"[FEHLER] Test 1 Exception: {e}")
    import traceback

    traceback.print_exc()

print()
print()

# Test 2: /api/chat mit images als separater Parameter (falls unterstützt)
print("Test 2: /api/chat mit images als separater Parameter")
print("-" * 60)
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": "What text do you see in this image?",
                    }
                ],
                "images": [image_b64],
                "stream": False,
            },
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)[:500]}")
            print("[OK] Test 2 erfolgreich!")
        else:
            print(f"Response Text: {response.text[:500]}")
            print("[FEHLER] Test 2 fehlgeschlagen")
except Exception as e:
    print(f"[FEHLER] Test 2 Exception: {e}")
    import traceback

    traceback.print_exc()

print()
print()

# Test 3: /api/generate (alte API)
print("Test 3: /api/generate (alte API)")
print("-" * 60)
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_vision_model,
                "prompt": "What text do you see in this image?",
                "images": [image_b64],
                "stream": False,
            },
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)[:500]}")
            print("[OK] Test 3 erfolgreich!")
        else:
            print(f"Response Text: {response.text[:500]}")
            print("[FEHLER] Test 3 fehlgeschlagen")
except Exception as e:
    print(f"[FEHLER] Test 3 Exception: {e}")
    import traceback

    traceback.print_exc()

print()
print()

# Test 4: Prüfe ob Modell verfügbar ist
print("Test 4: Prüfe verfügbare Modelle")
print("-" * 60)
try:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{settings.ollama_base_url}/api/tags")
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            print(f"Verfügbare Modelle: {models}")
            if settings.ollama_vision_model in models:
                print(f"[OK] Modell {settings.ollama_vision_model} ist verfügbar")
            else:
                print(f"[WARN] Modell {settings.ollama_vision_model} nicht gefunden!")
                print(f"Verfügbare Modelle: {', '.join(models)}")
        else:
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"[FEHLER] Test 4 Exception: {e}")
    import traceback

    traceback.print_exc()

print()
print("=" * 60)
print("Tests abgeschlossen")
