from mss import mss
import numpy as np
import cv2
from ultralytics import YOLO
import socket
import struct
from time import sleep

model = YOLO('yolov8s_cs2.pt')

# load monitor data and calculate the region
mss_instance = mss()
monitor = mss_instance.monitors[2] # you may need to change this index if you have more than one monitor
center = (monitor['width']//2, monitor['height']//2)
top_left = (center[0] - 150, center[1] - 150)
region = {'top': top_left[1], 'left': top_left[0], 'width': 300, 'height': 300}

last_box = None  

def getScreen():
    try:
        im = np.ascontiguousarray(
            np.array(mss_instance.grab(region))[:, :, :3], dtype=np.uint8
        )
        return im
    except Exception as e:
        print(f"Error capturing screen: {e}")
        return

def isPerson(image):
    global last_box

    results = model.predict(image, classes=[1, 3], conf=0.65, verbose=False)[0]

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

def send(off_x, off_y):
    data = struct.pack('ii', off_x, off_y)
    sock.send(data)
    
while(True):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.settimeout(5)
        sock.connect(("192.168.50.10", 42069))

        while(True):
            im = getScreen()
            if im is not None:
                person_detected, box = isPerson(im)
                if person_detected:
                    head_box = [box[0], box[1], box[2], box[3]]
                    
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

                    send(offset_x, offset_y)

                    # uncomment for debugging purposes
                    #cv2.rectangle(im, (int(center_x), int(center_y)), (int(center_x), int(center_y)), (0, 255, 0), 2)
                
                # uncomment for debugging purposes
                #cv2.imwrite("output.png", im)
                
            cv2.waitKey(1)

    except Exception as e:
        sock.close()
        print(f"Disconnected ({e}), retrying in 2s…")
        sleep(2)
