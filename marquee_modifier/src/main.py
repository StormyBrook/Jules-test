from .image_utils import load_image, display_image
from .selection_utils import select_area
from .text_renderer import render_text_with_boxes
import os
import numpy as np
import cv2
from PIL import Image

# --- Configuration ---
# User should place their image in the 'images' directory
DEFAULT_INPUT_IMAGE_FILENAME = "sample.png"
# User should place their .ttf font file in the 'fonts' directory
DEFAULT_FONT_FILENAME = "DejaVuSansMono.ttf"
# Output will be saved in the 'output' directory
DEFAULT_OUTPUT_IMAGE_FILENAME = "final_marquee_image.png"

# Construct full paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Assumes src is one level down
# If main.py is in src, then project root is its parent.
# If running script directly from src, this path might be different than if run as module from root.
# For simplicity, let's assume paths are relative to the project root if run as a module,
# or relative to current dir if script is run directly.
# The current os.path.join usage implies relative to where script is run.

# For more robust paths assuming execution from project root (marquee_modifier/):
# FONT_PATH = os.path.join(BASE_DIR, "fonts", DEFAULT_FONT_FILENAME)
# IMAGE_PATH = os.path.join(BASE_DIR, "images", DEFAULT_INPUT_IMAGE_FILENAME)
# OUTPUT_PATH = os.path.join(BASE_DIR, "output", DEFAULT_OUTPUT_IMAGE_FILENAME)

# Sticking to simpler relative paths for now, assuming script is run from project root.
FONT_PATH = os.path.join("fonts", DEFAULT_FONT_FILENAME)
IMAGE_PATH = os.path.join("images", DEFAULT_INPUT_IMAGE_FILENAME)
OUTPUT_PATH = os.path.join("output", DEFAULT_OUTPUT_IMAGE_FILENAME)


def get_marquee_text() -> str:
    while True:
        text = input(">>> Please enter the text you want on the marquee (e.g., 'HELLO WORLD'): ")
        if text.strip(): # Check if text is not just whitespace
            print(f"--- Marquee text received: '{text.strip()}'")
            return text.strip()
        else:
            print("--- No text entered or text is whitespace. Please provide some meaningful text.")

def main():
    print("=============================================")
    print("=== Welcome to the Marquee Text Modifier! ===")
    print("=============================================")
    print("\n--- Prerequisites ---")
    print(f"1. Ensure an image file is present at: '{os.path.abspath(IMAGE_PATH)}'")
    print(f"   (You can change 'DEFAULT_INPUT_IMAGE_FILENAME' in this script if needed)")
    print(f"2. Ensure a .ttf font file is present at: '{os.path.abspath(FONT_PATH)}'")
    print(f"   (You can change 'DEFAULT_FONT_FILENAME' in this script if needed)")
    print(f"3. The output image will be saved to: '{os.path.abspath(OUTPUT_PATH)}'")
    print("---------------------------------------------\n")

    if not os.path.exists(FONT_PATH):
        print(f"CRITICAL ERROR: Font file '{os.path.abspath(FONT_PATH)}' not found!")
        print("Please add the font file or correct the FONT_PATH variable in the script and try again.")
        return

    if not os.path.exists(IMAGE_PATH):
        print(f"CRITICAL ERROR: Image file '{os.path.abspath(IMAGE_PATH)}' not found!")
        print("Please add the image file or correct the IMAGE_PATH variable in the script and try again.")
        return

    print(f"--- Loading image: '{os.path.abspath(IMAGE_PATH)}' ---")
    original_img_cv = load_image(IMAGE_PATH)

    if original_img_cv is None:
        print("--- Image loading failed. Please check the image file and path. Exiting. ---")
        return # Already handled by load_image's print, but good to be explicit.

    orig_h, orig_w = original_img_cv.shape[:2]
    print(f"--- Image loaded successfully (Dimensions: {orig_w}x{orig_h}). ---")

    print("\n--- Step 1: Select Marquee Area ---")
    print("A window will open. Click and drag to draw a rectangle on the marquee.")
    print("Press 'c' to confirm, 'r' to reset, 'q' to quit selection.")
    selection_img_copy = original_img_cv.copy()
    marquee_coords_rect = select_area(selection_img_copy)

    if not marquee_coords_rect:
        print("--- Marquee area selection was cancelled or failed. Exiting. ---")
        return

    print(f"--- Marquee area selected: {marquee_coords_rect} ---")

    print("\n--- Step 2: Enter Marquee Text ---")
    marquee_text = get_marquee_text()

    print(f"\n--- Step 3: Rendering Text '{marquee_text}' ---")
    # Consider making font_size configurable or dynamic
    rendered_text_pil = render_text_with_boxes(marquee_text, FONT_PATH, font_size=40)

    if not rendered_text_pil:
        print("--- Text rendering failed. Check font or text_renderer.py. Exiting. ---")
        return

    print(f"--- Text rendered successfully (PIL Image size: {rendered_text_pil.size}) ---")

    print("\n--- Step 4: Transforming and Compositing Text ---")
    rendered_text_cv_bgra = cv2.cvtColor(np.array(rendered_text_pil), cv2.COLOR_RGBA2BGRA)
    text_h, text_w = rendered_text_cv_bgra.shape[:2]

    src_pts = np.array([
        [0, 0], [text_w - 1, 0],
        [text_w - 1, text_h - 1], [0, text_h - 1]
    ], dtype=np.float32)

    startX, startY, endX, endY = marquee_coords_rect
    dst_pts = np.array([
        [startX, startY], [endX, startY],
        [endX, endY], [startX, endY]
    ], dtype=np.float32)

    try:
        perspective_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    except Exception as e:
        print(f"--- CRITICAL ERROR calculating perspective matrix: {e} ---")
        print("--- This can happen if the selected area is too small or forms an invalid shape. ---")
        return

    warped_text_bgra = cv2.warpPerspective(rendered_text_cv_bgra, perspective_matrix, (orig_w, orig_h))

    b, g, r, alpha_channel = cv2.split(warped_text_bgra)
    warped_text_bgr = cv2.merge((b,g,r))
    alpha_normalized = alpha_channel / 255.0
    alpha_mask_3channel = cv2.merge((alpha_normalized, alpha_normalized, alpha_normalized))

    background_part = (original_img_cv.astype(float) * (1.0 - alpha_mask_3channel))
    foreground_part = (warped_text_bgr.astype(float) * alpha_mask_3channel)

    final_image_cv = (background_part + foreground_part).astype(np.uint8)
    print("--- Text transformed and composited onto original image. ---")

    print(f"\n--- Step 5: Saving and Displaying Result ---")
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        cv2.imwrite(OUTPUT_PATH, final_image_cv)
        print(f"--- Successfully saved final image to: '{os.path.abspath(OUTPUT_PATH)}' ---")

        print("--- Displaying final image. Press any key in the image window to close. ---")
        display_image(final_image_cv, "Final Marquee Image")

    except Exception as e:
        print(f"--- ERROR saving or displaying final image: {e} ---")
        return # Exit if saving/display fails

    print("\n===================================")
    print("=== Processing Complete! ===")
    print("===================================")

if __name__ == "__main__":
    main()
