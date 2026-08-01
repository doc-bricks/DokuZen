#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Image Tools
==============================
Bildkonvertierung, ICO-Builder und Bildverarbeitung.
"""

from pathlib import Path
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from enum import Enum
import io

from utils.logger import LoggerMixin

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ImageFormat(Enum):
    """Unterstützte Bildformate."""
    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"
    GIF = "gif"
    BMP = "bmp"
    WEBP = "webp"
    TIFF = "tiff"
    ICO = "ico"
    PDF = "pdf"


@dataclass
class ImageInfo:
    """Informationen über ein Bild."""
    path: str
    format: str
    width: int
    height: int
    mode: str
    file_size: int
    has_transparency: bool
    dpi: Optional[Tuple[int, int]] = None


class ImageConverter(LoggerMixin):
    """
    Konvertiert Bilder zwischen verschiedenen Formaten.
    
    Features:
    - Format-Konvertierung
    - Größenanpassung
    - Qualitätseinstellung
    - Batch-Verarbeitung
    """
    
    SUPPORTED_FORMATS = {
        ".png": ImageFormat.PNG,
        ".jpg": ImageFormat.JPEG,
        ".jpeg": ImageFormat.JPEG,
        ".gif": ImageFormat.GIF,
        ".bmp": ImageFormat.BMP,
        ".webp": ImageFormat.WEBP,
        ".tiff": ImageFormat.TIFF,
        ".tif": ImageFormat.TIFF,
        ".ico": ImageFormat.ICO,
        ".pdf": ImageFormat.PDF,
    }
    
    def __init__(self):
        if not PIL_AVAILABLE:
            self.logger.warning("Pillow nicht verfügbar")
    
    def get_image_info(self, path: str) -> Optional[ImageInfo]:
        """Gibt Informationen über ein Bild zurück."""
        if not PIL_AVAILABLE:
            return None
        
        try:
            file_path = Path(path)
            file_size = file_path.stat().st_size
            
            with Image.open(path) as img:
                has_alpha = img.mode in ('RGBA', 'LA', 'PA') or \
                           (img.mode == 'P' and 'transparency' in img.info)
                
                dpi = img.info.get('dpi')
                
                return ImageInfo(
                    path=path,
                    format=img.format or "",
                    width=img.width,
                    height=img.height,
                    mode=img.mode,
                    file_size=file_size,
                    has_transparency=has_alpha,
                    dpi=dpi
                )
        except Exception as e:
            self.logger.error(f"Fehler beim Lesen: {e}")
            return None
    
    def convert(self, input_path: str, output_path: str,
                target_format: ImageFormat = None,
                resize: Tuple[int, int] = None,
                quality: int = 85,
                keep_transparency: bool = True) -> bool:
        """
        Konvertiert ein Bild.
        
        Args:
            input_path: Eingabedatei
            output_path: Ausgabedatei
            target_format: Zielformat (aus Dateiendung wenn None)
            resize: Neue Größe (width, height)
            quality: JPEG-Qualität (1-100)
            keep_transparency: Transparenz beibehalten
            
        Returns:
            True bei Erfolg
        """
        if not PIL_AVAILABLE:
            return False
        
        try:
            with Image.open(input_path) as img:
                # Format aus Ausgabepfad ermitteln
                out_path = Path(output_path)
                if target_format is None:
                    target_format = self.SUPPORTED_FORMATS.get(
                        out_path.suffix.lower(), ImageFormat.PNG
                    )
                
                # Größe anpassen
                if resize:
                    img = img.resize(resize, Image.Resampling.LANCZOS)
                
                # Transparenz handhaben
                if target_format in [ImageFormat.JPEG, ImageFormat.JPG, ImageFormat.BMP, ImageFormat.PDF]:
                    if img.mode in ('RGBA', 'LA', 'PA') or (img.mode == 'P' and 'transparency' in img.info):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode in ('RGBA', 'LA', 'PA'):
                            background.paste(img, mask=img.split()[-1])
                        else:
                            rgba_img = img.convert('RGBA')
                            background.paste(rgba_img, mask=rgba_img.split()[3])
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                
                # Speichern
                save_kwargs = {}
                
                if target_format in [ImageFormat.JPEG, ImageFormat.JPG]:
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                elif target_format == ImageFormat.PNG:
                    save_kwargs['optimize'] = True
                elif target_format == ImageFormat.WEBP:
                    save_kwargs['quality'] = quality
                elif target_format == ImageFormat.PDF:
                    save_kwargs['format'] = 'PDF'
                
                img.save(output_path, **save_kwargs)
                
                self.logger.info(f"Konvertiert: {input_path} -> {output_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Konvertierung fehlgeschlagen: {e}")
            return False
    
    def batch_convert(self, input_files: List[str], output_dir: str,
                      target_format: ImageFormat,
                      resize: Tuple[int, int] = None,
                      quality: int = 85) -> Dict[str, bool]:
        """Batch-Konvertierung mehrerer Bilder."""
        results = {}
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for input_file in input_files:
            in_path = Path(input_file)
            out_file = output_path / f"{in_path.stem}.{target_format.value}"
            
            results[input_file] = self.convert(
                input_file, str(out_file),
                target_format, resize, quality
            )
        
        return results


class IcoBuilder(LoggerMixin):
    """
    Erstellt ICO-Dateien mit mehreren Größen.
    
    Standard-Größen für Windows-Icons:
    - 16x16 (klein)
    - 24x24
    - 32x32 (normal)
    - 48x48
    - 64x64
    - 128x128
    - 256x256 (groß)
    """
    
    STANDARD_SIZES = [16, 24, 32, 48, 64, 128, 256]
    
    PRESETS = {
        "minimal": [16, 32],
        "standard": [16, 32, 48, 256],
        "full": [16, 24, 32, 48, 64, 128, 256],
        "web": [16, 32, 180, 192],  # Für Favicons
    }
    
    def __init__(self):
        if not PIL_AVAILABLE:
            self.logger.warning("Pillow nicht verfügbar")
    
    def create_ico(self, source_path: str, output_path: str,
                   sizes: List[int] = None,
                   preset: str = None) -> bool:
        """
        Erstellt eine ICO-Datei aus einem Bild.
        
        Args:
            source_path: Quellbild (PNG empfohlen)
            output_path: Ausgabe .ico Datei
            sizes: Liste von Größen (z.B. [16, 32, 48])
            preset: Preset-Name ('minimal', 'standard', 'full', 'web')
            
        Returns:
            True bei Erfolg
        """
        if not PIL_AVAILABLE:
            return False
        
        # Größen bestimmen
        if preset and preset in self.PRESETS:
            sizes = self.PRESETS[preset]
        elif sizes is None:
            sizes = self.PRESETS["standard"]
        
        # Größen sortieren
        sizes = sorted(set(sizes))
        
        try:
            with Image.open(source_path) as img:
                # In RGBA konvertieren falls nötig
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Icons in verschiedenen Größen erstellen
                icons = []
                for size in sizes:
                    # Lanczos-Resampling für beste Qualität
                    resized = img.resize((size, size), Image.Resampling.LANCZOS)
                    icons.append(resized)
                
                # Als ICO speichern
                # BUGSWEEP-30: append_images=None (bei nur einer Größe) wirft je nach Pillow-
                # Version TypeError; eine leere Liste ist immer gültig.
                icons[0].save(
                    output_path,
                    format='ICO',
                    sizes=[(s, s) for s in sizes],
                    append_images=icons[1:]
                )
                
                self.logger.info(f"ICO erstellt: {output_path} ({len(sizes)} Größen)")
                return True
                
        except Exception as e:
            self.logger.error(f"ICO-Erstellung fehlgeschlagen: {e}")
            return False
    
    def extract_sizes(self, ico_path: str, output_dir: str) -> List[str]:
        """
        Extrahiert alle Größen aus einer ICO-Datei.
        
        Args:
            ico_path: ICO-Datei
            output_dir: Ausgabeverzeichnis
            
        Returns:
            Liste der extrahierten Dateien
        """
        if not PIL_AVAILABLE:
            return []
        
        extracted = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            with Image.open(ico_path) as ico:
                # ICO kann mehrere Frames haben
                for i, size in enumerate(ico.info.get('sizes', [(ico.width, ico.height)])):
                    ico.seek(i)
                    
                    out_file = output_path / f"icon_{size[0]}x{size[1]}.png"
                    ico.save(str(out_file), 'PNG')
                    extracted.append(str(out_file))
                    
        except Exception as e:
            self.logger.error(f"Extraktion fehlgeschlagen: {e}")
        
        return extracted
    
    def create_favicon_package(self, source_path: str, output_dir: str) -> Dict[str, str]:
        """
        Erstellt ein komplettes Favicon-Paket für Websites.
        
        Erstellt:
        - favicon.ico (16, 32)
        - favicon-16x16.png
        - favicon-32x32.png
        - apple-touch-icon.png (180x180)
        - android-chrome-192x192.png
        - android-chrome-512x512.png
        """
        if not PIL_AVAILABLE:
            return {}
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        files = {}
        
        try:
            with Image.open(source_path) as img:
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # favicon.ico
                ico_path = output_path / "favicon.ico"
                self.create_ico(source_path, str(ico_path), [16, 32])
                files["favicon.ico"] = str(ico_path)
                
                # PNGs in verschiedenen Größen
                png_sizes = {
                    "favicon-16x16.png": 16,
                    "favicon-32x32.png": 32,
                    "apple-touch-icon.png": 180,
                    "android-chrome-192x192.png": 192,
                    "android-chrome-512x512.png": 512,
                }
                
                for filename, size in png_sizes.items():
                    resized = img.resize((size, size), Image.Resampling.LANCZOS)
                    out_file = output_path / filename
                    resized.save(str(out_file), 'PNG')
                    files[filename] = str(out_file)
                
                # Manifest erstellen
                manifest = {
                    "name": "",
                    "short_name": "",
                    "icons": [
                        {"src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png"},
                        {"src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png"}
                    ],
                    "theme_color": "#ffffff",
                    "background_color": "#ffffff",
                    "display": "standalone"
                }
                
                import json
                manifest_path = output_path / "site.webmanifest"
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, indent=2)
                files["site.webmanifest"] = str(manifest_path)
                
                self.logger.info(f"Favicon-Paket erstellt: {len(files)} Dateien")
                
        except Exception as e:
            self.logger.error(f"Favicon-Paket fehlgeschlagen: {e}")
        
        return files


class ImageProcessor(LoggerMixin):
    """
    Bildverarbeitungs-Werkzeuge.
    
    Features:
    - Filter (Blur, Sharpen, etc.)
    - Anpassungen (Helligkeit, Kontrast)
    - Transformationen (Drehen, Spiegeln)
    - Zuschneiden
    """
    
    def __init__(self):
        if not PIL_AVAILABLE:
            self.logger.warning("Pillow nicht verfügbar")
    
    def apply_filter(self, input_path: str, output_path: str,
                     filter_name: str) -> bool:
        """Wendet einen Filter an."""
        if not PIL_AVAILABLE:
            return False
        
        filters = {
            "blur": ImageFilter.BLUR,
            "sharpen": ImageFilter.SHARPEN,
            "contour": ImageFilter.CONTOUR,
            "detail": ImageFilter.DETAIL,
            "edge_enhance": ImageFilter.EDGE_ENHANCE,
            "emboss": ImageFilter.EMBOSS,
            "smooth": ImageFilter.SMOOTH,
        }
        
        if filter_name not in filters:
            self.logger.error(f"Unbekannter Filter: {filter_name}")
            return False
        
        try:
            with Image.open(input_path) as img:
                filtered = img.filter(filters[filter_name])
                filtered.save(output_path)
                return True
        except Exception as e:
            self.logger.error(f"Filter fehlgeschlagen: {e}")
            return False
    
    def adjust(self, input_path: str, output_path: str,
               brightness: float = 1.0,
               contrast: float = 1.0,
               saturation: float = 1.0,
               sharpness: float = 1.0) -> bool:
        """
        Passt Bildparameter an.
        
        Werte:
        - 1.0 = Original
        - < 1.0 = Weniger
        - > 1.0 = Mehr
        """
        if not PIL_AVAILABLE:
            return False
        
        try:
            with Image.open(input_path) as img:
                if brightness != 1.0:
                    img = ImageEnhance.Brightness(img).enhance(brightness)
                if contrast != 1.0:
                    img = ImageEnhance.Contrast(img).enhance(contrast)
                if saturation != 1.0:
                    img = ImageEnhance.Color(img).enhance(saturation)
                if sharpness != 1.0:
                    img = ImageEnhance.Sharpness(img).enhance(sharpness)
                
                img.save(output_path)
                return True
        except Exception as e:
            self.logger.error(f"Anpassung fehlgeschlagen: {e}")
            return False
    
    def rotate(self, input_path: str, output_path: str,
               angle: float, expand: bool = True) -> bool:
        """Dreht ein Bild."""
        if not PIL_AVAILABLE:
            return False
        
        try:
            with Image.open(input_path) as img:
                rotated = img.rotate(angle, expand=expand, resample=Image.Resampling.BICUBIC)
                rotated.save(output_path)
                return True
        except Exception as e:
            self.logger.error(f"Rotation fehlgeschlagen: {e}")
            return False
    
    def flip(self, input_path: str, output_path: str,
             horizontal: bool = True) -> bool:
        """Spiegelt ein Bild."""
        if not PIL_AVAILABLE:
            return False
        
        try:
            with Image.open(input_path) as img:
                if horizontal:
                    flipped = ImageOps.mirror(img)
                else:
                    flipped = ImageOps.flip(img)
                flipped.save(output_path)
                return True
        except Exception as e:
            self.logger.error(f"Spiegelung fehlgeschlagen: {e}")
            return False
    
    def crop(self, input_path: str, output_path: str,
             left: int, top: int, right: int, bottom: int) -> bool:
        """Schneidet ein Bild zu."""
        if not PIL_AVAILABLE:
            return False
        
        try:
            with Image.open(input_path) as img:
                cropped = img.crop((left, top, right, bottom))
                cropped.save(output_path)
                return True
        except Exception as e:
            self.logger.error(f"Zuschneiden fehlgeschlagen: {e}")
            return False
    
    def resize_to_fit(self, input_path: str, output_path: str,
                      max_width: int, max_height: int,
                      upscale: bool = False) -> bool:
        """Passt Größe an (behält Seitenverhältnis)."""
        if not PIL_AVAILABLE:
            return False
        
        try:
            with Image.open(input_path) as img:
                if not upscale and img.width <= max_width and img.height <= max_height:
                    img.save(output_path)
                    return True
                
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                img.save(output_path)
                return True
        except Exception as e:
            self.logger.error(f"Größenanpassung fehlgeschlagen: {e}")
            return False
    
    def auto_enhance(self, input_path: str, output_path: str) -> bool:
        """Automatische Bildverbesserung."""
        if not PIL_AVAILABLE:
            return False
        
        try:
            with Image.open(input_path) as img:
                # Auto-Kontrast
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                enhanced = ImageOps.autocontrast(img)
                enhanced.save(output_path)
                return True
        except Exception as e:
            self.logger.error(f"Auto-Enhance fehlgeschlagen: {e}")
            return False
