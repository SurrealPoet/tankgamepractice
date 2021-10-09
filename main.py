import pygame
from pygame.math import Vector2
import tmx
import os
import math

os.environ['SDL_VIDEO_CENTERED'] = '1'


###############################################################################
#                               Game State                                    #
###############################################################################


class GameItem:
    def __init__(self, state, position, tile):
        self.state = state
        self.status = "alive"
        self.position = position
        self.tile = tile
        self.orientation = 0


class Unit(GameItem):
    def __init__(self, state, position, tile):
        super().__init__(state, position, tile)
        self.weapon_target = Vector2(0, 0)
        self.last_bullet_epoch = -100


class Bullet(GameItem):
    def __init__(self, state, unit):
        super().__init__(state, unit.position, Vector2(2, 1))
        self.unit = unit
        self.start_position = unit.position
        self.end_position = unit.weapon_target


class GameState:
    def __init__(self):
        self.epoch = 0
        self.world_size = Vector2(16, 10)
        self.ground = [[Vector2(5, 1)] * 16] * 10
        self.walls = [[None] * 16] * 10
        self.units = [Unit(self, Vector2(8, 9), Vector2(1, 0))]
        self.bullets = []
        self.bullet_speed = 0.1
        self.bullet_range = 4
        self.bullet_delay = 5
        self.observers = []

    @property
    def world_width(self):
        return int(self.world_size.x)

    @property
    def world_height(self):
        return int(self.world_size.y)

    def is_inside(self, position):
        """
        Returns true if position is inside the world
        """
        return 0 <= position.x < self.world_width and 0 <= position.y < self.world_height

    def find_unit(self, position):
        """
        Returns the index of the first unit at position, otherwise None.
        """
        for unit in self.units:
            if int(unit.position.x) == int(position.x) and int(unit.position.y) == int(position.y):
                return unit
        return None

    def find_live_unit(self, position):
        """
        Returns the index of the first live unit at position, otherwise None.
        """
        unit = self.find_unit(position)
        if unit is None or unit.status != "alive":
            return None
        return unit

    def add_observer(self, observer):
        self.observers.append(observer)

    def notify_unit_destroyed(self, unit):
        for observer in self.observers:
            observer.unit_destroyed(unit)


class GameStateObserver:
    def unit_destroyed(self, unit):
        pass


###############################################################################
#                                Commands                                     #
###############################################################################


class Command:
    def execute(self):
        raise NotImplementedError


class MoveCommand(Command):
    def __init__(self, state, unit, move_vector):
        self.state = state
        self.unit = unit
        self.move_vector = move_vector

    def execute(self):
        # Destroyed units can't move
        if self.unit.status != "alive":
            return

        # Update unit orientation
        if self.move_vector.x < 0:
            self.unit.orientation = 90
        elif self.move_vector.x > 0:
            self.unit.orientation = -90
        if self.move_vector.y < 0:
            self.unit.orientation = 0
        elif self.move_vector.y > 0:
            self.unit.orientation = 180

        # Compute new tank position
        new_position = self.unit.position + self.move_vector

        # Don't allow outside world
        # if 0 > new_position.x or new_position.x >= self.state.world_size.x:
        #     new_position.x = self.unit.position.x
        # if 0 > new_position.y or new_position.y >= self.state.world_size.y:
        #     new_position.y = self.unit.position.y
        if not self.state.is_inside(new_position):
            return

        # Don't allow wall positions
        if self.state.walls[int(new_position.y)][int(new_position.x)] is not None:
            return

        # Don't allow other unit positions
        unit_index = self.state.find_unit(new_position)
        if unit_index is not None:
            return

        self.unit.position = new_position


class TargetCommand(Command):
    def __init__(self, state, unit, target):
        self.state = state
        self.unit = unit
        self.target = target

    def execute(self):
        self.unit.weapon_target = self.target


class ShootCommand(Command):
    def __init__(self, state, unit):
        self.state = state
        self.unit = unit

    def execute(self):
        if self.unit.status != "alive":
            return
        if self.state.epoch - self.unit.last_bullet_epoch < self.state.bullet_delay:
            return
        self.unit.last_bullet_epoch = self.state.epoch
        self.state.bullets.append(Bullet(self.state, self.unit))


