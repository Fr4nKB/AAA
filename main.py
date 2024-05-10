from mss import mss
import numpy as np
import cv2
from ultralytics import YOLO
import socket
import select
import struct
import math

model = YOLO('yolov8n.pt')

# load monitor data and calculate the region
monitor = mss().monitors[1]
center = (monitor['width']//2, monitor['height']//2)
top_left = (center[0] - 150, center[1] - 150)
region = {'top': top_left[1], 'left': top_left[0], 'width': 300, 'height': 300}

def getScreen():
    try:
        im = np.array(mss().grab(region))
        im = im[:, :, :3]
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        return im
    except:
        return None

def isPerson(image):
    result = model.predict(image, classes=[0], conf=0.6, max_det=1, verbose=False)[0]
    if result.boxes:
        if len(result.boxes) > 1:
            return False, None
        box = result.boxes[0].xyxy[0]
        return True, box
    
    return False, None

def send(off_x, off_y):
    data = struct.pack('ii', off_x, off_y)
    sock.send(data)
    
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("192.168.50.10", 42069))

while(True):
    im = getScreen()
    if im is not None:
        person_detected, box = isPerson(im)
        if person_detected:
            # Estimate the head position as the top 25% of the bounding box
            head_box = [box[0], box[1], box[2], box[1] + 0.25*(box[3]-box[1])]
            
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

            cv2.rectangle(im, (int(center_x), int(center_y)), (int(center_x), int(center_y)), (0, 255, 0), 2)

        cv2.imwrite("output.png", im)
        
    cv2.waitKey(1)
