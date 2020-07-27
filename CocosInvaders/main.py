import cocos
import cocos.layer
import cocos.collision_model as cm
import random
import cocos.euclid as eu

from collections import defaultdict
from pyglet.window import key
from pyglet.image import load, ImageGrid, Animation


class Actor(cocos.sprite.Sprite):
    def __init__(self, image, x, y):
        super(Actor, self).__init__(image)
        pos = eu.Vector2(x, y)

        # self.position is defined in cocos.sprite.Sprite with type (int, int)
        # assigning self.position type eu.Vector2(int,int) seems to assign the type (int,int)
        self.position = pos
        self.cshape = cm.CircleShape(pos, self.width / 2)

    def move(self, offset):
        self.position += offset
        self.cshape = cm.AARectShape(self.position, self.width / 2, self.height / 2)

    def update(self, elapsed):
        """Template design pattern for the child classes to implement"""
        pass

    def collide(self, other):
        """Template design pattern for the child classes to implement"""
        pass


class PlayerCannon(Actor):
    KEYS_PRESSED = defaultdict(int)

    def __init__(self, x, y):
        super(PlayerCannon, self).__init__("img/cannon.png", x, y)
        self.speed = eu.Vector2(200, 0)

    def update(self, elapsed):
        pressed = PlayerCannon.KEYS_PRESSED
        space_pressed = pressed[key.SPACE] == 1

        if PlayerShoot.INSTANCE is None and space_pressed:
            self.parent.add(PlayerShoot(self.x, self.y + 50))

        movement = pressed[key.RIGHT] - pressed[key.LEFT]
        w = self.width / 2

        # w <= self.x <= self.parent.width is the same as
        # w <= self.x and self.x <= self.parent.width:
        if movement != 0 and w <= self.x <= self.parent.width:
            self.move(self.speed * movement * elapsed)

    def collide(self, other: cocos.cocosnode.CocosNode):
        other.kill()
        self.kill()


class GameLayer(cocos.layer.Layer):
    is_event_handler = True

    def __init__(self, hud):
        super(GameLayer, self).__init__()
        width, height = cocos.director.director.get_window_size()
        self.hud = hud
        self.width = width
        self.height = height
        self.lives = 3
        self.score = 0
        self.update_score()
        self.create_player()
        self.create_alien_group(100, 300)

        # recommended cell size is the maximum object width *1.25
        cell = self.player.width * 1.25
        self.collman = cm.CollisionManagerGrid(0, width, 0, height,
                                               cell, cell)

        # Defined in cocos.cocosnode.CocosNode
        self.schedule(self.update)

    def on_key_press(self, k, _):
        PlayerCannon.KEYS_PRESSED[k] = 1

    def on_key_release(self, k, _):
        PlayerCannon.KEYS_PRESSED[k] = 0

    def create_player(self):
        self.player = PlayerCannon(self.width / 2, 50)
        self.add(self.player)
        self.hud.update_lives(self.lives)

    def update_score(self, score=0):
        self.score += score
        self.hud.update_score(self.score)

    def create_alien_group(self, x, y):
        """(0,0) = bottom left"""
        self.alien_group = AlienGroup(x, y)
        for alien in self.alien_group:
            self.add(alien)

    def update(self, dt):
        self.collman.clear()

        node: Actor
        for _, node in self.children:
            self.collman.add(node)
            if not self.collman.knows(node):
                self.remove(node)

        # Have the PlayerShoot collide with the aliens
        # We don't do anything about the return value since
        # PlayerShoot handles killing itself and the alien it hit
        self.collide(PlayerShoot.INSTANCE)

        # If the player collides with Shoot or an Alien
        if self.collide(self.player):
            self.respawn_player()

        no_more_aliens = all([len(column.aliens) == 0 for column in self.alien_group.columns])
        if no_more_aliens:
            self.unschedule(self.update)
            self.hud.show_game_won()

        for column in self.alien_group.columns:
            shoot = column.shoot()
            if shoot is not None:
                self.add(shoot)

        for _, node in self.children:
            node.update(dt)

        self.alien_group.update(dt)
        if random.random()<0.001:
            self.add(MysteryShip(50, self.height-50))

    def collide(self, node: Actor):
        other: Actor

        # The player shoot instance can be None if there's no current shoot
        if node is not None:
            for other in self.collman.iter_colliding(node):
                node.collide(other)
                return True
        return False

    def respawn_player(self):
        """Unschedule update() when there are no more lives left to stop the main loop"""
        self.lives -= 1
        if self.lives < 0:
            self.unschedule(self.update)
            self.hud.show_game_over()
        else:
            self.create_player()


