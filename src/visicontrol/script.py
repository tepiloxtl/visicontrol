import evdev
import pygame
import asyncio

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
    def __init__(self, x, y, w, h, label):
        self.rect = pygame.Rect(x, y, w, h)
        self.reticle = pygame.Rect(self.rect.centerx, self.rect.centery, 5, 5)
        self.label = label

        self.bg_color = (30,30,30)
        self.reticle_color = (255,30,30)
        self.border_color = (200,200,200)
        self.text_color = (255,255,255)
        self.font = pygame.font.SysFont("Arial", 16)
    
    def update(self, update):
        # print(update.value)
        # REL_Y = code 01, up is negative
        # REL_X = code 00, left is negative
        if update.code == 1:
            self.reticle = pygame.Rect(self.rect.centerx, self.rect.centery + (update.value * 10), 5, 5)
        elif update.code == 0:
            self.reticle = pygame.Rect(self.rect.centerx + (update.value * 10), self.rect.centery, 5, 5)
    
    def draw(self, screen):
        # current_color = self.active_color if self.is_pressed else self.bg_color

        pygame.draw.rect(screen, self.bg_color, self.rect)
        pygame.draw.rect(screen, self.border_color, self.rect, 2)
        pygame.draw.rect(screen, self.reticle_color, self.reticle)

        # label_surf = self.font.render(self.label, True, self.text_color)
        # text_x = self.rect.centerx - (label_surf.get_width() // 2)
        # text_y = self.rect.centery - (label_surf.get_height() // 2)
        # screen.blit(label_surf, (text_x, text_y))

async def print_events(type, device, queue):
    async for event in device.async_read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            # print(evdev.categorize(event))
            # print(event)
            await queue.put([type, event])
        elif event.type == evdev.ecodes.EV_REL:
            # print(str(evdev.categorize(event)) + str(event.value))
            await queue.put([type, event])
        

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in devices:
    print(device.path, device.name, device.phys)

kbd = evdev.InputDevice('/dev/input/event6')
mouse = evdev.InputDevice('/dev/input/event2')


async def pygame_main():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True
    event_queue = asyncio.Queue()

    elements = {
        "KEY_Q":     Button(50, 50, 100, 100, "Q"),
        "KEY_W":     Button(150, 50, 100, 100, "W"),
        "KEY_E":     Button(250, 50, 100, 100, "E"),
        "KEY_R":     Button(350, 50, 100, 100, "R"),
        "KEY_T":     Button(450, 50, 100, 100, "T"),
        "KEY_Y":     Button(550, 50, 100, 100, "Y"),
        "MouseXY":     MouseRel(800, 50, 100, 100, "")
    }

    # bg_task = asyncio.create_task(print_events("mouse", mouse, event_queue))
    for task in ["kbd", kbd], ["mouse", mouse]:
        asyncio.create_task(print_events(task[0], task[1], event_queue))

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        mouse_updates = {}
        try:
            while True:
            # get_nowait() checks the queue without blocking the game loop
            # If the queue is empty, it raises asyncio.QueueEmpty
                event = event_queue.get_nowait()
                if event[0] == "kbd":
                    print(evdev.ecodes.KEY[event[1].code] + ": " + str(event[1]))
                    # print(str(evdev.categorize(event)) + " " + str(event.value))
                    try:
                        elements[evdev.ecodes.KEY[event[1].code]].update(event[1])
                    except:
                        print("No button " + evdev.ecodes.KEY[event[1].code])
                elif event[0] == "mouse":
                    # print(evdev.categorize(event[1]))
                    # print(event[1])
                    mouse_updates[event[1].code] = event[1]
            
        except asyncio.QueueEmpty:
            pass

        for code, event in mouse_updates.items():
            elements["MouseXY"].update(event)

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