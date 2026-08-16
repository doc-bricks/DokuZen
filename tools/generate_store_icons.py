"""Generate Windows Store tile icons for DokuZen from master icon.

Generates standard tile dimensions:
- icon_44x44.png (Small tile / App list)
- icon_50x50.png (Store logo)
- icon_150x150.png (Medium tile)
- icon_310x150.png (Wide tile)
- icon_310x310.png (Large tile)
"""

from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ICON = PROJECT_ROOT / "assets" / "icon.png"

TARGET_DIRS = [
    PROJECT_ROOT / "store_package" / "DokuZen" / "icons",
    PROJECT_ROOT / "assets" / "icons",
    PROJECT_ROOT / "store_assets",
]


def generate_tiles():
    if not SOURCE_ICON.exists():
        raise FileNotFoundError(f"Source icon not found at {SOURCE_ICON}")

    img = Image.open(SOURCE_ICON).convert("RGBA")

    for target_dir in TARGET_DIRS:
        target_dir.mkdir(parents=True, exist_ok=True)

        # 44x44
        t44 = img.resize((44, 44), Image.Resampling.LANCZOS)
        t44.save(target_dir / "icon_44x44.png", format="PNG", optimize=True)

        # 50x50
        t50 = img.resize((50, 50), Image.Resampling.LANCZOS)
        t50.save(target_dir / "icon_50x50.png", format="PNG", optimize=True)

        # 150x150
        t150 = img.resize((150, 150), Image.Resampling.LANCZOS)
        t150.save(target_dir / "icon_150x150.png", format="PNG", optimize=True)

        # 310x310
        t310 = img.resize((310, 310), Image.Resampling.LANCZOS)
        t310.save(target_dir / "icon_310x310.png", format="PNG", optimize=True)

        # 310x150 (Wide tile: transparent canvas with centered square icon)
        wide = Image.new("RGBA", (310, 150), (0, 0, 0, 0))
        scaled_for_wide = img.resize((130, 130), Image.Resampling.LANCZOS)
        offset_x = (310 - 130) // 2
        offset_y = (150 - 130) // 2
        wide.paste(scaled_for_wide, (offset_x, offset_y), scaled_for_wide)
        wide.save(target_dir / "icon_310x150.png", format="PNG", optimize=True)

    print(f"Successfully generated store icons in {len(TARGET_DIRS)} directories.")


if __name__ == "__main__":
    generate_tiles()
