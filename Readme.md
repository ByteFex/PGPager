# PiSMS

PiSMS is a Python-App for the Raspberry Pi by David Darmann.
It's designed for a Pi with the [Adafruit PiTFT](http://www.adafruit.com/products/1601) on top.

It's touch screen user interface enables you to send and receive PGP encrypted SMS. You can also manage your PGP keys from the user interface. It's developed and tested with an Huawei E303 UMTS USB-Stick but will possibly also work with other Huawei sticks since their interfaces are quite similar.


Tech
-------

PiSMS uses a number of open source projects to work properly:

* [pygame] - Set of Python modules designed for writing games.
* [VKeyboard] - A Python Virtual Keyboard for Adafruit PiTFT and other touch screen devices
* [GnuPG] - Complete and free implementation of the OpenPGP standard
* [python-gnupg] - Python wrapper for GnuPG
* [requests] - An Apache2 Licensed HTTP library, written in Python
* [textrect] - Word-wrapped text display module

Installation
--------------

### Preparation

I assume that you've got the [Adafruit PiTFT] already working and you can see the text console on the PiTFT. If that's not the case, there is an excellent guide at the [Adafruit Learning System]. Youn can even find a ready to use kernel image there.

I also assume that you have an ssh connection to your pi. If not, there's also a lot of [tutorials](http://www.raspberrypi.org/documentation/remote-access/ssh/) for that.

You can use [FileZilla] to copy files to and from your Raspberry Pi in comfort. You find all the settings [here](http://www.raspberrypi.org/documentation/remote-access/ssh/sftp.md).

### Configure Huawei E303
This can be quite tricky. When you first plug the UMTS-Stick into your Pi (or any other computer) it will act as a CD drive. But that's not what we want. We want it to act as a network interface to give us internet access. That way we can also use the web interface to send and receive SMS messages.

Plug your E303 into your Pi and type ``lsusb``. This will give you a list of connected usb devices. You should see something like this
```
Bus 001 Device 002: ID 0424:9512 Standard Microsystems Corp. 
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
Bus 001 Device 003: ID 0424:ec00 Standard Microsystems Corp. 
Bus 001 Device 004: ID 12d1:1f01 Huawei Technologies Co., Ltd. 
```
The last line here comes from our E303. And the `1f01` (the second part of the ID) tells us, it's in the wrong mode. ``14db`` is what we'd like to see here.

Luckily there's [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch/). As it's name suggests, it does exactly what we need: it switches our E303 into network-interface mode. It needs a few packages, so let's install those first.
```sh
sudo apt-get install libusb-1.0-0 libusb-1.0-0-dev
```

I do recommend building it form source to get the latest version. You can do that by running the following commands
```sh
mkdir usb_modeswitch
cd usb_modeswitch/
wget http://www.draisberghof.de/usb_modeswitch/usb-modeswitch-2.2.0.tar.bz2
wget http://www.draisberghof.de/usb_modeswitch/usb-modeswitch-data-20140529.tar.bz2
tar -jxvf usb-modeswitch-2.2.0.tar.bz2
tar -jxvf usb-modeswitch-data-20140529.tar.bz2
cd usb-modeswitch-2.2.0/
sudo make install
cd ../usb-modeswitch-data-20140529/
sudo make install
```
After that do a reboot with ``sudo reboot`` and check ``lsusb`` again. You should now see the E303 with the correct ID.
```
Bus 001 Device 005: ID 12d1:14db Huawei Technologies Co., Ltd. 
```
Also, when you run `ifconfig` there should be a second network interface `eth1` available. If that's the case, the tricky part is done.

However, we still need to edit the interfaces file:
```sh
sudo nano /etc/network/interfaces
```
Copy & paste the following line in:
```
iface eth1 inet dhcp
```

After yet another reboot, the Pi should get an IP address from the E303. If your home network (for ssh access) is also a 192.168.1.0 network you could now get trouble, since the Huawei Stick also uses that network.

PiSMS assumes that the E303 doesn't ask for a PIN Code and it auto-connects to the internet. You can configure this settings from the E303's web interface (just plug it into your Computer).

### Install necessary packages

PiSMS needs a few packages installed. I assume that you are running Raspbian and therefore list only those which are not already included.

#### Install PIP
[PIP](https://pypi.python.org/pypi/pip) is a tool for installing and managing Python packages. To install it, use the following commands on your Pi
```sh
wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
sudo python get-pip.py
```

#### Install python-gnupg
It's now quite easy to install [python-gnupg]. You could just run `sudo pip install python-gnupg`.

However, you need at least version 0.3.7 because PiSMS uses some features added in this version. At this point in time, you can only get it from the [python-gnupg BitBucket Project](https://bitbucket.org/vinay.sajip/python-gnupg/). To install from most recent sources, run
```sh
sudo apt-get install mercurial
hg clone https://bitbucket.org/vinay.sajip/python-gnupg
cd python-gnupg/
sudo python setup.py install
python test_gnupg.py
```
The last command is for testing the installation and might take a while... You can skip that if you don't want to wait.

After that you can verify that you got the correct version by typing
```sh
pip list | grep gnupg
```
This should give you `python-gnupg (0.3.7.dev0)`

#### Install requests
Thanks to pip, that's very easy
```sh
sudo pip install requests
```

#### Install Open Sans font
Download and install by running the following commands
```sh
wget --content-disposition http://www.fontsquirrel.com/fonts/download/open-sans
unzip open-sans.zip *.ttf -d open-sans
sudo mv open-sans /usr/share/fonts/truetype/open
```

### Run PiSMS
Clone the repository
```sh
cd ~/
git clone https://github.com/ByteFex/PiSMS.git      #TODO: check this link!!
```

start the script
```sh
cd PiSMS
sudo python pisms.py
```
and have fun!

## Run PiSMS on startup
Maybe you want PiSMS to start automatically when you boot your Pi. With [GNU screen](http://www.gnu.org/software/screen/), that's easy.

We first need to make the startup-script executable.
```sh
cd ~/PiSMS
chmod +x start_pisms
```

Then install screen
```sh
sudo apt-get install screen
```

and finally edit `rc.local`
```sh
sudo nano /etc/rc.local
```
Add the following line before `exit 0`
```sh
su - pi -c "screen -dm -S pisms ~/PiSMS/start_pisms"
```

You can even take over the session and view debug-output when you ssh into your Pi after PiSMS has started. To do that, use the command
```sh
screen -DR
```

If you want even more (or different) screen awesomeness, there is a nice [documentation](http://www.gnu.org/software/screen/manual/screen.html).

License
----

GNU General Public License

[pygame]:http://www.pygame.org/
[FileZilla]:https://filezilla-project.org/
[Adafruit Learning System]:https://learn.adafruit.com/adafruit-pitft-28-inch-resistive-touchscreen-display-raspberry-pi
[Adafruit PiTFT]:http://www.adafruit.com/products/1601
[VKeyboard]:https://github.com/wbphelps/VKeyboard
[python-gnupg]:https://pythonhosted.org/python-gnupg/
[GnuPG]:https://www.gnupg.org/
[requests]:http://docs.python-requests.org/en/latest/
[textrect]:http://www.pygame.org/pcr/text_rect/index.php