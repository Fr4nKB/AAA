import time
from random import randint
from math import sqrt
import socket
import struct
from threading import Thread
from queue import Queue, Full

ip = "192.168.50.10"
port = 42069

def write_report(report):
    with open('/dev/hidg0', 'wb+') as fd:
        fd.write(report)

def raw_move(x_pixels, y_pixels):
    # 0.35 is my sensitivity in game
    x_units = int(x_pixels * 1/0.35)
    y_units = int(y_pixels * 1/0.35)
    report = bytearray([0, x_units & 0xFF, (x_units >> 8) & 0xFF, y_units & 0xFF, (y_units >> 8) & 0xFF])
    write_report(report)

def perform_lmb_click():
    write_report(bytearray([0x01, 0, 0, 0, 0]))
    time.sleep(0.1)
    write_report(bytearray([0x00, 0, 0, 0, 0]))

def bezier(t, p0, p1, p2, p3):
    return (1 - t)**3 * p0 + 3 * (1 - t)**2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3

def move_mouse(x_offset, y_offset):
    # Generate control points for the Bezier curve
    val = 1 if randint(0,1) == 1 else -1
    control_points = [(0, 0), ((x_offset + val) / 4, (y_offset - val) / 4), ((x_offset - val) * 3/4, (y_offset + val) * 3/4), (x_offset, y_offset)]

    # Initialize previous x and y
    prev_x, prev_y = 0, 0

    # Calculate the total distance to travel
    total_distance = sqrt(x_offset**2 + y_offset**2)
    if(total_distance <= 5):    # avoid moving if already close enough
        return 1

    # Move the mouse along the Bezier curve
    t = 1.0
    while(t <= 30.0):
        if t <= 5.0 or t >= 25.0:     # ease in and out
            step_size = 0.5
        else:
            step_size = 1.0
        
        # get current position on the curve
        x = int(bezier(t/30, control_points[0][0], control_points[1][0], control_points[2][0], control_points[3][0]))
        y = int(bezier(t/30, control_points[0][1], control_points[1][1], control_points[2][1], control_points[3][1]))

        # Calculate the difference from the previous position
        dx = x - prev_x
        dy = y - prev_y

        prev_x, prev_y = x, y

        # Move the mouse by the difference
        raw_move(dx, dy)
        t += step_size

    return 0

def listen():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((ip, port))
    sock.listen(1)
    print("Listening on " + ip + ":" + str(port))

    while True:
        client_socket, client_address = sock.accept()
        print("Accepted connection from:", client_address)

        try:
            while True:
                data = client_socket.recv(8)
                if not data:
                    break

                try:
                    q.put(struct.unpack('ii', data), block=False)
                except Full:
                    continue
        except:
            print("Connection down")

        client_socket.close()

q = Queue(maxsize=1)
listener = Thread(target=listen)
listener.daemon = True
listener.start()

try:
    while True:
        if not q.empty():
            offsets = q.get()
            ret = move_mouse(offsets[0], offsets[1])

            # comment this if you don't want to fire automatically
            # if ret == 1:
            #     time.sleep(0.05)
            #     perform_lmb_click()
except KeyboardInterrupt:
    print("Program exited.")
