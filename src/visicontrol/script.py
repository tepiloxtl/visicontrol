import evdev
import pygame
import asyncio
import json5
import os
import argparse
import struct, errno
from dataclasses import dataclass

@dataclass
class Device:
    name: str
    type: str
    obj: evdev.InputDevice

@dataclass
class Event:
    name: str
    type: str
    data: EventData

@dataclass
class EventData:
    type: int
    code: int
    value: int

class Button:
    def __init__(self, x, y, w, h, label):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.is_pressed = False

        self.bg_color = (30,30,30)
        self.active_color = (255,30,30)
        self.border_color = (200,200,200)
        self.text_color = (255,255,255)
        self.font = pygame.font.SysFont("Arial", 16)
    
    def update(self, update):
        if update.value == 0:
            self.is_pressed = False
        else:
            self.is_pressed = True
    
    def draw(self, screen):
        current_color = self.active_color if self.is_pressed else self.bg_color

        pygame.draw.rect(screen, current_color, self.rect)
        pygame.draw.rect(screen, self.border_color, self.rect, 2)

        label_surf = self.font.render(self.label, True, self.text_color)
        text_x = self.rect.centerx - (label_surf.get_width() // 2)
        text_y = self.rect.centery - (label_surf.get_height() // 2)
        screen.blit(label_surf, (text_x, text_y))

class MouseRel:
    def __init__(self, x, y, w, h, reticle_size = 5, label = ""):
        self.rect = pygame.Rect(x, y, w, h)
        self.w = w
        self.h = h
        self.reticle_size = reticle_size
        self.reticle = pygame.Rect(self.rect.centerx, self.rect.centery, self.reticle_size, self.reticle_size)
        self.label = label
        self.mouse_x = 0
        self.mouse_y = 0
        self.no_update = 0

        self.bg_color = (30,30,30)
        self.reticle_color = (255,30,30)
        self.border_color = (200,200,200)
        self.text_color = (255,255,255)
        self.font = pygame.font.SysFont("Arial", 16)
    
    def update(self, update):
        if update == {0:0,1:0}:
            self.no_update += 1
            if self.no_update > 240:
                self.no_update = 0
                self.mouse_x = 0
                self.mouse_y = 0
        self.mouse_x = max(self.w * -0.5, min(update[0], self.w * 0.5)) if update[0] != 0 else self.mouse_x
        self.mouse_y = max(self.h * -0.5, min(update[1], self.h * 0.5)) if update[1] != 0 else self.mouse_y
        self.reticle.center = (self.rect.centerx + self.mouse_x, self.rect.centery + self.mouse_y)
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.bg_color, self.rect)
        pygame.draw.rect(screen, self.border_color, self.rect, 2)
        pygame.draw.rect(screen, self.reticle_color, self.reticle)

class MouseScrollBtn:
    def __init__(self, x, y, w, h, direction, label = ""):
        self.rect = pygame.Rect(x, y, w, h)
        self.w = w
        self.h = h
        self.direction = direction
        self.label = label
        self.is_pressed = False
        self.presses = 0
        self.cooldown = 20
        self.timer = 0

        self.bg_color = (30,30,30)
        self.active_color = (255,30,30)
        self.border_color = (200,200,200)
        self.text_color = (255,255,255)
        self.font = pygame.font.SysFont("Arial", 16)
        self.display_label = self.label
    
    def update(self, update):
        if self.direction == update.value:
            self.is_pressed = True
            self.presses += 1
            self.timer = self.cooldown
            self.display_label = "{}\n{}".format(self.label, self.presses)
            # self.display_label = str(self.presses)
    
    def draw(self, screen):
        if self.timer:
            self.timer -= 1
            if self.timer == 0:
                self.is_pressed = False
                self.presses = 0
                self.display_label = self.label
        current_color = self.active_color if self.is_pressed else self.bg_color

        pygame.draw.rect(screen, current_color, self.rect)
        pygame.draw.rect(screen, self.border_color, self.rect, 2)

        lines = self.display_label.splitlines()
        line_height = self.font.get_linesize()
        total_height = len(lines) * line_height
        current_y = self.rect.centery - (total_height // 2)
        for line in lines:
            label_surf = self.font.render(line, True, self.text_color)
            text_x = self.rect.centerx - (label_surf.get_width() // 2)
            screen.blit(label_surf, (text_x, current_y))
            current_y += line_height

async def print_events(type, name, device, queue):
    loop = asyncio.get_running_loop()
    fd = device.fd
    
    # Pre-bind the put method to avoid attribute lookup costs in the hot path
    put_nowait = queue.put_nowait
    # https://stackoverflow.com/questions/5060710/format-of-dev-input-event
    # https://docs.python.org/3/library/errno.html
    def read_batch():
        while True:
            try:
                # Read a chunk of raw bytes (max 32 events at once)
                data = os.read(fd, EVENT_SIZE * 32)
            except OSError as e:
                if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                    break
                else:
                    print(f"Device error: {e}")
                    break
            
            # If device disconnected or sent empty string
            if not data:
                break

            for i in range(0, len(data), EVENT_SIZE):
                chunk = data[i:i+EVENT_SIZE]
                if len(chunk) < EVENT_SIZE:
                    break
                tv_sec, tv_usec, evtype, evcode, evvalue = struct.unpack(EVENT_FMT, chunk)

                # Drop Detection
                if evtype == 0 and evcode == 3: # EV_SYN, SYN_DROPPED
                    print(f"{name} BUFFER OVERFLOW")
                    continue

                try:
                    # put_nowait((name, type, code, value))
                    # Putting two dataclasses in here might still cause memory issues maybe? But this works without reenginering the entire thing
                    put_nowait(Event(name, type, EventData(evtype, evcode, evvalue)))
                except asyncio.QueueFull:
                    pass

    # Register the callback. This runs even while main loop is sleeping
    loop.add_reader(fd, read_batch)

    try:
        # Keep this task alive forever
        await asyncio.Future()
    except asyncio.CancelledError:
        loop.remove_reader(fd)

def load_layout(layout, config):
    devices = []
    elements = {}
    input_map = {}
    if layout["window_size"]:
        config["window_size"] = layout["window_size"]
    for device_name, device in layout["devices"].items():
        devices.append(Device(device_name, device["type"], evdev.InputDevice(device["input_device"])))
        for element_name, element in device["inputs"].items():
            if element["type"] == "Button":
                elements[element_name] = Button(element["position"]["x"], element["position"]["y"], element["position"]["w"], element["position"]["h"], element["label"])
            elif element["type"] == "MouseRel":
                elements[element_name] = MouseRel(element["position"]["x"], element["position"]["y"], element["position"]["w"], element["position"]["h"], element["reticle_size"])
            elif element["type"] == "MouseScrollBtn":
                elements[element_name] = MouseScrollBtn(element["position"]["x"], element["position"]["y"], element["position"]["w"], element["position"]["h"], element["direction"], element["label"])
            if (device_name, element["keycode"]) in input_map:
                input_map[(device_name, element["keycode"])].append(element_name)
            else:
                input_map[(device_name, element["keycode"])] = [element_name]
    return devices, elements, input_map


alldevices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in alldevices:
    print(device.path, device.name, device.phys)

EVENT_FMT = 'llHHi'
EVENT_SIZE = struct.calcsize(EVENT_FMT)

async def pygame_main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-force-wayland', action='store_true', help='Disable forcing Wayland compositor')
    parser.add_argument('-c', '--config', type=str, help='Path to a JSON5 configuration file')
    args = parser.parse_args()
    if args.no_force_wayland == False:
        os.environ["SDL_VIDEODRIVER"] = "wayland,x11"
    layoutpath = "../../layout.json5"
    if args.config:
        layoutpath = args.config
    with open(layoutpath, "r") as file:
        layout = json5.load(file)
    print(layout)
    pygame.init()
    print(f"--- DEBUG INFO ---")
    print(f"Pygame Version: {pygame.version.ver}")
    print(f"SDL Version: {pygame.get_sdl_version()}")
    print(f"Video Driver: {pygame.display.get_driver()}")
    print(f"------------------")

    config = {"window_size": [1280, 720]}
    devices, elements, input_map = load_layout(layout, config)
    print(devices)
    print(elements)
    print(input_map)

    key_lookup = evdev.ecodes.bytype[evdev.ecodes.EV_KEY]

    screen = pygame.display.set_mode(config["window_size"])
    target_frame_duration = 1.0 / 60.0
    running = True
    event_queue = asyncio.Queue()

    tasks = set()
    for device in devices:
        task = asyncio.create_task(print_events(device.type, device.name, device.obj, event_queue))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    while running:
        loop_start = asyncio.get_running_loop().time()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        mouse_updates = {}
        for device in devices:
            if device.type == "mouse":
                mouse_updates[device.name] = {0: 0, 1: 0}
        # idk if theres an another kind of device other than a mouse that would benefit from MouseScrollBtn
        # Still needs special case for MouseXY, its REL event happens MUCH more frequently than once a frame and it bogs down the visuals
        try:
            while True:
            # get_nowait() checks the queue without blocking the game loop
            # If the queue is empty, it raises asyncio.QueueEmpty
                event = event_queue.get_nowait()
                if event.data.type == 1:
                    try:
                        raw_name = key_lookup[event.data.code]
                        for action in input_map[(event.name, raw_name[0] if isinstance(raw_name, (list, tuple)) else raw_name)]:
                            elements[action].update(event.data)
                    except:
                        print("No button " + str(raw_name))
                        pass
                elif event.data.type == 2:
                    if event.data.code == 0 or event.data.code == 1:
                        mouse_updates[device.name][event.data.code] += event.data.value
                    else:
                        try:
                            raw_name = evdev.ecodes.REL[event.data.code]
                            for action in input_map[(event.name, raw_name[0] if isinstance(raw_name, (list, tuple)) else raw_name)]:
                                elements[action].update(event.data)
                        except:
                            # print("No button " + str(raw_name))
                            pass
            
        except asyncio.QueueEmpty:
            pass
        # print(mouse_updates)
        for device in mouse_updates:
            for element in input_map[(device, "MouseXY")]:
                elements[element].update(mouse_updates[device])

        screen.fill("purple")

        for element in elements.values():
            element.draw(screen)

        pygame.display.flip()
        #This replaces clock.tick(60) cos its nonblocking and allow high-polling devices to work better?
        elapsed = asyncio.get_running_loop().time() - loop_start
        sleep_time = target_frame_duration - elapsed
        
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
        else:
            await asyncio.sleep(0)

    pygame.quit()

if __name__ == "__main__":
    asyncio.run(pygame_main())