import pygame
from pygame.math import Vector2
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
        self.ground = [
            [Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 2), Vector2(5, 1),
             Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1),
             Vector2(5, 1), Vector2(5, 1)],
            [Vector2(5, 1), Vector2(5, 1), Vector2(7, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 2), Vector2(7, 1),
             Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 4),
             Vector2(7, 2), Vector2(7, 2)],
            [Vector2(5, 1), Vector2(6, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 1), Vector2(6, 2), Vector2(5, 1),
             Vector2(6, 1), Vector2(6, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 2),
             Vector2(6, 1), Vector2(5, 1)],
            [Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 1), Vector2(6, 2), Vector2(5, 1),
             Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 2),
             Vector2(5, 1), Vector2(7, 1)],
            [Vector2(5, 1), Vector2(7, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 5), Vector2(7, 2),
             Vector2(7, 2), Vector2(7, 2), Vector2(7, 2), Vector2(7, 2), Vector2(7, 2), Vector2(7, 2), Vector2(8, 5),
             Vector2(5, 1), Vector2(5, 1)],
            [Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 1), Vector2(6, 2), Vector2(5, 1),
             Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 2),
             Vector2(5, 1), Vector2(7, 1)],
            [Vector2(6, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 2), Vector2(5, 1),
             Vector2(5, 1), Vector2(7, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 2),
             Vector2(7, 1), Vector2(5, 1)],
            [Vector2(5, 1), Vector2(5, 1), Vector2(6, 4), Vector2(7, 2), Vector2(7, 2), Vector2(8, 4), Vector2(5, 1),
             Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(6, 2),
             Vector2(5, 1), Vector2(5, 1)],
            [Vector2(5, 1), Vector2(5, 1), Vector2(6, 2), Vector2(5, 1), Vector2(5, 1), Vector2(7, 1), Vector2(5, 1),
             Vector2(5, 1), Vector2(6, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(7, 4),
             Vector2(7, 2), Vector2(7, 2)],
            [Vector2(5, 1), Vector2(5, 1), Vector2(6, 2), Vector2(6, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1),
             Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1), Vector2(5, 1),
             Vector2(5, 1), Vector2(5, 1)]
        ]
        self.units = [Unit(self, Vector2(1, 9), Vector2(1, 0)),
                      Unit(self, Vector2(6, 3), Vector2(0, 2)),
                      Unit(self, Vector2(6, 5), Vector2(0, 2)),
                      Unit(self, Vector2(13, 3), Vector2(0, 1)),
                      Unit(self, Vector2(13, 6), Vector2(0, 1))]
        self.walls = [
            [None, None, None, None, None, None, None, None, None, Vector2(1, 3), Vector2(1, 1), Vector2(1, 1),
             Vector2(1, 1), Vector2(1, 1), Vector2(1, 1), Vector2(1, 1)],
            [None, None, None, None, None, None, None, None, None, Vector2(2, 1), None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None, None, Vector2(2, 1), None, None, Vector2(1, 3),
             Vector2(1, 1), Vector2(0, 3), None],
            [None, None, None, None, None, None, None, Vector2(1, 1), Vector2(1, 1), Vector2(3, 3), None, None,
             Vector2(2, 1), None, Vector2(2, 1), None],
            [None, None, None, None, None, None, None, None, None, None, None, None, Vector2(2, 1), None, Vector2(2, 1),
             None],
            [None, None, None, None, None, None, None, Vector2(1, 1), Vector2(1, 1), Vector2(0, 3), None, None,
             Vector2(2, 1), None, Vector2(2, 1), None],
            [None, None, None, None, None, None, None, None, None, Vector2(2, 1), None, None, Vector2(2, 1), None,
             Vector2(2, 1), None],
            [None, None, None, None, None, None, None, None, None, Vector2(2, 1), None, None, Vector2(2, 3),
             Vector2(1, 1), Vector2(3, 3), None],
            [None, None, None, None, None, None, None, None, None, Vector2(2, 1), None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None, None, Vector2(2, 3), Vector2(1, 1), Vector2(1, 1),
             Vector2(1, 1), Vector2(1, 1), Vector2(1, 1), Vector2(1, 1)]
        ]
        self.bullets = []
        self.bullet_speed = 0.1
        self.bullet_range = 4
        self.bullet_delay = 10

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
            return
        # Nothing happens, continue bullet trajectory
        self.bullet.position = new_position


class DeleteDestroyedCommand(Command):
    def __init__(self, item_list):
        self.item_list = item_list

    def execute(self):
        new_list = [item for item in self.item_list if item.status == "alive"]
        self.item_list[:] = new_list


###############################################################################
#                                Rendering                                    #
###############################################################################


class Layer:
    def __init__(self, cell_size, image_file):
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
    def __init__(self, ui, image_file, game_state, array):
        super().__init__(ui, image_file)
        self.game_state = game_state
        self.array = array

    def render(self, surface):
        for y in range(self.game_state.world_height):
            for x in range(self.game_state.world_width):
                tile = self.array[y][x]
                if tile is not None:
                    self.render_tile(surface, Vector2(x, y), tile)


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


###############################################################################
#                             User Interface                                  #
###############################################################################


class UserInterface:
    def __init__(self):
        pygame.init()

        self.game_state = GameState()

        # Rendering properties
        self.cell_size = Vector2(64, 64)
        self.layers = [
            ArrayLayer(self.cell_size, "assets/ground.png", self.game_state, self.game_state.ground),
            ArrayLayer(self.cell_size, "assets/walls.png", self.game_state, self.game_state.walls),
            UnitsLayer(self.cell_size, "assets/units.png", self.game_state, self.game_state.units),
            BulletLayer(self.cell_size, "assets/explosions.png", self.game_state, self.game_state.bullets)
        ]

        # Window
        window_size = self.game_state.world_size.elementwise() * self.cell_size
        self.window = pygame.display.set_mode((int(window_size.x), int(window_size.y)))
        pygame.display.set_caption("Practice")
        pygame.display.set_icon(pygame.image.load("assets/icon.png"))

        # Controls
        self.player_unit = self.game_state.units[0]
        self.commands = []

        # Loop properties
        self.clock = pygame.time.Clock()
        self.running = True

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
                self.running = False
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
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

        # Keyboard controls the moves of the player's unit
        if move_vector.x != 0 or move_vector.y != 0:
            self.commands.append(MoveCommand(self.game_state, self.player_unit, move_vector))

        # Mouse controls the target of the player's unit
        mouse_position = pygame.mouse.get_pos()
        target_cell = Vector2()
        target_cell.x = mouse_position[0] / self.cell_width - 0.5
        target_cell.y = mouse_position[1] / self.cell_width - 0.5
        self.commands.append(TargetCommand(self.game_state, self.player_unit, target_cell))

        # Other units always target the player's unit and shoot if close enough
        for unit in self.game_state.units:
            if unit is not self.player_unit:
                self.commands.append(TargetCommand(self.game_state, unit, self.player_unit.position))
                distance = unit.position.distance_to(self.player_unit.position)
                if distance <= self.game_state.bullet_range:
                    self.commands.append(ShootCommand(self.game_state, unit))

        # Shoot if left mouse was clicked
        if mouse_clicked:
            self.commands.append(ShootCommand(self.game_state, self.player_unit))

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

    def render(self):
        self.window.fill((0, 0, 0))

        for layer in self.layers:
            layer.render(self.window)

        pygame.display.update()

    def run(self):
        while self.running:
            self.process_input()
            self.update()
            self.render()
            self.clock.tick(60)


user_interface = UserInterface()
user_interface.run()

pygame.quit()
