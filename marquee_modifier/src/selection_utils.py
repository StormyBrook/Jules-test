import cv2
import numpy as np

# Global variables to store selection points and state
ref_pt = []
selecting = False
selection_done = False
image_for_selection = None # To store the image being selected on

def click_and_select(event, x, y, flags, param):
    """Mouse callback function for selecting an area."""
    global ref_pt, selecting, selection_done, image_for_selection

    if event == cv2.EVENT_LBUTTONDOWN:
        ref_pt = [(x, y)]
        selecting = True
        selection_done = False
        print(f"Selection started at {ref_pt[0]}")

    elif event == cv2.EVENT_LBUTTONUP:
        ref_pt.append((x, y))
        selecting = False
        selection_done = True
        # Draw final rectangle on the image copy
        if image_for_selection is not None and len(ref_pt) == 2:
            cv2.rectangle(image_for_selection, ref_pt[0], ref_pt[1], (0, 255, 0), 2)
            cv2.imshow("Select Area - Press 'c' to confirm, 'r' to reset", image_for_selection)
        print(f"Selection ended at {ref_pt[1]}. Press 'c' to confirm, 'r' to reset.")

    elif event == cv2.EVENT_MOUSEMOVE and selecting:
        # Draw rectangle dynamically if selecting
        if image_for_selection is not None and len(ref_pt) == 1:
            temp_image = image_for_selection.copy()
            cv2.rectangle(temp_image, ref_pt[0], (x,y), (0, 255, 0), 2)
            cv2.imshow("Select Area - Press 'c' to confirm, 'r' to reset", temp_image)


def select_area(image: np.ndarray) -> tuple[int, int, int, int] | None:
    """
    Allows the user to select a rectangular area on the image.

    Args:
        image: The OpenCV image object (NumPy array).

    Returns:
        A tuple (startX, startY, endX, endY) representing the selected rectangle,
        or None if selection is cancelled or fails.
    """
    global ref_pt, selecting, selection_done, image_for_selection

    if image is None:
        print("Error: Cannot select area on a None image.")
        return None

    image_for_selection = image.copy() # Use a copy for drawing
    clone_for_reset = image.copy() # For resetting selection
    window_name = "Select Area - Press 'c' to confirm, 'r' to reset"

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, click_and_select)

    print("Please select the marquee area by clicking and dragging.")
    print("Press 'c' to confirm your selection.")
    print("Press 'r' to reset the selection.")
    print("Press 'q' to quit selection without saving.")

    while True:
        if image_for_selection is not None:
            cv2.imshow(window_name, image_for_selection)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("r"): # Reset selection
            print("Selection reset.")
            image_for_selection = clone_for_reset.copy()
            ref_pt = []
            selecting = False
            selection_done = False

        elif key == ord("c"): # Confirm selection
            if selection_done and len(ref_pt) == 2:
                # Ensure top-left and bottom-right
                startX = min(ref_pt[0][0], ref_pt[1][0])
                startY = min(ref_pt[0][1], ref_pt[1][1])
                endX = max(ref_pt[0][0], ref_pt[1][0])
                endY = max(ref_pt[0][1], ref_pt[1][1])

                if startX >= endX or startY >= endY: # Check for valid rectangle
                    print("Invalid selection (e.g. a line or point). Please reset and try again.")
                    image_for_selection = clone_for_reset.copy() # Reset visual
                    ref_pt = []
                    selecting = False
                    selection_done = False
                    continue # Go back to loop to allow re-selection or quit

                print(f"Selection confirmed: ({startX}, {startY}) to ({endX}, {endY})")
                cv2.destroyWindow(window_name)
                return (startX, startY, endX, endY)
            else:
                print("No selection made or selection not finalized. Please select an area first.")

        elif key == ord("q"): # Quit
            print("Selection quit by user.")
            cv2.destroyWindow(window_name)
            return None

        # Handle window closure via 'X' button if possible (depends on OpenCV backend)
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            print("Selection window closed by user.")
            return None


if __name__ == '__main__':
    # This part is for testing selection_utils.py directly
    # It would require an image.
    # print("To test selection_utils.py, run it with an image path argument")
    # print("e.g., python selection_utils.py path_to_your_image.png")
    # if len(sys.argv) > 1:
    #     img = cv2.imread(sys.argv[1])
    #     if img is not None:
    #         selected_coords = select_area(img)
    #         if selected_coords:
    #             print(f"Selected coordinates: {selected_coords}")
    #         else:
    #             print("No area selected.")
    #     else:
    #         print(f"Could not load image: {sys.argv[1]}")
    # else:
    # print("Provide an image path to test selection.")
    print("selection_utils.py executed. Direct testing requires an image and interactive display.")
