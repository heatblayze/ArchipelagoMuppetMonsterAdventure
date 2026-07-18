from AutoWorld import World

from BaseClasses import Item, Location

from .Constants import mma_game_name


class MMAItem(Item):
    game: str = mma_game_name


class MMALocation(Location):
    game: str = mma_game_name


class MuppetMonsterAdventureWorld(World):
    game = "Muppet Monster Adventure"
