import mss
import numpy as np
import cv2
from ultralytics import YOLO
from random import randint
from serial import Serial
from time import sleep


class Aimbot:
    def __init__(self, model_path, port, settings, config, debug=False):
        self.debug = debug
        self.model = YOLO(model_path)
        self.model.to('cuda')
        self.serial_interface = Serial(port, 9600)
        self.mss_instance = mss.mss()

        self.mon_width, self.mon_heigth = self.get_main_monitor_resolution()

        self.update_config(settings, config)

        center = (self.mon_width // 2, self.mon_heigth // 2)
        top_left = (center[0] - self.half_box_size, center[1] - self.half_box_size)
        self.region = {
            'top': top_left[1], 'left': top_left[0],
            'width': self.box_size, 'height': self.box_size
        }

        self.last_box = None


    def update_config(self, settings, config):
        self.box_size = int(settings["aimbot_box_size_percentage"] * self.mon_heigth)
        self.half_box_size = self.box_size // 2

        self.sensitivity = settings["sensitivity"]
        self.confidence = settings["confidence"]

        self.fov_radius_perc = config["aimbot_fov"]
        self.dead_zone_perc = config["dead_zone"]
        self.trigger = config["trigger_bot"]
        self.classes = config["classes"]
        self.smoothness = config["smoothness"] * 100

        self.multiplication_factor = 1 / (0.022 * self.sensitivity)
        self.fov_radius_sq = (self.fov_radius_perc * self.half_box_size / 2) ** 2
        self.dead_zone_radius_sq = (self.dead_zone_perc * self.half_box_size / 2) ** 2


    def get_main_monitor_resolution(self):
        monitors = self.mss_instance.monitors[1:]
        width, height = max(
            ((m["width"], m["height"]) for m in monitors),
            key=lambda wh: wh[0] * wh[1]
        )
        return width, height


    def get_screen(self):
        try:
            im = np.ascontiguousarray(
                np.array(self.mss_instance.grab(self.region))[:, :, :3], dtype=np.uint8
            )
            return im
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None


    def find_player(self, image):
        results = self.model.predict(image, classes=self.classes, conf=self.confidence, verbose=False)[0]
        if not results.boxes:
            return False, None

        if self.last_box is not None:
            ious = []
            for box in results.boxes.xyxy:
                xA = max(self.last_box[0], box[0])
                yA = max(self.last_box[1], box[1])
                xB = min(self.last_box[2], box[2])
                yB = min(self.last_box[3], box[3])

                interArea = max(0, xB - xA) * max(0, yB - yA)
                boxAArea = (self.last_box[2] - self.last_box[0]) * (self.last_box[3] - self.last_box[1])
                boxBArea = (box[2] - box[0]) * (box[3] - box[1])
                iou = interArea / float(boxAArea + boxBArea - interArea)
                ious.append(iou)

            best_idx = int(max(range(len(ious)), key=lambda i: ious[i]))
            box = results.boxes.xyxy[best_idx]
        else:
            box = results.boxes.xyxy[0]

        self.last_box = box
        return True, box


    def send_movement(self, button, x, y):
        deg_x = x * 150 / self.mon_width
        deg_y = y * 85 / self.mon_heigth

        x_units = int(deg_x * self.multiplication_factor)
        y_units = int(deg_y * self.multiplication_factor)

        report = bytearray([
            button,
            x_units & 0xFF, (x_units >> 8) & 0xFF,
            y_units & 0xFF, (y_units >> 8) & 0xFF
        ])

        self.serial_interface.write(report)
        self.serial_interface.flush()


    @staticmethod
    def bezier(t, p0, p1, p2, p3):
        return (1 - t)**3 * p0 + 3 * (1 - t)**2 * t * p1 + \
               3 * (1 - t) * t**2 * p2 + t**3 * p3


    def move_mouse(self, x_offset, y_offset):
        val = 1 if randint(0, 1) == 1 else -1
        control_points = [
            (0, 0),
            ((x_offset + val) / 5, (y_offset - val) / 5),
            ((x_offset - val) * 4/5, (y_offset + val) * 4/5),
            (x_offset, y_offset)
        ]

        if(self.smoothness == 1):
            self.send_movement(0, x_offset, y_offset)
            return

        prev_x, prev_y = 0, 0
        step_size = 0.5 / self.smoothness
        t = 0.0

        while t < 1.0:
            t = min(t + step_size, 1.0)

            # ease in and out
            if t >= 0.8:
                step_size = 0.5 / self.smoothness
            elif t >= 0.2:
                step_size = 1.0 / self.smoothness

            x = int(self.bezier(t, control_points[0][0], control_points[1][0],
                                control_points[2][0], control_points[3][0]))
            y = int(self.bezier(t, control_points[0][1], control_points[1][1],
                                control_points[2][1], control_points[3][1]))

            dx = x - prev_x
            dy = y - prev_y
            prev_x, prev_y = x, y

            self.send_movement(0, dx, dy)
            sleep(0.001)

        print()
        return 0
    

    def shoot(self):
        self.send_movement(1, 0, 0)
        self.send_movement(0, 0, 0)


    def run(self):
        print("Aimbot started.")
        try:
            while True:
                im = self.get_screen()

                if im is not None:
                    is_player_detected, box = self.find_player(im)

                    if is_player_detected:
                        center_x = (box[2] + box[0]) / 2
                        center_y = (box[3] + box[1]) / 2

                        offset_x = int((center_x - self.half_box_size).item())
                        offset_y = int((center_y - self.half_box_size).item())

                        distance_sq = offset_x**2 + offset_y**2

                        if distance_sq <= self.dead_zone_radius_sq:
                            if self.trigger:
                                self.shoot()
                        elif distance_sq <= self.fov_radius_sq:
                            self.move_mouse(offset_x, offset_y)

                        if self.debug:
                            cv2.rectangle(im, (int(center_x), int(center_y)),
                                          (int(center_x), int(center_y)), (0, 255, 0), 2)

                    if self.debug:
                        cv2.imwrite("output.png", im)

                cv2.waitKey(6)
            
        finally:
            print("Aimbot stopped.")
            self.serial_interface.close()
