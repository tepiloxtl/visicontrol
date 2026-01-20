Wayland input visualiser, intended to support keyboard, mouse and controller input, maybe a client/server architecture (allowing visualising user input from another device), done in pygame in evdev

## Whats done:
* KEY events (keyboard, mouse)
* Mouse-specific REL events (relative mouse position, scroll wheel(s))
* Layout configuration in JSON5
* Device separation

## Whats to be done:
* Selection of input device based on name or some identifier instead of device file, which may change
* Controller support
* Styling
* Proper packaging and release
* ... and (possibly) more

## How to use it (abridged abridged)
`pip install evdev pygame-ce json5` (preferably in venv)  
Evdev requires special permissions, your options are:  
* Run as root
* Add yourself to `input` group, reload session
* I think you can do `setcap cap_dac_override+ep` on a python executable. Normally if you do that on your venv python executable, since its a symlink, it will apply to your systemwide python interpreter. Create venv with `--copies` argument to avoid that, maybe
* You may also be able to `setfacl /dev/input/event*`???

There is an exmaple layout.json5 file that defines devices and which inputs will be displayed in the window, as well as window size. Application will print list of evdev devices on startup, update `input_device` for your keyboard and mouse accordingly, then you can start exploring. Example file contains all features currently available. Basically for now you can only adjust size of displayed elements, add a label, and for MouseRel element also size of its "reticle", no options for styling just yet. By default application will open the layout.json5 file provided, you can load any file with `-c` argument. `--no-force-wayland` also exists, should be self explanatory

Tested on KDE Wayland, on Fedora 43. Yell at me if it doesn't work in your Wayland environment, I might look into this