class MoveBulletCommand(Command):
    def __init__(self, state, bullet):
        self.state = state
        self.bullet = bullet

    def execute(self):
        direction = (self.bullet.end_position - self.bullet.start_position).normalize()
        new_position = self.bullet.position + self.state.bullet_speed * direction
        new_center_position = new_position + Vector2(0.5, 0.5)
        # If bullet goes outside the world, destroy it
        if not self.state.is_inside(new_position):
            self.bullet.status = "destroyed"
            return
        # If the bullet goes towards the target cell, destroy it
        if ((direction.x >= 0 and new_position.x >= self.bullet.end_position.x)
            or (direction.x < 0 and new_position.x <= self.bullet.end_position.x)) \
                and ((direction.y >= 0 and new_position.y >= self.bullet.end_position.y)
                     or (direction.y < 0 and new_position.y <= self.bullet.end_position.y)):
            self.bullet.status = "destroyed"
            return
        # If the bullet is outside the allowed range, destroy it
        if new_position.distance_to(self.bullet.start_position) >= self.state.bullet_range:
            self.bullet.status = "destroyed"
            return
        # If the bullet hits a unit, destroy the bullet and the unit
        unit = self.state.find_live_unit(new_center_position)
        if unit is not None and unit != self.bullet.unit:
            self.bullet.status = "destroyed"
            unit.status = "destroyed"
            self.state.notify_unit_destroyed(unit)
            return
        # Nothing happens, continue bullet trajectory
        self.bullet.position = new_position


class DeleteDestroyedCommand(Command):
    def __init__(self, item_list):
        self.item_list = item_list

    def execute(self):
        new_list = [item for item in self.item_list if item.status == "alive"]
        self.item_list[:] = new_list


