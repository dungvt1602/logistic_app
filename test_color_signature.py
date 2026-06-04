import fitz
import cv2
import numpy as np

# Load PDF
doc = fitz.open("INV_IG_ETD 21.05.PDF")
page = doc[0]
scale = 150 / 72.0
matrix = fitz.Matrix(scale, scale)
pix = page.get_pixmap(matrix=matrix)
img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
if pix.n == 4:
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
else:
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
b, g, r = cv2.split(img_bgr)
s = hsv[:, :, 1]
v = hsv[:, :, 2]

# 1. Red Stamp Mask (with black text protection)
lower_red1 = np.array([0, 20, 30])
upper_red1 = np.array([15, 255, 255])
lower_red2 = np.array([165, 20, 30])
upper_red2 = np.array([180, 255, 255])
mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
hsv_mask_red = mask1 + mask2

r_g_diff = r.astype(int) - g.astype(int)
r_b_diff = r.astype(int) - b.astype(int)
rgb_mask_red = ((r_g_diff > 10) & (r_b_diff > 10) & (r > 80)).astype(np.uint8) * 255
combined_red = cv2.bitwise_or(hsv_mask_red, rgb_mask_red)

# Red protection
protected_red = (v < 110) & (s < 40)
is_real_red = (r_g_diff > 15) & (r_b_diff > 15)
protected_red = protected_red & (~is_real_red)

red_mask = combined_red.copy()
red_mask[protected_red] = 0

# 2. Blue Signature Mask (with black text protection)
lower_blue = np.array([85, 30, 30])
upper_blue = np.array([140, 255, 255])
hsv_mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

b_r_diff = b.astype(int) - r.astype(int)
b_g_diff = b.astype(int) - g.astype(int)
rgb_mask_blue = ((b_r_diff > 10) & (b_g_diff > 10) & (b > 80)).astype(np.uint8) * 255
combined_blue = cv2.bitwise_or(hsv_mask_blue, rgb_mask_blue)

# Blue protection
protected_blue = (v < 110) & (s < 40)
is_real_blue = (b_r_diff > 15) & (b_g_diff > 15)
protected_blue = protected_blue & (~is_real_blue)

blue_mask = combined_blue.copy()
blue_mask[protected_blue] = 0

# Union of both masks
final_mask = cv2.bitwise_or(red_mask, blue_mask)

# Apply dilation to make sure edges are clean
dilation = 1
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilation * 2 + 1, dilation * 2 + 1))
final_mask = cv2.dilate(final_mask, kernel, iterations=1)

# Apply to image
cleaned = img_bgr.copy()
cleaned[final_mask > 0] = [255, 255, 255]

# Also remove Bill No
rects = page.search_for("Bill No")
for rect in rects:
    page_width = page.rect.width
    x0 = int((rect.x0 - 5) * scale)
    y0 = int((rect.y0 - 3) * scale)
    x1 = int(page_width * scale)
    y1 = int((rect.y1 + 3) * scale)
    
    h, w = cleaned.shape[:2]
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(w, x1)
    y1 = min(h, y1)
    cleaned[y0:y1, x0:x1] = [255, 255, 255]

cv2.imwrite("test_color_sig.png", cleaned)
print("Saved test_color_sig.png")
doc.close()
