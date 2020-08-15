import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock

import cocos
import pyglet

from main import Alien, Bunker, PlayerCannon, Shoot
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

    def test_instantiate_actors(self):
        self.assertEqual(1, len(self.get_game_children(PlayerCannon)))
        self.assertEqual(50, len(self.get_game_children(Alien)))
        self.assertEqual(0, len(self.get_game_children(Shoot)))

        self.assertTrue(0 < len(self.get_game_children(Bunker)))

    def get_game_children(self, child_class):
        return [child for _, child in self.game_layer.children if isinstance(child, child_class)]
