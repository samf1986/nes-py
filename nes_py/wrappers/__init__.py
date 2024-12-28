"""Wrappers for altering the functionality of the game."""
from nes_py.wrappers.joypad_space import JoypadSpace


# explicitly define the outward facing API of this package
__all__ = [JoypadSpace.__name__]