class LoadLevelCommand(Command):
    def __init__(self, game_mode, file_name):
        self.game_mode = game_mode
        self.file_name = file_name

    def decode_layer(self, tile_map, layer):
        """
        Decode layer and check layer properties

        Returns the corresponding tileset
        """
        if not isinstance(layer, tmx.Layer):
            raise RuntimeError("Error in {}: invalid layer type".format(self.file_name))
        if len(layer.tiles) != tile_map.width * tile_map.height:
            raise RuntimeError("Error in {}: invalid tiles count".format(self.file_name))

        # Guess which tileset is used by this layer
        gid = None
        for tile in layer.tiles:
            if tile.gid != 0:
                gid = tile.gid
                break
        if gid is None:
            if len(tile_map.tilesets) == 0:
                raise RuntimeError("Error in {}: no tilesets".format(self.file_name))
            tileset = tile_map.tilesets[0]
        else:
            tileset = None
            for t in tile_map.tilesets:
                if t.firstgid <= gid < t.firstgid + t.tilecount:
                    tileset = t
                    break
            if tileset is None:
                raise RuntimeError("Error in {}: no corresponding tileset".format(self.file_name))

        # Check the tileset
        if tileset.columns <= 0:
            raise RuntimeError("Error in {}: invalid columns count".format(self.file_name))
        if tileset.image.data is not None:
            raise RuntimeError("Error in {}: embedded tileset image is not supported".format(self.file_name))

        return tileset

    def decode_array_layer(self, tile_map, layer):
        """
        Create an array from a tileMap layer
        """
        tileset = self.decode_layer(tile_map, layer)

        array = [None] * tile_map.height
        for y in range(tile_map.height):
            array[y] = [None] * tile_map.width
            for x in range(tile_map.width):
                tile = layer.tiles[x + y * tile_map.width]
                if tile.gid == 0:
                    continue
                lid = tile.gid - tileset.firstgid
                if lid < 0 or lid >= tileset.tilecount:
                    raise RuntimeError("Error in {}: invalid tile id".format(self.file_name))
                tile_x = lid % tileset.columns
                tile_y = lid // tileset.columns
                array[y][x] = Vector2(tile_x, tile_y)

        return tileset, array

    def decode_units_layer(self, state, tile_map, layer):
        """
        Create a list from a tileMap layer
        """
        tileset = self.decode_layer(tile_map, layer)

        units = []
        for y in range(tile_map.height):
            for x in range(tile_map.width):
                tile = layer.tiles[x + y * tile_map.width]
                if tile.gid == 0:
                    continue
                lid = tile.gid - tileset.firstgid
                if lid < 0 or lid >= tileset.tilecount:
                    raise RuntimeError("Error in {}: invalid tile id".format(self.file_name))
                tile_x = lid % tileset.columns
                tile_y = lid // tileset.columns
                unit = Unit(state, Vector2(x, y), Vector2(tile_x, tile_y))
                units.append(unit)

        return tileset, units

    def execute(self):
        # Load level
        if not os.path.exists(self.file_name):
            raise RuntimeError("No file {}".format(self.file_name))
        tile_map = tmx.TileMap.load(self.file_name)

        # Check main properties
        if tile_map.orientation != "orthogonal":
            raise RuntimeError("Error in {}: invalid orientation".format(self.file_name))
        if len(tile_map.layers) != 5:
            raise RuntimeError("Error in {}: 5 layers are expected".format(self.file_name))

        # World size
        state = self.game_mode.game_state
        state.world_size = Vector2(tile_map.width, tile_map.height)

        # Ground layer
        tileset, array = self.decode_array_layer(tile_map, tile_map.layers[0])
        cell_size = Vector2(tileset.tilewidth, tileset.tileheight)
        state.ground[:] = array
        image_file = tileset.image.source
        self.game_mode.layers[0].set_tileset(cell_size, image_file)

        # Walls Layer
        tileset, array = self.decode_array_layer(tile_map, tile_map.layers[1])
        if tileset.tilewidth != cell_size.x or tileset.tileheight != cell_size.y:
            raise RuntimeError("Error in {}: tileset sizes must be the same in all layers".format(self.file_name))
        state.walls[:] = array
        image_file = tileset.image.source
        self.game_mode.layers[1].set_tileset(cell_size, image_file)

        # Units layer
        tanks_tileset, tanks = self.decode_units_layer(state, tile_map, tile_map.layers[2])
        towers_tileset, towers = self.decode_units_layer(state, tile_map, tile_map.layers[3])
        if tanks_tileset != towers_tileset:
            raise RuntimeError("Error in {}: tanks and towers tilesets must be the same")
        if tanks_tileset.tilewidth != cell_size.x or tanks_tileset.tileheight != cell_size.y:
            raise RuntimeError("Error in {}: tile sizes must be the same in all layers".format(self.file_name))
        state.units[:] = tanks + towers
        cell_size = Vector2(tanks_tileset.tilewidth, tanks_tileset.tileheight)
        image_file = tanks_tileset.image.source
        self.game_mode.layers[2].set_tileset(cell_size, image_file)

        # Player units
        self.game_mode.player_unit = tanks[0]

        # Explosion layer
        tileset, array = self.decode_array_layer(tile_map, tile_map.layers[4])
        if tileset.tilewidth != cell_size.x or tileset.tileheight != cell_size.y:
            raise RuntimeError("Error in {}: tile sizes must be the same in a ll layers".format(self.file_name))
        state.bullets.clear()
        image_file = tileset.image.source
        self.game_mode.layers[3].set_tileset(cell_size, image_file)

        # Window
        window_size = state.world_size.elementwise() * cell_size
        self.game_mode.ui.window = pygame.display.set_mode((int(window_size.x), int(window_size.y)))

        # Resume game
        self.game_mode.game_over = False


###############################################################################
#                                Rendering                                    #
###############################################################################


