from PIL import Image, ImageDraw, ImageFont
import os

def render_text_with_boxes(
    text: str,
    font_path: str,
    font_size: int = 40,
    text_color: tuple = (0, 0, 0, 255), # Black, fully opaque
    box_padding: int = 5,
    box_outline_color: tuple = (50, 50, 50, 255), # Dark grey outline for boxes
    box_fill_color: tuple = (200, 200, 200, 100) # Light grey, semi-transparent fill
) -> Image.Image | None:
    """
    Renders text with individual boxes around each letter.

    Args:
        text: The string to render.
        font_path: Path to the TTF font file.
        font_size: Desired font size.
        text_color: Color of the text (R, G, B, A).
        box_padding: Padding around each letter inside its box.
        box_outline_color: Color of the box outline (R, G, B, A).
        box_fill_color: Fill color of the box (R, G, B, A).

    Returns:
        A PIL Image object with the rendered text and boxes, or None on error.
    """
    if not os.path.exists(font_path):
        print(f"Error: Font file not found at '{font_path}'.")
        print("Please ensure a .ttf font file is available in the 'fonts' directory and the path is correct.")
        return None

    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print(f"Error loading font: {e}")
        return None

    char_images = []
    total_width = 0
    max_height = 0

    # First pass: Render each character to get its size and create its boxed image
    for char_code in text:
        char = str(char_code) # Ensure it's a string
        # Get bounding box for the character itself
        # For Pillow < 10.0.0, textbbox might not exist, use textsize as fallback for width/height
        try:
            # (left, top, right, bottom) relative to (0,0)
            char_bbox = font.getbbox(char, anchor='lt')
            char_width = char_bbox[2] - char_bbox[0]
            char_height = char_bbox[3] - char_bbox[1]
            # Offset for drawing the character, as getbbox is relative to (0,0)
            char_offset_x = char_bbox[0]
            char_offset_y = char_bbox[1]

        except AttributeError: # Fallback for older Pillow versions
            # textsize returns (width, height)
            text_size = font.getsize(char)
            char_width = text_size[0]
            char_height = text_size[1]
            char_offset_x = 0
            char_offset_y = 0 # Assuming no negative bearing for simplicity in fallback

        # Create size for the individual character tile (char + padding)
        tile_width = char_width + 2 * box_padding
        tile_height = char_height + 2 * box_padding

        # Create a transparent tile for this character
        char_img = Image.new('RGBA', (tile_width, tile_height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(char_img)

        # Draw the semi-transparent box
        draw.rectangle(
            (0, 0, tile_width -1 , tile_height -1), # -1 for outline to be visible within bounds
            fill=box_fill_color,
            outline=box_outline_color
        )

        # Draw the character onto its tile
        # Position character considering its own bbox offset and padding
        text_x = box_padding - char_offset_x
        text_y = box_padding - char_offset_y
        draw.text((text_x, text_y), char, font=font, fill=text_color)

        char_images.append(char_img)
        total_width += tile_width
        if tile_height > max_height:
            max_height = tile_height

    if not char_images:
        return Image.new('RGBA', (1,1), (255,255,255,0)) # Return tiny transparent image if no text

    # Second pass: Composite all character tiles into one image
    final_image = Image.new('RGBA', (total_width, max_height), (255, 255, 255, 0))
    current_x = 0
    for char_img in char_images:
        final_image.paste(char_img, (current_x, 0), char_img) # Paste considering alpha
        current_x += char_img.width

    print(f"Text rendered with boxes. Final image size: {final_image.size}")
    return final_image

if __name__ == '__main__':
    print("Text Renderer Module")
    # Basic test - requires a font file
    font_file = "../fonts/DejaVuSansMono.ttf" # Example, user needs to ensure this exists
    if not os.path.exists(font_file):
        # Try to find a common system font as a fallback for basic testing
        # This is OS-dependent and might not work reliably in all environments
        if os.name == 'nt': # Windows
            font_file_system = "C:/Windows/Fonts/arial.ttf"
        else: # Linux/macOS (common paths)
            font_file_system = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
            if not os.path.exists(font_file_system):
                font_file_system = "/Library/Fonts/Arial.ttf" # macOS

        if os.path.exists(font_file_system):
            print(f"Local font '{font_file}' not found. Using system font '{font_file_system}' for testing.")
            font_file = font_file_system
        else:
            print(f"Font '{font_file}' not found, and common system fonts not found. Cannot run test.")
            font_file = None

    if font_file:
        test_text = "HELLO"
        rendered_img = render_text_with_boxes(test_text, font_file, font_size=40)
        if rendered_img:
            try:
                rendered_img.save("../output/rendered_text_test.png")
                print(f"Test rendered image saved to ../output/rendered_text_test.png")
            except Exception as e:
                print(f"Could not save test image: {e}")
        else:
            print("Test rendering failed.")
    else:
        print("Skipping render test as no font file is available.")
