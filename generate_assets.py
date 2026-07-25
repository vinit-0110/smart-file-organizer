"""
Smart File Organizer - Icon & Asset Generator Script
Generates clean PNG assets and icon placeholders using PIL.
"""

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def create_app_icon(output_path: str):
    if not HAS_PIL:
        return
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Base rounded rectangle shape
    draw.rounded_rectangle([16, 16, 240, 240], radius=40, fill="#1F6AA5", outline="#3B8ED0", width=6)
    # Inner folder shape
    draw.polygon([(50, 90), (100, 90), (120, 110), (206, 110), (206, 190), (50, 190)], fill="#FFFFFF")
    # Checkmark badge
    draw.ellipse([140, 140, 210, 210], fill="#2CC985")
    draw.line([(155, 175), (170, 190), (195, 155)], fill="#FFFFFF", width=6)

    img.save(output_path, "PNG")


def create_sidebar_icons(icons_dir: str):
    if not HAS_PIL:
        return
    os.makedirs(icons_dir, exist_ok=True)
    icon_names = ["organize.png", "statistics.png", "settings.png", "logs.png", "search.png"]
    colors = ["#3B8ED0", "#2CC985", "#E5A93C", "#9B51E0", "#EB5757"]

    for name, col in zip(icon_names, colors):
        path = os.path.join(icons_dir, name)
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill=col)
        img.save(path, "PNG")


def create_screenshot_placeholder(output_path: str):
    if not HAS_PIL:
        return
    img = Image.new("RGB", (1100, 700), "#1A1A1A")
    draw = ImageDraw.Draw(img)
    # Header area
    draw.rectangle([0, 0, 1100, 60], fill="#242424")
    draw.text((30, 20), "Smart File Organizer - Desktop GUI Mockup", fill="#FFFFFF")
    # Sidebar
    draw.rectangle([0, 60, 220, 700], fill="#111111")
    # Main area
    draw.rectangle([240, 80, 1070, 180], fill="#242424", outline="#333333")
    draw.text((260, 100), "Target Folder: C:/Users/Documents/Downloads", fill="#2CC985")
    draw.text((260, 130), "Status: 100% Complete | 4,250 Files Organized | 320 MB Reclaimed", fill="#E5A93C")

    img.save(output_path, "PNG")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    icons_dir = base_dir / "assets" / "icons"
    screenshots_dir = base_dir / "assets" / "screenshots"

    os.makedirs(icons_dir, exist_ok=True)
    os.makedirs(screenshots_dir, exist_ok=True)

    create_app_icon(str(icons_dir / "app_icon.png"))
    create_sidebar_icons(str(icons_dir))
    create_screenshot_placeholder(str(screenshots_dir / "app_preview.png"))
    print("Generated all asset placeholders successfully.")
