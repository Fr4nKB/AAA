# Installation
## On RPI (assuming you are on RaspberryPi OS):
- `echo "dtoverlay=dwc2" | sudo tee -a /boot/firmware/config.txt`
- `echo "dwc2" | sudo tee -a /etc/modules`
- `sudo echo "libcomposite" | sudo tee -a /etc/modules`
- Move `em_hid` into /usr/bin and run `sudo chmod 777 em_hid`, if you're copying from Windows you must run `sudo dos2unix /usr/bin/em_hid`
- Open `/etc/rc.local/` with a text editor, between `fi` and `exit 0` add `/usr/bin/em_hid` and `chmod 777 /dev/hidg0`
- Move `mouse.py` to the Pi's home
- Now you are can turn off the pi, plug it to a PC via the data port instead of the power port and it will be detected as a mouse once it has boot
## On your PC:
- Install python and run `pip install -r requirements.txt`

# Usage
SSH into the Pi and run `python mouse.py` then run `python main.py` on your PC (be sure to change the IP server address in `main.py` to the Pi's IP address)