class Layer(GameStateObserver):
    def __init__(self, cell_size, image_file):
        self.cell_size = cell_size
        self.texture = pygame.image.load(image_file)

    def set_tileset(self, cell_size, image_file):
        self.cell_size = cell_size
        self.texture = pygame.image.load(image_file)

    @property
    def cell_width(self):
        return int(self.cell_size.x)

    @property
    def cell_height(self):
        return int(self.cell_size.y)

    def render_tile(self, surface, position, tile, angle=None):
        # Location on screen
        sprite_point = position.elementwise() * self.cell_size

        # Texture
        texture_point = tile.elementwise() * self.cell_size
        texture_rect = pygame.Rect(int(texture_point.x), int(texture_point.y), self.cell_width, self.cell_height)

        # Draw
        if angle is None:
            surface.blit(self.texture, sprite_point, texture_rect)
        else:
            # Extract the tile in a surface
            texture_tile = pygame.Surface((self.cell_width, self.cell_height), pygame.SRCALPHA)
            texture_tile.blit(self.texture, (0, 0), texture_rect)
            # Rotate the surface with the tile
            rotated_tile = pygame.transform.rotate(texture_tile, angle)
            # Compute the new coordinate on the screen, knowing that we rotate around the center of tile
            sprite_point.x -= (rotated_tile.get_width() - texture_tile.get_width()) // 2
            sprite_point.y -= (rotated_tile.get_height() - texture_tile.get_height()) // 2
            # Render the rotated_tile
            surface.blit(rotated_tile, sprite_point)

    def render(self, surface):
        raise NotImplementedError


class ArrayLayer(Layer):
    def __init__(self, ui, image_file, game_state, array, surface_flags=pygame.SRCALPHA):
        super().__init__(ui, image_file)
        self.game_state = game_state
        self.array = array
        self.surface = None
        self.surface_flags = surface_flags

    def set_tileset(self, cell_size, image_file):
        super().set_tileset(cell_size, image_file)
        self.surface = None

    def render(self, surface):
        if self.surface is None:
            self.surface = pygame.Surface(surface.get_size(), flags=self.surface_flags)
            for y in range(self.game_state.world_height):
                for x in range(self.game_state.world_width):
                    tile = self.array[y][x]
                    if tile is not None:
                        self.render_tile(self.surface, Vector2(x, y), tile)
        surface.blit(self.surface, (0, 0))


class UnitsLayer(Layer):
    def __init__(self, ui, image_file, game_state, units):
        super().__init__(ui, image_file)
        self.game_state = game_state
        self.units = units

    def render(self, surface):
        for unit in self.units:
            self.render_tile(surface, unit.position, unit.tile, unit.orientation)
            if unit.status == "alive":
                size = unit.weapon_target - unit.position
                angle = math.atan2(-size.x, -size.y) * 180 / math.pi
                self.render_tile(surface, unit.position, Vector2(0, 6), angle)


class BulletLayer(Layer):
    def __init__(self, ui, image_file, game_state, bullets):
        super().__init__(ui, image_file)
        self.game_state = game_state
        self.bullets = bullets

    def render(self, surface):
        for bullet in self.bullets:
            if bullet.status == "alive":
                self.render_tile(surface, bullet.position, bullet.tile, bullet.orientation)


class ExplosionLayer(Layer):
    def __init__(self, ui, image_file):
        super().__init__(ui, image_file)
        self.explosions = []
        self.max_frame_index = 27

    def add(self, position):
        self.explosions.append({'position': position, 'frame_index': 0})

    def unit_destroyed(self, unit):
        self.add(unit.position)

    def render(self, surface):
        for explosion in self.explosions:
            frame_index = math.floor(explosion['frame_index'])
            self.render_tile(surface, explosion['position'], Vector2(frame_index, 4))
            explosion['frame_index'] += 0.5
        self.explosions = [explosion for explosion in self.explosions
                           if explosion['frame_index'] < self.max_frame_index]


###############################################################################
#                                Game Modes                                   #
###############################################################################


