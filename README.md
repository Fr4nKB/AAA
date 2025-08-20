# Installation
## On RPI (assuming you are on RaspberryPi OS):
- `echo "dtoverlay=dwc2" | sudo tee -a /boot/firmware/config.txt`
- `echo "dwc2" | sudo tee -a /etc/modules`
- `sudo echo "libcomposite" | sudo tee -a /etc/modules`
- Copy `em_hid` to your rpi zero, if you're copying from Windows you must run `sudo dos2unix em_hid`
- Run `sudo mv em_hid /usr/bin` and `sudo chmod +x em_hid`
- Open `/etc/rc.local/` with a text editor, between `fi` and `exit 0` add `/usr/bin/em_hid` and `chmod 777 /dev/hidg0`
- Move `mouse.py` to the Pi's home
- Turn off the pi, plug it to a PC via the *data port* instead of the power port and it will be detected as a mouse once it has finished booting
## On your PC:
- Install python and run `pip install -r requirements.txt`
- Using pytorch for CUDA is recommended for better performance

# Usage
SSH into the Pi and run `python mouse.py` then run `python main.py` on your PC
