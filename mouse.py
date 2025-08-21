import serial
import struct


LOG_DEBUG = False


if __name__ == '__main__':
    try:
        serial_interface = serial.Serial('/dev/ttyGS0', 9600, timeout=1)
        emulated_mouse = open('/dev/hidg0', 'wb+')

        print("Emulated mouse started.")

        while True:
            # read 5 bytes: 1 for button, 2 for X, 2 for Y
            report = serial_interface.read(5)
            serial_interface.flush()
            
            if len(report) == 5:

                if(LOG_DEBUG):
                    # unpack for debugging
                    button, x, y = struct.unpack('<Bhh', report)
                    print(f"Button: {button}, X: {x}, Y: {y}")

                emulated_mouse.write(report)
                emulated_mouse.flush()

    except KeyboardInterrupt:
        print("Stopped by user.")

    except Exception as e:
        print(e)

    finally:
        serial_interface.close()
        emulated_mouse.close()
