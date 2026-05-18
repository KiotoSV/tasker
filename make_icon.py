"""Генератор icon.ico для приложения. Запуск: python make_icon.py"""

from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "icon.ico"
SUPER = 1024
FINAL_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

GREEN = (22, 163, 74, 255)
WHITE = (255, 255, 255, 255)

img = Image.new("RGBA", (SUPER, SUPER), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

inset = 40
radius = 220
draw.rounded_rectangle(
    [inset, inset, SUPER - inset, SUPER - inset],
    radius=radius,
    fill=GREEN,
)

line_thickness = 78
line_r = line_thickness // 2
left_x = 220
right_x_long = 824
right_x_short = 640

rows = [
    (360, right_x_short),
    (510, right_x_long),
    (660, right_x_long),
    (810, right_x_short + 60),
]
for y, right_x in rows:
    draw.rounded_rectangle(
        [left_x, y - line_r, right_x, y + line_r],
        radius=line_r,
        fill=WHITE,
    )

img = img.resize((256, 256), Image.LANCZOS)
img.save(OUT, sizes=FINAL_SIZES)
print(f"Saved: {OUT}")