class GameMode:
    def process_input(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()

    def render(self, window):
        raise NotImplementedError()


class MessageGameMode(GameMode):
    def __init__(self, ui, message):
        self.ui = ui
        self.font = pygame.font.Font("assets/BD_Cartoon_Shout.ttf", 36)
        self.message = message

    def process_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.ui.quit_game()
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE \
                        or event.key == pygame.K_SPACE \
                        or event.key == pygame.K_RETURN:
                    self.ui.show_menu()

    def update(self):
        pass

    def render(self, window):
        surface = self.font.render(self.message, True, (200, 0, 0))
        x = (window.get_width() - surface.get_width()) // 2
        y = (window.get_height() - surface.get_height()) // 2
        window.blit(surface, (x, y))


class MenuGameMode(GameMode):
    def __init__(self, ui):
        self.ui = ui

        # Font
        self.title_font = pygame.font.Font("assets/BD_Cartoon_Shout.ttf", 72)
        self.item_font = pygame.font.Font("assets/BD_Cartoon_Shout.ttf", 48)

        # Menu items
        self.menu_items = [
            {
                'title': 'Level 1',
                'action': lambda: self.ui.load_level("assets/level1.tmx")
            },
            {
                'title': 'Level 2',
                'action': lambda: self.ui.load_level("assets/level2.tmx")
            },
            {
                'title': 'Level 3',
                'action': lambda: self.ui.load_level("assets/level3.tmx")
            },
            {
                'title': 'Quit',
                'action': lambda: self.ui.quit_game()
            }
        ]

        # Compute menu width
        self.menu_width = 0
        for item in self.menu_items:
            surface = self.item_font.render(item['title'], True, (200, 0, 0))
            self.menu_width = max(self.menu_width, surface.get_width())
            item['surface'] = surface

        self.current_menu_item = 0
        self.menu_cursor = pygame.image.load("assets/cursor.png")

    def process_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.ui.quit_game()
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.ui.show_game()
                elif event.key == pygame.K_DOWN:
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

    def render(self, window):
        # Initial y
        y = 50

        # Title
        surface = self.title_font.render("TANK BATTLEGROUNDS !!", True, (200, 0, 0))
        x = (window.get_width() - surface.get_width()) // 2
        window.blit(surface, (x, y))
        y += (200 * surface.get_height()) // 100

        # Draw menu items
        x = (window.get_width() - self.menu_width) // 2
        for index, item in enumerate(self.menu_items):
            # Item text
            surface = item['surface']
            window.blit(surface, (x, y))

            # Cursor
            if index == self.current_menu_item:
                cursor_x = x - self.menu_cursor.get_width() - 10
                cursor_y = y + (surface.get_height() - self.menu_cursor.get_height()) // 2
                window.blit(self.menu_cursor, (cursor_x, cursor_y))

            y += (120 * surface.get_height()) // 100


class PlayGameMode(GameMode):
    def __init__(self, ui):
        self.ui = ui

        # Game state
        self.game_state = GameState()

        # Rendering properties
        self.cell_size = Vector2(64, 64)

        # Layers
        self.layers = [
            ArrayLayer(self.cell_size, "assets/ground.png", self.game_state, self.game_state.ground, 0),
            ArrayLayer(self.cell_size, "assets/walls.png", self.game_state, self.game_state.walls),
            UnitsLayer(self.cell_size, "assets/units.png", self.game_state, self.game_state.units),
            BulletLayer(self.cell_size, "assets/explosions.png", self.game_state, self.game_state.bullets),
            ExplosionLayer(self.cell_size, "assets/explosions.png")
        ]

        # All layers listen to game state events
        for layer in self.layers:
            self.game_state.add_observer(layer)

        # Controls
        self.player_unit = self.game_state.units[0]
        self.game_over = False
        self.commands = []

    @property
    def cell_width(self):
        return int(self.cell_size.x)

    @property
    def cell_height(self):
        return int(self.cell_size.y)

    def process_input(self):
        # Pygame events (close, keyboard, and mouse click)
        move_vector = Vector2()
        mouse_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.ui.quit_game()
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.ui.show_menu()
                    break
                if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    move_vector.x = 1
                if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    move_vector.x = -1
                if event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    move_vector.y = 1
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    move_vector.y = -1
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_clicked = True

        # If the game is over, all commands creations are disabled
        if self.game_over:
            return

        # Keyboard controls the moves of the player's unit
        if move_vector.x != 0 or move_vector.y != 0:
            self.commands.append(MoveCommand(self.game_state, self.player_unit, move_vector))

        # Mouse controls the target of the player's unit
        mouse_position = pygame.mouse.get_pos()
        target_cell = Vector2()
        target_cell.x = mouse_position[0] / self.cell_width - 0.5
        target_cell.y = mouse_position[1] / self.cell_width - 0.5
        self.commands.append(TargetCommand(self.game_state, self.player_unit, target_cell))

        # Shoot if left mouse was clicked
        if mouse_clicked:
            self.commands.append(ShootCommand(self.game_state, self.player_unit))

        # Other units always target the player's unit and shoot if close enough
        for unit in self.game_state.units:
            if unit != self.player_unit:
                self.commands.append(TargetCommand(self.game_state, unit, self.player_unit.position))
                distance = unit.position.distance_to(self.player_unit.position)
                if distance <= self.game_state.bullet_range:
                    self.commands.append(ShootCommand(self.game_state, unit))

        # Bullets automatic movement
        for bullet in self.game_state.bullets:
            self.commands.append(MoveBulletCommand(self.game_state, bullet))

        # Delete any destroyed bullet
        self.commands.append(DeleteDestroyedCommand(self.game_state.bullets))

    def update(self):
        for command in self.commands:
            command.execute()
        self.commands.clear()
        self.game_state.epoch += 1

        # Check game over
        if self.player_unit.status != "alive":
            self.game_over = True
            self.ui.show_message("GAME OVER")
        else:
            one_enemy_still_lives = False
            for unit in self.game_state.units:
                if unit == self.player_unit:
                    continue
                if unit.status == "alive":
                    one_enemy_still_lives = True
                    break
            if not one_enemy_still_lives:
                self.game_over = True
                self.ui.show_message("Victory !")

    def render(self, window):
        for layer in self.layers:
            layer.render(window)


###############################################################################
#                             User Interface                                  #
###############################################################################


class UserInterface:
    def __init__(self):
        # Window
        pygame.init()
        self.window = pygame.display.set_mode((1280, 720))
        pygame.display.set_caption("Practice")
        pygame.display.set_icon(pygame.image.load("assets/icon.png"))

        # Modes
        self.play_game_mode = None
        self.overlay_game_mode = MenuGameMode(self)
        self.current_active_mode = 'Overlay'

        # Loop properties
        self.clock = pygame.time.Clock()
        self.running = True

    def load_level(self, file_name):
        if self.play_game_mode is None:
            self.play_game_mode = PlayGameMode(self)
        self.play_game_mode.commands.append(LoadLevelCommand(self.play_game_mode, file_name))
        try:
            self.play_game_mode.update()
            self.current_active_mode = 'Play'
        except Exception as ex:
            print(ex)
            self.play_game_mode = None
            self.show_message("Level loading failed :-(")

    def show_game(self):
        if self.play_game_mode is not None:
            self.current_active_mode = 'Play'

    def show_menu(self):
        self.overlay_game_mode = MenuGameMode(self)
        self.current_active_mode = 'Overlay'

    def show_message(self, message):
        self.overlay_game_mode = MessageGameMode(self, message)
        self.current_active_mode = 'Overlay'

    def quit_game(self):
        self.running = False

    def run(self):
        while self.running:
            # Inputs and updates are exclusives
            if self.current_active_mode == 'Overlay':
                self.overlay_game_mode.process_input()
                self.overlay_game_mode.update()
            elif self.play_game_mode is not None:
                self.play_game_mode.process_input()
                try:
                    self.play_game_mode.update()
                except Exception as ex:
                    print(ex)
                    self.play_game_mode = None
                    self.show_message("Error during the game update...")

            # Render game (if any), and then the overlay (if active)
            if self.play_game_mode is not None:
                self.play_game_mode.render(self.window)
            else:
                self.window.fill((0, 0, 0))
            if self.current_active_mode == 'Overlay':
                dark_surface = pygame.Surface(self.window.get_size(), flags=pygame.SRCALPHA)
                pygame.draw.rect(dark_surface, (0, 0, 0, 150), dark_surface.get_rect())
                self.window.blit(dark_surface, (0, 0))
                self.overlay_game_mode.render(self.window)

            # Update display
            pygame.display.update()
            self.clock.tick(60)


user_interface = UserInterface()
user_interface.run()

pygame.quit()
