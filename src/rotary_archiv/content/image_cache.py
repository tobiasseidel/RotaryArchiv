from __future__ import annotations

import hashlib
import imghdr
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import httpx
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from src.rotary_archiv.config import settings
from src.rotary_archiv.core.models import CachedImage


def _parse_sizes(raw: str) -> list[int]:
    sizes: list[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError:
            continue
        if value > 0:
            sizes.append(value)
    uniq_sorted = sorted(set(sizes))
    return uniq_sorted or [64, 128, 256, 512]


def commons_file_url(filename: str) -> str:
    clean = (filename or "").strip()
    if clean.startswith("File:"):
        clean = clean[5:].strip()
    encoded = quote(clean.replace(" ", "_"))
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{encoded}"


class ImageCacheService:
    def __init__(self) -> None:
        self.base_path = Path(settings.image_cache_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.variant_sizes = _parse_sizes(settings.image_cache_sizes)
        self.max_source_bytes = max(
            1_000_000, int(settings.image_cache_max_source_bytes)
        )

    def _relative_media_url(self, file_path: Path) -> str:
        rel = file_path.relative_to(self.base_path).as_posix()
        return f"/media-cache/{rel}"

    def _source_hash(self, source_key: str) -> str:
        return hashlib.sha256(source_key.encode("utf-8")).hexdigest()

    def _download(
        self, source_url: str
    ) -> tuple[bytes, str | None, str | None, str | None]:
        headers = {
            "User-Agent": "RotaryArchiv/1.0 image-cache",
            "Accept": "image/*,*/*;q=0.8",
        }
        with httpx.Client(
            timeout=45.0, follow_redirects=True, headers=headers
        ) as client:
            resp = client.get(source_url)
            resp.raise_for_status()
            data = resp.content
            if not data:
                raise ValueError("Leeres Bild")
            if len(data) > self.max_source_bytes:
                raise ValueError("Quelldatei zu groß")
            content_type = (
                (resp.headers.get("content-type") or "").split(";")[0].strip()
            )
            if content_type and not content_type.startswith("image/"):
                guessed = imghdr.what(None, h=data[:64])
                if not guessed:
                    raise ValueError("Quelle ist kein Bild")
            return (
                data,
                content_type or None,
                resp.headers.get("etag"),
                resp.headers.get("last-modified"),
            )

    def cache_remote_image(
        self,
        db: Session,
        *,
        source_url: str,
        source_type: str,
        source_key: str | None = None,
    ) -> dict:
        source_url = (source_url or "").strip()
        if not source_url:
            raise ValueError("source_url fehlt")
        source_key_final = (source_key or source_url).strip()
        existing = (
            db.query(CachedImage)
            .filter(CachedImage.source_key == source_key_final)
            .first()
        )
        if existing:
            return {
                "source_url": existing.source_url,
                "main_url": (existing.variants_json or {}).get(
                    str(max(self.variant_sizes))
                )
                or self._relative_media_url(self.base_path / existing.original_path),
                "variants": existing.variants_json or {},
                "width": existing.width,
                "height": existing.height,
                "cached": True,
            }

        blob, mime, etag, last_modified = self._download(source_url)
        image_hash = self._source_hash(source_key_final)
        image_dir = self.base_path / image_hash
        image_dir.mkdir(parents=True, exist_ok=True)

        original_path = image_dir / "original.bin"
        original_path.write_bytes(blob)

        img = Image.open(BytesIO(blob)).convert("RGB")
        width, height = img.size
        variants: dict[str, str] = {}
        for size in self.variant_sizes:
            variant = ImageOps.contain(img, (size, size), Image.Resampling.LANCZOS)
            variant_file = image_dir / f"{size}.jpg"
            variant.save(variant_file, format="JPEG", quality=86, optimize=True)
            variants[str(size)] = self._relative_media_url(variant_file)

        row = CachedImage(
            source_type=source_type,
            source_key=source_key_final,
            source_url=source_url,
            mime_type=mime,
            original_path=original_path.relative_to(self.base_path).as_posix(),
            variants_json=variants,
            width=width,
            height=height,
            etag=etag,
            last_modified=last_modified,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {
            "source_url": source_url,
            "main_url": variants.get(str(max(self.variant_sizes))),
            "variants": variants,
            "width": width,
            "height": height,
            "cached": False,
        }

    def cache_commons_file(self, db: Session, filename: str) -> dict:
        clean = (filename or "").strip()
        if clean.startswith("File:"):
            clean = clean[5:].strip()
        if not clean:
            raise ValueError("commons filename fehlt")
        return self.cache_remote_image(
            db,
            source_url=commons_file_url(clean),
            source_type="commons",
            source_key=f"commons:{clean}",
        )
