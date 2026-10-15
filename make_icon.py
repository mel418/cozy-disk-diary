"""Draws icon.ico (a kawaii bunny on a pastel tile). Run once: python make_icon.py"""
from PIL import Image, ImageDraw

S = 1024  # draw big, shrink for smooth edges
BROWN, PINK, PEACH, CREAM, WHITE = "#675348", "#F4C6CD", "#F5C6A2", "#F8E6C6", "#FFFFFF"

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
w = 28  # outline width

d.rounded_rectangle((30, 30, S - 30, S - 30), radius=230, fill=PINK, outline=BROWN, width=w)
# gingham hint
for x in range(120, S - 100, 170):
    d.line((x, 70, x, S - 70), fill="#F9D9DE", width=40)
# ears
for cx in (370, 654):
    d.ellipse((cx - 85, 120, cx + 85, 560), fill=WHITE, outline=BROWN, width=w)
    d.ellipse((cx - 38, 190, cx + 38, 500), fill=PINK)
# head
d.ellipse((190, 360, 834, 900), fill=WHITE, outline=BROWN, width=w)
# eyes, cheeks, mouth
for cx in (390, 634):
    d.ellipse((cx - 32, 590, cx + 32, 665), fill=BROWN)
    d.ellipse((cx - 11, 604, cx + 3, 620), fill=WHITE)
for cx in (305, 719):
    d.ellipse((cx - 55, 670, cx + 55, 735), fill=PEACH)
d.arc((452, 650, 512, 730), 10, 170, fill=BROWN, width=w - 4)
d.arc((512, 650, 572, 730), 10, 170, fill=BROWN, width=w - 4)
# little heart
d.polygon([(730, 790), (800, 790), (765, 840)], fill="#E59A9A")
d.ellipse((722, 760, 770, 810), fill="#E59A9A")
d.ellipse((760, 760, 808, 810), fill="#E59A9A")

img = img.resize((256, 256), Image.LANCZOS)
img.save("icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
img.save("icon_preview.png")
