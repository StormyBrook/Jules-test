from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.staticfiles import StaticFiles # Will still use for /static (frontend assets)
from fastapi.responses import FileResponse, JSONResponse
import os
import shutil
import numpy as np
import cv2
from PIL import Image

from .image_utils import load_image
from .text_renderer import render_text_with_boxes

app = FastAPI(
    title="Marquee Text Modifier API",
    description="API for modifying text on theater marquees in images.",
    version="0.1.0"
)

# --- Static File Serving (Frontend Assets) ---
app.mount("/static", StaticFiles(directory="static"), name="static_frontend")

# --- Dynamic File Storage (for Vercel's /tmp directory) ---
TMP_UPLOAD_DIR = "/tmp/marquee_uploads"
os.makedirs(TMP_UPLOAD_DIR, exist_ok=True)

# REMOVED: app.mount("/tmp_viewer", StaticFiles(directory=TMP_UPLOAD_DIR), name="static_tmp_uploads")
# This was problematic for serverless environments.

# --- Configuration ---
DEFAULT_FONT_FILENAME = "DejaVuSansMono.ttf"
FONT_PATH = os.path.join("fonts", DEFAULT_FONT_FILENAME)

@app.get("/", include_in_schema=False)
async def read_root_html():
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/upload_image/")
async def upload_image(imageFile: UploadFile = File(...)):
    os.makedirs(TMP_UPLOAD_DIR, exist_ok=True)
    try:
        # Consider using UUID for unique names to prevent clashes in /tmp
        # filename = f"{uuid.uuid4()}_{imageFile.filename}"
        filename = imageFile.filename
        file_path = os.path.join(TMP_UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(imageFile.file, buffer)

        # The image is in /tmp. The frontend cannot reliably access it via a URL.
        # We return the filename for the subsequent /process_image call.
        # The frontend might use FileReader for a local preview if needed.
        return JSONResponse(
            content={
                "filename": filename, # This is the key piece of info for the next step
                "message": f"Image '{filename}' uploaded to temporary storage successfully."
            },
            status_code=200
        )
    except Exception as e:
        return JSONResponse(content={"message": f"Upload error: {str(e)}"}, status_code=500)
    finally:
        if imageFile: imageFile.file.close()

from pydantic import BaseModel
class ProcessImageRequest(BaseModel):
    filename: str # Filename of the image in TMP_UPLOAD_DIR
    selection: dict
    text: str
    font_size: int = 40

@app.post("/process_image/")
async def process_image_endpoint(request: ProcessImageRequest = Body(...)):
    os.makedirs(TMP_UPLOAD_DIR, exist_ok=True)
    processed_image_path_in_tmp = None # Define to ensure it's available for finally block
    uploaded_image_path = os.path.join(TMP_UPLOAD_DIR, request.filename) # Define for potential cleanup
    try:
        if not os.path.exists(uploaded_image_path):
            raise HTTPException(status_code=404, detail=f"Uploaded image not found in /tmp: {request.filename}. It might have expired or was not uploaded correctly.")

        if not os.path.exists(FONT_PATH):
            print(f"SERVER ERROR: Font file not found at {os.path.abspath(FONT_PATH)}")
            raise HTTPException(status_code=500, detail="Server configuration error: Font file not found.")

        original_img_cv = load_image(uploaded_image_path)
        if original_img_cv is None:
            raise HTTPException(status_code=500, detail="Could not load original image from /tmp for processing.")

        orig_h, orig_w = original_img_cv.shape[:2]

        rendered_text_pil = render_text_with_boxes(
            text=request.text, font_path=FONT_PATH, font_size=request.font_size
        )
        if not rendered_text_pil:
            raise HTTPException(status_code=500, detail="Failed to render text.")

        rendered_text_cv_bgra = cv2.cvtColor(np.array(rendered_text_pil), cv2.COLOR_RGBA2BGRA)
        # ... (rest of the image processing logic: src_pts, dst_pts, warp, composite) ...
        text_h, text_w = rendered_text_cv_bgra.shape[:2]
        src_pts = np.array([
            [0, 0], [text_w - 1, 0],
            [text_w - 1, text_h - 1], [0, text_h - 1]
        ], dtype=np.float32)
        sel = request.selection
        dst_pts = np.array([
            [int(sel['startX']), int(sel['startY'])], [int(sel['endX']), int(sel['startY'])],
            [int(sel['endX']), int(sel['endY'])], [int(sel['startX']), int(sel['endY'])]
        ], dtype=np.float32)
        try:
            perspective_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        except Exception as e:
            if not (sel['endX'] > sel['startX'] and sel['endY'] > sel['startY']):
                raise HTTPException(status_code=400, detail=f"Invalid selection coordinates: {sel}")
            raise HTTPException(status_code=400, detail=f"Perspective transform failed. Selection valid? Error: {str(e)}")
        warped_text_bgra = cv2.warpPerspective(rendered_text_cv_bgra, perspective_matrix, (orig_w, orig_h))
        b, g, r, alpha_channel = cv2.split(warped_text_bgra)
        warped_text_bgr = cv2.merge((b, g, r))
        alpha_normalized = alpha_channel / 255.0
        alpha_mask_3channel = cv2.merge((alpha_normalized, alpha_normalized, alpha_normalized))
        background_part = (original_img_cv.astype(float) * (1.0 - alpha_mask_3channel))
        foreground_part = (warped_text_bgr.astype(float) * alpha_mask_3channel)
        final_image_cv = (background_part + foreground_part).astype(np.uint8)
        # --- End of image processing logic adaptation ---

        processed_filename = f"processed_{request.filename}"
        processed_image_path_in_tmp = os.path.join(TMP_UPLOAD_DIR, processed_filename)

        cv2.imwrite(processed_image_path_in_tmp, final_image_cv)

        # Return the processed image file directly
        return FileResponse(
            processed_image_path_in_tmp,
            media_type="image/png", # Or determine dynamically based on filename extension
            filename=processed_filename # Suggests a filename to the browser for download
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        # Clean up the specific processed file from /tmp after sending it.
        if processed_image_path_in_tmp and os.path.exists(processed_image_path_in_tmp):
            try:
                os.remove(processed_image_path_in_tmp)
                print(f"Cleaned up temporary processed file: {processed_image_path_in_tmp}")
            except Exception as e_remove:
                print(f"Error cleaning up temporary file {processed_image_path_in_tmp}: {e_remove}")

        # Clean up the original uploaded file from /tmp as it's no longer needed after processing.
        if os.path.exists(uploaded_image_path):
            try:
                os.remove(uploaded_image_path)
                print(f"Cleaned up temporary uploaded file: {uploaded_image_path}")
            except Exception as e_remove:
                print(f"Error cleaning up temporary uploaded file {uploaded_image_path}: {e_remove}")
