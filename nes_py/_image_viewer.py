"""A simple class for viewing images using pyglet."""
import threading
from typing import Dict
from typing import List
from typing import Tuple
from typing import Optional
from typing import ClassVar
from dataclasses import dataclass

import pyglet
import numpy as np
import pyglet.gl as gl
from pyglet.window import key
from pyglet.window import BaseWindow



@dataclass(init=False)
class ImageViewer:
    """A class for displaying images using pyglet window system.

    This class provides functionality to create and manage a window for displaying
    RGB image arrays. It supports keyboard monitoring and window management.

    Attributes:
        caption (str): The title of the window.
        height (int): The height of the window in pixels.
        width (int): The width of the window in pixels.
        monitor_keyboard (bool): Whether to monitor keyboard events.
        relevant_keys (Optional[List[int]]): List of key codes to monitor. If None, all keys are monitored.
        _pressed_keys (List[int]): Internal list of currently pressed keys.
        _is_escape_pressed (bool): Internal flag for escape key state.
        _window (Optional[BaseWindow]): Internal pyglet window instance.
    """

    caption: str
    height: int
    width: int
    monitor_keyboard: bool
    _pressed_keys: List[int]
    _is_escape_pressed: bool
    relevant_keys: Optional[List[int]]
    _window: Optional[BaseWindow]

    # Map pyglet key codes to their native equivalents
    KEY_MAP: ClassVar[Dict[int, int]] = {
        key.ENTER: ord('\r'),
        key.SPACE: ord(' '),
    }

    def __init__(
        self, 
        caption: str, 
        height: int, 
        width: int,
        monitor_keyboard: bool = False,
        relevant_keys: Optional[List[int]] = None,
    ) -> None:
        """Initialize a new image viewer instance.

        Args:
            caption: The title of the window.
            height: The height of the window in pixels.
            width: The width of the window in pixels.
            monitor_keyboard: Whether to monitor keyboard events.
            relevant_keys: List of key codes to monitor. If None, all keys are monitored.

        Raises:
            RuntimeError: If initialized from a non-main thread.
        """
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('rendering from python threads is not supported')
        
        self.caption = caption
        self.height = height
        self.width = width
        self.monitor_keyboard = monitor_keyboard
        self.relevant_keys = relevant_keys
        self._window = None
        self._pressed_keys = []
        self._is_escape_pressed = False

    @property
    def is_open(self) -> bool:
        """Check if the window is currently open.

        Returns:
            bool: True if window is open, False otherwise.
        """
        return self._window is not None

    @property
    def is_escape_pressed(self) -> bool:
        """Check if the escape key is currently pressed.

        Returns:
            bool: True if escape key is pressed, False otherwise.
        """
        return self._is_escape_pressed

    @property
    def pressed_keys(self) -> Tuple[int, ...]:
        """Get currently pressed keys.

        Returns:
            Tuple[int, ...]: A sorted tuple of key codes currently being pressed.
        """
        return tuple(sorted(self._pressed_keys))

    def _handle_key_event(self, symbol: int, is_press: bool) -> None:
        """Handle keyboard press/release events.

        Args:
            symbol: The key code of the pressed/released key.
            is_press: True if key was pressed, False if released.
        """
        symbol = self.KEY_MAP.get(symbol, symbol)

        if symbol == key.ESCAPE:
            self._is_escape_pressed = is_press
            return
        
        if self.relevant_keys is not None and symbol not in self.relevant_keys:
            return
        
        if is_press:
            self._pressed_keys.append(symbol)
        else:
            self._pressed_keys.remove(symbol)

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        """Handle key press events from pyglet.

        Args:
            symbol: The key code of the pressed key.
            modifiers: Bitwise combination of any keyboard modifiers currently pressed.
        """
        self._handle_key_event(symbol, True)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        """Handle key release events from pyglet.

        Args:
            symbol: The key code of the released key.
            modifiers: Bitwise combination of any keyboard modifiers currently pressed.
        """
        self._handle_key_event(symbol, False)

    def open(self) -> None:
        """Create and open the pyglet window.

        Creates a new window with the configured caption, dimensions and vsync settings.
        If keyboard monitoring is enabled, sets up the key event handlers.
        """
        # create a window for this image viewer instance
        self._window = pyglet.window.Window(
            caption=self.caption,
            height=self.height,
            width=self.width,
            vsync=False,
            resizable=True,
        )

        # add keyboard event monitors if enabled
        if self.monitor_keyboard:
            self._window.event(self.on_key_press)
            self._window.event(self.on_key_release)

    def close(self) -> None:
        """Close the pyglet window if it's open."""
        if self.is_open:
            self._window.close()
            self._window = None

    def show(self, frame: np.ndarray) -> None:
        """Display an RGB image array in the window.

        Opens the window if it isn't already open, clears it, and displays the new frame
        scaled to fit the window dimensions.

        Args:
            frame: RGB image array of shape (height, width, 3).

        Raises:
            ValueError: If frame doesn't have exactly 3 dimensions.
        """
        if len(frame.shape) != 3:
            raise ValueError('frame should have shape with only 3 dimensions')
        
        if not self.is_open:
            self.open()
        
        self._window.clear()
        self._window.switch_to()
        self._window.dispatch_events()

        image = pyglet.image.ImageData(
            frame.shape[1],
            frame.shape[0],
            'RGB',
            frame.tobytes(),
            pitch=frame.shape[1] * -3
        )
        
        texture = image.get_texture()        
        gl.glTexParameteri(
            gl.GL_TEXTURE_2D, 
            gl.GL_TEXTURE_MAG_FILTER, 
            gl.GL_NEAREST
        )
        gl.glTexParameteri(
            gl.GL_TEXTURE_2D, 
            gl.GL_TEXTURE_MIN_FILTER, 
            gl.GL_NEAREST
        )
        
        image.blit(0, 0, width=self._window.width, height=self._window.height) 
        self._window.flip()



# explicitly define the outward facing API of this module
__all__ = [ImageViewer.__name__]
