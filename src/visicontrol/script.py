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
        print(update.value)
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
                # print("reset")
                self.no_update = 0
                self.mouse_x = 0
                self.mouse_y = 0
        self.mouse_x = max(self.w * -0.5, min(update[0], self.w * 0.5)) if update[0] != 0 else self.mouse_x
        self.mouse_y = max(self.h * -0.5, min(update[1], self.h * 0.5)) if update[1] != 0 else self.mouse_y
        # The reticle itself is not "centered", need to figure something out here
        # self.reticle = pygame.Rect(self.rect.centerx + self.mouse_x, self.rect.centery + self.mouse_y, self.reticle_size, self.reticle_size)
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
    async for event in device.async_read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            # print(evdev.categorize(event))
            # print(event)
            await queue.put(Event(name, type, event))
        elif event.type == evdev.ecodes.EV_REL:
            # print(str(evdev.categorize(event)) + str(event.value))
            await queue.put(Event(name, type, event))
        

alldevices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in alldevices:
    print(device.path, device.name, device.phys)

devices = [Device("kbd0", "kbd", evdev.InputDevice('/dev/input/event6')), Device("mouse0", "mouse", evdev.InputDevice('/dev/input/event2'))]


async def pygame_main():
    pygame.init()
    print(f"--- DEBUG INFO ---")
    print(f"Pygame Version: {pygame.version.ver}")
    print(f"SDL Version: {pygame.get_sdl_version()}")
    print(f"Video Driver: {pygame.display.get_driver()}")
    print(f"------------------")
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
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

    # bg_task = asyncio.create_task(print_events("mouse", mouse, event_queue))
    # for task in ["kbd", kbd], ["mouse", mouse]:
    #     asyncio.create_task(print_events(task[0], task[1], event_queue))
    for device in devices:
        asyncio.create_task(print_events(device.type, device.name, device.obj, event_queue))

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        mouse_updates = {0: 0, 1: 0}
        # =======IMPORTANT=======
        # This shit needs some massive overhaul
        # Keyboard part is decent I guess
        # Mouse is shit: the rel position is hardcoded to one object mouse_updates
        # Then in general handling of all REL type events could be done better probably idk?
        # idk if theres an another kind of device other than a mouse that would benefit from MouseScrollBtn
        # But its only reachable from inside mouse device type I guess?? I dunno, I ceased to think tonight
        # Also clean up all the prints
        # Also between kbd and mouse theres like one snipped of code repeated 3 times, just with different event type
        # Just pull the type from event.data.type and handle it like that?
        # Still needs special case for MouseXY, its REL event happens MUCH more frequently than once a frame and it bogs down the visuals
        # Bababababababababa
        # =======================
        try:
            while True:
            # get_nowait() checks the queue without blocking the game loop
            # If the queue is empty, it raises asyncio.QueueEmpty
                event = event_queue.get_nowait()
                if event.type == "kbd":
                    print(evdev.ecodes.KEY[event.data.code] + ": " + str(event.data))
                    # print(str(evdev.categorize(event)) + " " + str(event.value))
                    try:
                        for action in input_map[(event.name, evdev.ecodes.KEY[event.data.code])]:
                            elements[action].update(event.data)
                    except:
                        print("No button " + evdev.ecodes.KEY[event.data.code])
                elif event.type == "mouse":
                    if event.data.type == 2:
                        if event.data.code == 0 or event.data.code == 1:
                            mouse_updates[event.data.code] += event.data.value
                        else:
                            try:
                                raw_name = evdev.ecodes.REL[event.data.code]
                                for action in input_map[(event.name, raw_name[0] if isinstance(raw_name, (list, tuple)) else raw_name)]:
                                    elements[action].update(event.data)
                            except:
                                # print("No button " + str(raw_name))
                                pass
                    else:
                        try:
                            raw_name = evdev.ecodes.BTN[event.data.code]
                            for action in input_map[(event.name, raw_name[0] if isinstance(raw_name, (list, tuple)) else raw_name)]:
                                elements[action].update(event.data)
                        except:
                            # print("No button " + str(raw_name))
                            pass
            
        except asyncio.QueueEmpty:
            pass
        try:
            for action in input_map[(event.name, "MouseXY")]:
                elements[action].update(mouse_updates)
        except:
            # print("No MouseRel " + evdev.name)
            pass
        # elements[("mouse0", "MouseXY")].update(mouse_updates)

        screen.fill("purple")

        for element in elements.values():
            element.draw(screen)

        pygame.display.flip()
        clock.tick(60) 
        await asyncio.sleep(0)

    # bg_task.cancel() # Stop the background task
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(pygame_main())