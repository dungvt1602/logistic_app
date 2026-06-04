import io
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import cv2
import numpy as np
import base64

app = FastAPI(title="PDF Stamp Remover API")

# Allow CORS for communication with Streamlit or other frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_stamp_mask(img_bgr, img_hsv, preset: str, **kwargs):
    """
    Generate a binary mask identifying the stamp pixels based on the selected preset or custom HSV values.
    """
    # Extract BGR channels for color difference filtering
    b, g, r = cv2.split(img_bgr)
    s = img_hsv[:, :, 1]
    v = img_hsv[:, :, 2]
    
    if preset == "red":
        # Red hue wraps around 0 and 180
        lower_red1 = np.array([0, 20, 30])
        upper_red1 = np.array([15, 255, 255])
        lower_red2 = np.array([165, 20, 30])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(img_hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(img_hsv, lower_red2, upper_red2)
        hsv_mask = mask1 + mask2
        
        # Color difference mask for faint red/pink edges:
        # Red channel must be higher than green and blue channels, and red must be above a minimum brightness.
        # This captures very light pink edges where saturation in HSV might be low.
        r_g_diff = r.astype(int) - g.astype(int)
        r_b_diff = r.astype(int) - b.astype(int)
        rgb_mask = ((r_g_diff > 10) & (r_b_diff > 10) & (r > 80)).astype(np.uint8) * 255
        
        combined_mask = cv2.bitwise_or(hsv_mask, rgb_mask)
        
        # Black/gray text protection:
        # A pixel is protected if its Value < 110 unless it is clearly red
        is_real_red = (r_g_diff > 15) & (r_b_diff > 15)
        protected = (v < 110) & (~is_real_red)
        
        mask = combined_mask.copy()
        mask[protected] = 0
        
    elif preset == "blue":
        lower_blue = np.array([85, 30, 30])
        upper_blue = np.array([140, 255, 255])
        hsv_mask = cv2.inRange(img_hsv, lower_blue, upper_blue)
        
        # Blue channel must be higher than red and green channels
        b_r_diff = b.astype(int) - r.astype(int)
        b_g_diff = b.astype(int) - g.astype(int)
        rgb_mask = ((b_r_diff > 12) & (b_g_diff > 12) & (b > 90)).astype(np.uint8) * 255
        
        combined_mask = cv2.bitwise_or(hsv_mask, rgb_mask)
        
        # Black/gray text protection for blue
        is_real_blue = (b_r_diff > 15) & (b_g_diff > 15)
        protected = (v < 110) & (~is_real_blue)
        
        mask = combined_mask.copy()
        mask[protected] = 0
        
    elif preset == "purple":
        lower_purple = np.array([125, 30, 30])
        upper_purple = np.array([168, 255, 255])
        hsv_mask = cv2.inRange(img_hsv, lower_purple, upper_purple)
        
        # Purple is a mix of red and blue, with low green
        r_g_diff = r.astype(int) - g.astype(int)
        b_g_diff = b.astype(int) - g.astype(int)
        rgb_mask = ((r_g_diff > 12) & (b_g_diff > 12) & (r > 90) & (b > 90)).astype(np.uint8) * 255
        
        combined_mask = cv2.bitwise_or(hsv_mask, rgb_mask)
        
        # Black/gray text protection for purple
        is_real_purple = (r_g_diff > 15) & (b_g_diff > 15)
        protected = (v < 110) & (~is_real_purple)
        
        mask = combined_mask.copy()
        mask[protected] = 0
        
    else:  # custom
        # Read custom HSV values from kwargs
        h_min_1 = kwargs.get("hue_min_1", 0)
        h_max_1 = kwargs.get("hue_max_1", 10)
        h_min_2 = kwargs.get("hue_min_2", 170)
        h_max_2 = kwargs.get("hue_max_2", 180)
        sat_min = kwargs.get("sat_min", 40)
        sat_max = kwargs.get("sat_max", 255)
        val_min = kwargs.get("val_min", 40)
        val_max = kwargs.get("val_max", 255)
        
        mask1 = cv2.inRange(img_hsv, np.array([h_min_1, sat_min, val_min]), np.array([h_max_1, sat_max, val_max]))
        mask2 = cv2.inRange(img_hsv, np.array([h_min_2, sat_min, val_min]), np.array([h_max_2, sat_max, val_max]))
        mask = mask1 + mask2

    # Apply morphological dilation if specified to expand the stamp mask slightly (fills gaps and handles fuzzy edges)
    dilation = kwargs.get("dilation", 1)
    if dilation > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilation * 2 + 1, dilation * 2 + 1))
        mask = cv2.dilate(mask, kernel, iterations=1)
        
    return mask

