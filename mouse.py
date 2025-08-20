import serial
import struct
from time import sleep


LOG_DEBUG = False


def write_report(report):
    with open('/dev/hidg0', 'wb+') as fd:
        fd.write(report)


def perform_lmb_click():
    write_report(bytearray([0x01, 0, 0, 0, 0]))
    sleep(0.1)
    write_report(bytearray([0x00, 0, 0, 0, 0]))


if __name__ == '__main__':
    ser = serial.Serial('/dev/ttyGS0', 9600, timeout=1)

    try:
        print("Emulated mouse started.")
        while True:
            # read 5 bytes: 1 for button, 2 for X, 2 for Y
            raw_data = ser.read(5)
            if len(raw_data) == 5:

                if(LOG_DEBUG):
                    # unpack for debugging
                    button, x, y = struct.unpack('<Bhh', raw_data)
                    print(f"Button: {button}, X: {x}, Y: {y}")

                write_report(raw_data)
                ser.flush()

    except KeyboardInterrupt:
        print("Stopped by user.")

    finally:
        ser.close()
