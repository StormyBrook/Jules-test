import cv2
from PIL import Image # For attempting to open and validate image
import numpy as np

def load_image(image_path: str) -> np.ndarray | None:
    """
    Loads an image using OpenCV.
    Also tries to open with Pillow to catch more potential errors.

    Args:
        image_path: Path to the image file.

    Returns:
        An OpenCV image object (NumPy array) if successful, None otherwise.
    """
    try:
        # Try with Pillow first to catch a wider range of format issues
        img_pil = Image.open(image_path)
        # Convert to OpenCV format (NumPy array)
        # Ensure it's in BGR format if coming from PIL RGB
        img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        if img_cv is None: # Should not happen if Pillow open succeeded
            print(f"Error: OpenCV could not convert PIL image for {image_path}")
            return None
        print(f"Image '{image_path}' loaded successfully.")
        return img_cv
    except FileNotFoundError:
        print(f"Error: Image file not found at '{image_path}'.")
        return None
    except Exception as e:
        print(f"Error: Could not load image '{image_path}'. Exception: {e}")
        return None

def display_image(image_cv: np.ndarray, window_name: str = "Image") -> None:
    """
    Displays an image using OpenCV.
    Waits for a key press to close the window.

    Args:
        image_cv: The OpenCV image object (NumPy array) to display.
        window_name: The name for the display window.
    """
    if image_cv is None:
        print("Error: Cannot display a None image.")
        return
    try:
        cv2.imshow(window_name, image_cv)
        print(f"Displaying image in window '{window_name}'. Press any key to close.")
        cv2.waitKey(0)
    except Exception as e:
        # Catch errors that might occur if no display server is available
        print(f"Warning: Could not display image. This might be due to a headless environment. Error: {e}")
    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass # Avoid crashing if windows were not created

if __name__ == '__main__':
    # This is for basic testing of the module itself.
    # Create a dummy image file for testing in the images directory.
    # Note: Actual file creation for testing should be part of a test suite,
    # but for this subtask, we'll assume an image exists or skip this direct test.

    # To test, you would need an image in the 'images' folder.
    # For example, if 'images/sample.png' exists:
    # sample_image_path = "../images/sample.png" # Adjust path as needed
    # img = load_image(sample_image_path)
    # if img is not None:
    # display_image(img, "Test Image")
    print("image_utils.py executed as main. Testing functions would require an image.")
