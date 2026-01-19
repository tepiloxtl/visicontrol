Wayland input visualiser, intended to support keyboard, mouse and controller input, maybe a client/server architecture (allowing visualising user input from another device), done in pygame in evdev

## Whats done:
* Buttons (keyboard, mouse)
* Mouse relative movement (implemented poorly, but works)

## Whats to be done:
* Layout file (currently elements are hardcoded in code, in elements)
* Proper device separation
* Controller support
* Styling
* ... and (possibly) more

## How to use it (abridged abridged)
`pip install evdev pygame-ce json5` (preferably in venv)  
Evdev requires special permissions, your options are:  
* Run as root
* Add yourself to `input` group, reload session
* I think you can do `setcap cap_dac_override+ep` on a python executable. Normally if you do that on your venv python executable, since its a symlink, it will apply to your systemwide python interpreter. Create venv with `--copies` argument to avoid that, maybe
* You may also be able to `setfacl /dev/input/event*`???

Inspect script.py. Find `mouse` and `kbd` variables, update with paths to your devices. Running the script will print list of all devices connected to PC (or nothing if permissions are not set correctly.) Next, find elements and define your buttons and mouse visualiser however you want. I am unsure if the mouse buttons will work rn after I reworked some evdev stuff, but keyboard and mouse movement should. Run it and it should work.

Tested on KDE Wayland, on Fedora 43. Yell at me if it doesn't work in your Wayland environment, I might look into this