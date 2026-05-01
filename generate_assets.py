"""
generate_assets.py
Run once to create static/template_bg.png placeholder asset.
Not part of the app runtime – utility script only.
"""
from PIL import Image, ImageDraw

w, h = 1080, 1920
img = Image.new("RGB", (w, h), (10, 14, 26))
draw = ImageDraw.Draw(img)

# Subtle diagonal grid lines
for i in range(-h, w + h, 80):
    draw.line([(i, 0), (i + h, h)], fill=(0, 30, 50), width=1)

img.save("static/template_bg.png", "PNG")
print("static/template_bg.png created.")
