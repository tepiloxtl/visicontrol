import evdev
import pygame
import asyncio
import json5
import os
from dataclasses import dataclass

os.environ["SDL_VIDEODRIVER"] = "wayland,x11"

@dataclass
class Device:
    name: str
    type: str
    obj: evdev.InputDevice

@dataclass
class Event:
    name: str
    type: str
    data: evdev.events.InputEvent

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
    # Some ideas copied from the internet. I dont understand how async works, but #itworks
    loop = asyncio.get_running_loop()
    fd = device.fd
    
    # Pre-bind the put method to avoid attribute lookup costs in the hot path
    put_nowait = queue.put_nowait
    
    def read_batch():
        try:
            # device.read() gets everything currently in the buffer
            for event in device.read():
                if event.type == evdev.ecodes.EV_SYN and event.code == evdev.ecodes.SYN_DROPPED:
                    print(f"⚠ {name} BUFFER OVERFLOW!")
                    continue
                put_nowait(Event(name, type, event))
                
        except (BlockingIOError, OSError):
            pass # Buffer empty or device read error

    # Register the callback. This runs even while main loop is sleeping
    loop.add_reader(fd, read_batch)

    try:
        # Keep this task alive forever
        await asyncio.Future()
    except asyncio.CancelledError:
        loop.remove_reader(fd)
        

alldevices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in alldevices:
    print(device.path, device.name, device.phys)

devices = [Device("kbd0", "kbd", evdev.InputDevice('/dev/input/event6')), Device("mouse0", "mouse", evdev.InputDevice('/dev/input/event2'))]
key_lookup = evdev.ecodes.bytype[evdev.ecodes.EV_KEY]


async def pygame_main():
    pygame.init()
    print(f"--- DEBUG INFO ---")
    print(f"Pygame Version: {pygame.version.ver}")
    print(f"SDL Version: {pygame.get_sdl_version()}")
    print(f"Video Driver: {pygame.display.get_driver()}")
    print(f"------------------")
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    target_frame_duration = 1.0 / 60.0
    running = True
    event_queue = asyncio.Queue()

    elements = {
        "KEY_Q":    Button(50, 50, 100, 100, "Q"),
        # "KEY_QQ":    Button(50, 150, 100, 100, "Q"),
        "KEY_W":    Button(150, 50, 100, 100, "W"),
        "KEY_E":    Button(250, 50, 100, 100, "E"),
        "KEY_R":    Button(350, 50, 100, 100, "R"),
        "KEY_T":    Button(450, 50, 100, 100, "T"),
        "KEY_Y":    Button(550, 50, 100, 100, "Y"),
        "MouseXY":  MouseRel(800, 50, 200, 200, 10),
        "MouseL":   Button(800, 250, 100, 100, "LMB"),
        "MouseR":   Button(900, 250, 100, 100, "RMB"),
        "ScrollUp": MouseScrollBtn(800, 350, 100, 100, 1, "Scroll UP"),
        "ScrollDown": MouseScrollBtn(900, 350, 100, 100, -1, "Scroll DOWN"),
        "ScrollLeft": MouseScrollBtn(800, 450, 100, 100, -1, "Scroll LEFT"),
        "ScrollRight": MouseScrollBtn(900, 450, 100, 100, 1, "Scroll RIGHT")

    }

    input_map = {
        ("kbd0", "KEY_Q"): ["KEY_Q", "KEY_QQ"],
        ("kbd0", "KEY_W"): ["KEY_W"],
        ("kbd0", "KEY_E"): ["KEY_E"],
        ("kbd0", "KEY_R"): ["KEY_R"],
        ("kbd0", "KEY_T"): ["KEY_T"],
        ("kbd0", "KEY_Y"): ["KEY_Y"],
        ("mouse0", "MouseXY"): ["MouseXY"],
        ("mouse0", "BTN_LEFT"): ["MouseL"],
        ("mouse0", "BTN_RIGHT"): ["MouseR"],
        ("mouse0", "REL_WHEEL"): ["ScrollUp", "ScrollDown"],
        ("mouse0", "REL_HWHEEL"): ["ScrollLeft", "ScrollRight"],
    }

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
        # =======IMPORTANT=======
        # This shit needs some massive overhaul
        # Keyboard part is decent I guess
        # Mouse is shit: the rel position is hardcoded to one object mouse_updates
        # Then in general handling of all REL type events could be done better probably idk?
        # idk if theres an another kind of device other than a mouse that would benefit from MouseScrollBtn
        # Also clean up all the prints
        # Still needs special case for MouseXY, its REL event happens MUCH more frequently than once a frame and it bogs down the visuals
        # Bababababababababa
        # =======================
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

    # bg_task.cancel() # Stop the background task
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(pygame_main())