def process_image(img_bgr, preset: str, **kwargs) -> np.ndarray:
    """
    Remove stamp from a BGR image by replacing the masked pixels with white.
    """
    # Convert to HSV color space
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # Generate stamp mask
    mask = get_stamp_mask(img_bgr, hsv, preset, **kwargs)
    
    # Copy original image
    cleaned = img_bgr.copy()
    
    # Replace stamp pixels with white (255, 255, 255)
    cleaned[mask > 0] = [255, 255, 255]
    
    return cleaned

def remove_regions_by_text(page, img_bgr, scale: float, search_texts: list, padding: dict = None):
    """
    Search for text on a PyMuPDF page, map coordinates to image pixels,
    and white out those regions on the BGR image.
    
    padding: dict with keys 'left', 'right', 'top', 'bottom' in PDF points to expand the region.
    """
    if padding is None:
        padding = {"left": 0, "right": 0, "top": 0, "bottom": 0}
    
    for text in search_texts:
        rects = page.search_for(text)
        for rect in rects:
            # Expand the rect by padding (in PDF coordinates)
            x0 = int((rect.x0 - padding.get("left", 0)) * scale)
            y0 = int((rect.y0 - padding.get("top", 0)) * scale)
            x1 = int((rect.x1 + padding.get("right", 0)) * scale)
            y1 = int((rect.y1 + padding.get("bottom", 0)) * scale)
            
            # Clamp to image bounds
            h, w = img_bgr.shape[:2]
            x0 = max(0, x0)
            y0 = max(0, y0)
            x1 = min(w, x1)
            y1 = min(h, y1)
            
            # White out the region
            img_bgr[y0:y1, x0:x1] = [255, 255, 255]
    
    return img_bgr

