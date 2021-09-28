import pygame


class Menu:
    def __init__(self):
        # Windows
        pygame.init()
        self.window = pygame.display.set_mode((1280, 720))
        pygame.display.set_caption("Practice")
        pygame.display.set_icon(pygame.image.load("assets/icon.png"))

        # Font
        self.title_font = pygame.font.Font("assets/BD_Cartoon_Shout.ttf", 72)
        self.item_font = pygame.font.Font("assets/BD_Cartoon_Shout.ttf", 48)

        # Menu items
        self.menu_items = [
            {
                'title': 'Level 1',
                'action': lambda: self.load_level("asset/level1.tmx")
            },
            {
                'title': 'Level 2',
                'action': lambda: self.load_level("asset/level2.tmx")
            },
            {
                'title': 'Quit',
                'action': lambda: self.exit_menu()
            }
        ]
        self.current_menu_item = 0
        self.menu_cursor = pygame.image.load("assets/cursor.png")

        # Loop properties
        self.clock = pygame.time.Clock()
        self.running = True

    def load_level(self, file_name):
        print("Load", file_name)

    def exit_menu(self):
        self.running = False

    def process_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.exit_menu()
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    if self.current_menu_item < len(self.menu_items) - 1:
                        self.current_menu_item += 1
                elif event.key == pygame.K_UP:
                    if self.current_menu_item > 0:
                        self.current_menu_item -= 1
                elif event.key == pygame.K_RETURN:
                    menu_item = self.menu_items[self.current_menu_item]
                    try:
                        menu_item['action']()
                    except Exception as ex:
                        print(ex)

    def update(self):
        pass

    def render(self):
        self.window.fill((0, 0, 0))

        # Initial y
        y = 50

        # Title
        surface = self.title_font.render("TANK BATTLEGROUNDS !!", True, (200, 0, 0))
        x = (self.window.get_width() - surface.get_width()) // 2
        self.window.blit(surface, (x, y))
        y += (200 * surface.get_height()) // 100

        # Compute menu width
        menu_width = 0
        for item in self.menu_items:
            surface = self.item_font.render(item['title'], True, (200, 0, 0))
            menu_width = max(menu_width, surface.get_width())
            item['surface'] = surface

        # Draw menu items
        x = (self.window.get_width() - menu_width) // 2
        for index, item in enumerate(self.menu_items):
            # Item text
            surface = item['surface']
            self.window.blit(surface, (x, y))

            # Cursor
            if index == self.current_menu_item:
                cursor_x = x - self.menu_cursor.get_width() - 10
                cursor_y = y + (surface.get_height() - self.menu_cursor.get_height()) // 2
                self.window.blit(self.menu_cursor, (cursor_x, cursor_y))

            y += (120 * surface.get_height()) // 100

        pygame.display.update()

    def run(self):
        while self.running:
            self.process_input()
            self.update()
            self.render()
            self.clock.tick(60)


menu = Menu()
menu.run()

pygame.quit()
