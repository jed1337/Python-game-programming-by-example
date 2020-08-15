import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock

import cocos
import pyglet

from main import Alien, Bunker, PlayerCannon, Shoot, PlayerShoot
from main import GameLayer


class TestGameLayer(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cocos.director.director.init()
        TestGameLayer.have_pyglet_point_to_CocosInvaders_folder()

    @staticmethod
    def have_pyglet_point_to_CocosInvaders_folder():
        pyglet.resource.path = [str(Path(os.path.realpath(__file__)).parent)]
        pyglet.resource.reindex()

    def setUp(self) -> None:
        self.game_layer = GameLayer(MagicMock())

    def test_did_instantiate_actors(self):
        self.assertEqual(1, len(self.get_game_children_by_type(PlayerCannon)))
        self.assertEqual(50, len(self.get_game_children_by_type(Alien)))
        self.assertEqual(0, len(self.get_game_children_by_type(Shoot)))

        self.assertTrue(0 < len(self.get_game_children_by_type(Bunker)))

    def test_collide_shoot_and_alien(self):
        player_shoot = PlayerShoot(100, 100)
        alien = Alien("img/alien1.png", 100, 100, 15)

        self.game_layer.add(player_shoot)
        self.game_layer.add(alien)

        self.assertTrue(player_shoot in self.get_game_children())
        self.assertTrue(alien in self.get_game_children())
        self.assertTrue(self.game_layer.score == 0)

        self.game_layer.update(0)

        self.assertTrue(player_shoot not in self.get_game_children())
        self.assertTrue(alien not in self.get_game_children())
        self.assertTrue(self.game_layer.score == 15)

    def get_game_children(self):
        return [child for _, child in self.game_layer.children]

    def get_game_children_by_type(self, child_class):
        return [child for child in self.get_game_children() if isinstance(child, child_class)]