def remove_signature_region(page, img_bgr, scale: float):
    """
    Remove the blue signature from the image using color masking.
    This preserves printed black text (such as company name and labels) 
    while removing the blue pen strokes.
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    b, g, r = cv2.split(img_bgr)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    
    # Blue mask (HSV and RGB color difference)
    lower_blue = np.array([85, 30, 30])
    upper_blue = np.array([140, 255, 255])
    hsv_mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    
    b_r_diff = b.astype(int) - r.astype(int)
    b_g_diff = b.astype(int) - g.astype(int)
    rgb_mask_blue = ((b_r_diff > 10) & (b_g_diff > 10) & (b > 80)).astype(np.uint8) * 255
    combined_blue = cv2.bitwise_or(hsv_mask_blue, rgb_mask_blue)
    
    # Black text protection (v < 110)
    is_real_blue = (b_r_diff > 15) & (b_g_diff > 15)
    protected_blue = (v < 110) & (~is_real_blue)
    
    blue_mask = combined_blue.copy()
    blue_mask[protected_blue] = 0
    
    # Dilate slightly to get clean edges
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    blue_mask = cv2.dilate(blue_mask, kernel, iterations=1)
    
    img_bgr[blue_mask > 0] = [255, 255, 255]
    return img_bgr

def remove_bill_no(page, img_bgr, scale: float):
    """
    Find 'Bill No' text and white out the entire line (text + value).
    """
    rects = page.search_for("Bill No")
    if not rects:
        return img_bgr
    
    for rect in rects:
        # White out from the start of 'Bill No' text to the right edge of the page,
        # with a small vertical padding
        page_width = page.rect.width
        x0 = int((rect.x0 - 5) * scale)
        y0 = int((rect.y0 - 3) * scale)
        x1 = int(page_width * scale)
        y1 = int((rect.y1 + 3) * scale)
        
        h, w = img_bgr.shape[:2]
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(w, x1)
        y1 = min(h, y1)
        
        img_bgr[y0:y1, x0:x1] = [255, 255, 255]
    
    return img_bgr

@app.post("/preview/")
async def preview_page(
    file: UploadFile = File(...),
    page_num: int = Form(0),
    preset: str = Form("red"),
    hue_min_1: int = Form(0),
    hue_max_1: int = Form(12),
    hue_min_2: int = Form(168),
    hue_max_2: int = Form(180),
    sat_min: int = Form(40),
    sat_max: int = Form(255),
    val_min: int = Form(40),
    val_max: int = Form(255),
    dilation: int = Form(1),
    dpi: int = Form(150),
    remove_sig: int = Form(0),
    remove_billno: int = Form(0)
):
    """
    Convert a specific PDF page to an image, run stamp removal on it,
    and return both original and cleaned images encoded as base64.
    """
    try:
        pdf_bytes = await file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if page_num < 0 or page_num >= len(doc):
            raise HTTPException(status_code=400, detail=f"Page number {page_num} is out of bounds (0 to {len(doc)-1})")
            
        page = doc[page_num]
        
        # Calculate matrix scaling factor based on DPI (72 DPI is base)
        scale = dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        
        pix = page.get_pixmap(matrix=matrix)
        
        # Convert to numpy BGR image
        # pix.samples has width * height * n bytes
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        else:
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
        # Process image
        kwargs = {
            "hue_min_1": hue_min_1, "hue_max_1": hue_max_1,
            "hue_min_2": hue_min_2, "hue_max_2": hue_max_2,
            "sat_min": sat_min, "sat_max": sat_max,
            "val_min": val_min, "val_max": val_max,
            "dilation": dilation
        }
        cleaned_bgr = process_image(img_bgr, preset, **kwargs)
        
        # Remove signature region if requested
        if remove_sig:
            cleaned_bgr = remove_signature_region(page, cleaned_bgr, scale)
        
        # Remove Bill No if requested
        if remove_billno:
            cleaned_bgr = remove_bill_no(page, cleaned_bgr, scale)
        
        # Encode both images to PNG
        _, orig_encoded = cv2.imencode(".png", img_bgr)
        _, clean_encoded = cv2.imencode(".png", cleaned_bgr)
        
        orig_b64 = base64.b64encode(orig_encoded).decode("utf-8")
        clean_b64 = base64.b64encode(clean_encoded).decode("utf-8")
        
        total_pages = len(doc)
        doc.close()
        
        return {
            "total_pages": total_pages,
            "page_num": page_num,
            "original": orig_b64,
            "cleaned": clean_b64
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process/")
async def process_pdf(
    file: UploadFile = File(...),
    preset: str = Form("red"),
    hue_min_1: int = Form(0),
    hue_max_1: int = Form(12),
    hue_min_2: int = Form(168),
    hue_max_2: int = Form(180),
    sat_min: int = Form(40),
    sat_max: int = Form(255),
    val_min: int = Form(40),
    val_max: int = Form(255),
    dilation: int = Form(1),
    dpi: int = Form(150),
    remove_sig: int = Form(0),
    remove_billno: int = Form(0)
):
    """
    Clean the entire PDF document, removing stamps from every page,
    and returns the compiled PDF file.
    """
    try:
        pdf_bytes = await file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        out_doc = fitz.open()
        
        scale = dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        
        kwargs = {
            "hue_min_1": hue_min_1, "hue_max_1": hue_max_1,
            "hue_min_2": hue_min_2, "hue_max_2": hue_max_2,
            "sat_min": sat_min, "sat_max": sat_max,
            "val_min": val_min, "val_max": val_max,
            "dilation": dilation
        }
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix)
            
            # Convert to numpy BGR image
            img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
            else:
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                
            # Remove stamp
            cleaned_bgr = process_image(img_bgr, preset, **kwargs)
            
            # Remove signature region if requested
            if remove_sig:
                cleaned_bgr = remove_signature_region(page, cleaned_bgr, scale)
            
            # Remove Bill No if requested
            if remove_billno:
                cleaned_bgr = remove_bill_no(page, cleaned_bgr, scale)
            
            # Convert back to PNG bytes
            _, png_encoded = cv2.imencode(".png", cleaned_bgr)
            png_bytes = png_encoded.tobytes()
            
            # Create a new page matching original size
            new_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)
            # Insert the cleaned image to fit the page exactly
            new_page.insert_image(page.rect, stream=png_bytes)
            
        # Save compiled PDF to bytes
        out_pdf_io = io.BytesIO()
        out_doc.save(out_pdf_io)
        out_pdf_io.seek(0)
        
        doc.close()
        out_doc.close()
        
        return StreamingResponse(
            out_pdf_io,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=cleaned_{file.filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
