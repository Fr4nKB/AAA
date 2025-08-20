from mss import mss
import numpy as np
import cv2
from ultralytics import YOLO
from random import randint
from math import sqrt
from serial import Serial

DEBUG = False
SCREEN_WINDOW_SIZE = 600
AIMBOT_FOV_RADIUS_PERC = int(0.1 * SCREEN_WINDOW_SIZE)
AIMBOT_FOV_RADIUS_SQ = AIMBOT_FOV_RADIUS_PERC**2
IN_GAME_SENSITIVITY = 0.325
MULTIPLICATION_FACTOR = 1/IN_GAME_SENSITIVITY
CONFIDENCE = 0.78
TRIGGER_THRESHOLD = 5

def getScreen(mss_instance, region):
    try:
        im = np.ascontiguousarray(
            np.array(mss_instance.grab(region))[:, :, :3], dtype=np.uint8
        )
        return im
    except Exception as e:
        print(f"Error capturing screen: {e}")
        return


def isPerson(model, image, last_box):
    results = model.predict(image, classes=[1, 3], conf=CONFIDENCE, verbose=False)[0]

    if not results.boxes:
        return False, None

    # If we already have a target, find the detection that overlaps it most
    if last_box is not None:
        ious = []
        for box in results.boxes.xyxy:
            # simple IoU calc
            xA = max(last_box[0], box[0])
            yA = max(last_box[1], box[1])
            xB = min(last_box[2], box[2])
            yB = min(last_box[3], box[3])

            interArea = max(0, xB - xA) * max(0, yB - yA)
            boxAArea = (last_box[2] - last_box[0]) * (last_box[3] - last_box[1])
            boxBArea = (box[2] - box[0]) * (box[3] - box[1])
            iou = interArea / float(boxAArea + boxBArea - interArea)
            ious.append(iou)

        best_match_idx = int(max(range(len(ious)), key=lambda i: ious[i]))
        box = results.boxes.xyxy[best_match_idx]
    else:
        # First frame: pick highest confidence
        box = results.boxes.xyxy[0]

    last_box = box
    return True, box


def send_movement(serial_interface, button, x, y):
    # 0.35 is my sensitivity in game
    x_units = int(x * MULTIPLICATION_FACTOR)
    y_units = int(y * MULTIPLICATION_FACTOR)
    report = bytearray([button, x_units & 0xFF, (x_units >> 8) & 0xFF, y_units & 0xFF, (y_units >> 8) & 0xFF])
    serial_interface.write(report)
    serial_interface.flush()


def bezier(t, p0, p1, p2, p3):
    return (1 - t)**3 * p0 + 3 * (1 - t)**2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3


def move_mouse(serial_interface, x_offset, y_offset):
    # Generate control points for the Bezier curve
    val = 1 if randint(0,1) == 1 else -1
    control_points = [(0, 0), ((x_offset + val) / 4, (y_offset - val) / 4), ((x_offset - val) * 3/4, (y_offset + val) * 3/4), (x_offset, y_offset)]

    # Initialize previous x and y
    prev_x, prev_y = 0, 0

    # Calculate the total distance to travel
    total_distance = sqrt(x_offset**2 + y_offset**2)
    if total_distance <= TRIGGER_THRESHOLD:    # avoid moving if already close enough
        send_movement(serial_interface, 1, 0, 0)
        send_movement(serial_interface, 0, 0, 0)
        return 1

    # move the mouse along the Bezier curve
    num_points = 20.0
    step_size = 0.5/num_points
    t = 0.0

    while(t < 1.0):
        t = min(t + step_size, 1.0)

        # ease in and out
        if t >= 0.8:
            step_size = 0.5/num_points
        elif t >= 0.2:
            step_size = 1.0/num_points

        # get current position on the curve
        x = int(bezier(t, control_points[0][0], control_points[1][0], control_points[2][0], control_points[3][0]))
        y = int(bezier(t, control_points[0][1], control_points[1][1], control_points[2][1], control_points[3][1]))

        # Calculate the difference from the previous position
        dx = x - prev_x
        dy = y - prev_y

        prev_x, prev_y = x, y

        # Move the mouse by the difference
        send_movement(serial_interface, 0, dx, dy)

    return 0
    

if __name__ == "__main__":
    try:
        model = YOLO('yolo12s_cs2.pt')
        model.to('cuda')
        ser = Serial('COM5', 9600)

        # load monitor data and calculate the region
        mss_instance = mss()
        monitor = mss_instance.monitors[2] # you may need to change this index if you have more than one monitor
        center = (monitor['width']//2, monitor['height']//2)
        top_left = (center[0] - SCREEN_WINDOW_SIZE//2, center[1] - SCREEN_WINDOW_SIZE//2)
        region = {'top': top_left[1], 'left': top_left[0], 'width': SCREEN_WINDOW_SIZE, 'height': SCREEN_WINDOW_SIZE}
        last_box = None

        while(True):
            im = getScreen(mss_instance, region)

            if im is not None:
                person_detected, last_box = isPerson(model, im, last_box)

                if person_detected:
                    head_box = [last_box[0], last_box[1], last_box[2], last_box[3]]
                    
                    # Adjust the width of the head box to be half the size of the body
                    width = head_box[2] - head_box[0]
                    height = head_box[3] - head_box[1]
                    center_x = head_box[0] + width / 2
                    center_y = head_box[1] + height / 2
                    
                    # Calculate the center of the image
                    image_center_x = im.shape[1] / 2
                    image_center_y = im.shape[0] / 2
                    
                    # Calculate the offset in the x and y directions
                    offset_x = int((center_x - image_center_x).item())
                    offset_y = int((center_y - image_center_y).item())

                    if offset_x*offset_x + offset_y*offset_y < AIMBOT_FOV_RADIUS_SQ:
                        move_mouse(ser, offset_x, offset_y)

                    if(DEBUG):
                        cv2.rectangle(im, (int(center_x), int(center_y)), (int(center_x), int(center_y)), (0, 255, 0), 2)
                
                if(DEBUG):
                    cv2.imwrite("output.png", im)
                
            cv2.waitKey(0)
    except Exception as e:
        print(e)
        ser.close()