class Alien(Actor):
    def load_animation(image):
        seq = ImageGrid(load(image), 2, 1)
        return Animation.from_image_sequence(seq, 0.5)

    TYPES = {
        "1": (load_animation("img/alien1.png"), 40),
        "2": (load_animation("img/alien2.png"), 20),
        "3": (load_animation("img/alien3.png"), 10)
    }

    def from_type(x, y, alien_type, column):
        animation, score = Alien.TYPES[alien_type]
        return Alien(animation, x, y, score, column)

    # We pass a reference to alien_column so the column of aliens know which alien is at the bottom
    def __init__(self, img, x, y, score, alien_column=None):
        super(Alien, self).__init__(img, x, y)
        self.score = score
        self.alien_column = alien_column

    def on_exit(self):
        super(Alien, self).on_exit()
        if self.alien_column:
            self.alien_column.remove(self)


class MysteryShip(Alien):
    SCORES = [10, 50, 100, 200]

    def __init__(self, x, y):
        score = random.choice(MysteryShip.SCORES)
        super(MysteryShip, self).__init__("img/alien4.png", x, y, score)
        self.speed = eu.Vector2(150, 0)

    def update(self, elapsed):
        self.move(self.speed * elapsed)


class AlienColumn(object):
    def __init__(self, x, y):
        alien_types = enumerate(["3", "3", "2", "2", "1"])
        self.aliens = [Alien.from_type(x, y + i * 60, alien, self)
                       for i, alien in alien_types]

    def should_turn(self, direction):
        if len(self.aliens) == 0:
            return False
        alien = self.aliens[0]
        x, parent_width = alien.x, alien.parent.width

        right = 1
        left = -1
        return (x >= parent_width - 50 and direction == right) or (x <= 50 and direction == left)

    def remove(self, alien):
        self.aliens.remove(alien)

    def shoot(self):
        # We set a low probability of shooting since random() is called multiple times per second
        if random.random() < 0.001 and len(self.aliens) > 0:
            bottom_most_alien_position = self.aliens[0].position
            return Shoot(bottom_most_alien_position[0], bottom_most_alien_position[1] - 50)
        return None


class AlienGroup(object):
    def __init__(self, x, y):
        self.columns = [AlienColumn(x + i * 60, y)
                        for i in range(10)]
        self.speed = eu.Vector2(10, 0)

        # 1 = right
        # -1 = left
        self.direction = 1
        self.elapsed = 0.0
        self.period = 1.0

    def __iter__(self):
        for column in self.columns:
            for alien in column.aliens:
                yield alien

    def update(self, elapsed):
        self.elapsed += elapsed
        while self.elapsed >= self.period:
            self.elapsed -= self.period
            offset = self.direction * self.speed
            if self.side_reached():
                self.direction *= -1
                offset = eu.Vector2(0, -10)
            for alien in self:
                alien.move(offset)

    def side_reached(self):
        return any(map(lambda column: column.should_turn(self.direction), self.columns))


class Shoot(Actor):
    def __init__(self, x, y, image="img/shoot.png"):
        super(Shoot, self).__init__(image, x, y)
        self.speed = eu.Vector2(0, -400)

    def update(self, elapsed):
        self.move(self.speed * elapsed)


class PlayerShoot(Shoot):
    INSTANCE = None
    """The player can't shoot until the shoot hits an enemy or goes off-screen"""

    def __init__(self, x, y):
        super(PlayerShoot, self).__init__(x, y, image="img/laser.png")
        self.speed *= -1
        PlayerShoot.INSTANCE = self

    def collide(self, other):
        if isinstance(other, Alien):
            self.parent.update_score(other.score)
            other.kill()
            self.kill()

    def on_exit(self):
        super(PlayerShoot, self).on_exit()
        PlayerShoot.INSTANCE = None


class HUD(cocos.layer.Layer):
    """
    score-----------lives\n
    |                |\n
    |    game over   |\n
    |                |\n
    """

    def __init__(self):
        super(HUD, self).__init__()
        width, height = cocos.director.director.get_window_size()
        self.score_text = cocos.text.Label("", font_size=18)
        self.score_text.position = (20, height - 40)
        self.lives_text = cocos.text.Label("", font_size=18)
        self.lives_text.position = (width - 100, height - 40)
        self.add(self.score_text)
        self.add(self.lives_text)

    def update_score(self, score):
        self.score_text.element.text = "Score %s" % score

    def update_lives(self, lives):
        self.lives_text.element.text = "Lives %s" % lives

    def show_game_over(self):
        self._show_center_text("Press F to pay respects")

    def show_game_won(self):
        self._show_center_text("You won!")

    def _show_center_text(self, text):
        width, height = cocos.director.director.get_window_size()
        label = cocos.text.Label(text,
                                 font_size=50,
                                 anchor_x="center",
                                 anchor_y="center")
        label.position = (width / 2, height / 2)
        self.add(label)


if __name__ == '__main__':
    cocos.director.director.init(caption="Cocos Invaders", width=800, height=650)
    main_scene = cocos.scene.Scene()
    hud_layer = HUD()
    game_layer = GameLayer(hud_layer)

    main_scene.add(hud_layer, z=1)
    main_scene.add(game_layer, z=0)

    cocos.director.director.run(main_scene)
