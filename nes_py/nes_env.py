"""A CTypes interface to the C++ NES environment."""
import itertools
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import ClassVar
from typing import Optional
from dataclasses import dataclass

import gym
import numpy as np
from gym.spaces import Box
from gym.spaces import Discrete

from nes_py._rom import ROM
from nes_py.lib_emu import NESEmulator
from nes_py._image_viewer import ImageViewer



def check_rom_compatibility(rom: ROM):
    """Check that the ROM is compatible with the NES environment."""
    # check that there is PRG ROM
    if rom.prg_rom_size == 0:
        raise ValueError('ROM has no PRG-ROM banks.')

    # ensure that there is no trainer
    if rom.has_trainer:
        raise ValueError('ROM has trainer. trainer is not supported.')
        
    # try to read the PRG ROM and raise a value error if it fails
    _ = rom.prg_rom

    # try to read the CHR ROM and raise a value error if it fails
    _ = rom.chr_rom      

    # check the TV system
    if rom.is_pal:
        raise ValueError('ROM is PAL. PAL is not supported.')
    # check that the mapper is implemented
    elif rom.mapper not in {0, 1, 2, 3}:
        msg = 'ROM has an unsupported mapper number {}. please see https://github.com/Kautenja/nes-py/issues/28 for more information.'
        raise ValueError(msg.format(rom.mapper))          


@dataclass(init=False)
class NESEnv(gym.Env):
    """An NES environment based on the LaiNES emulator."""
    done: bool    
    viewer: Optional[ImageViewer]
    np_random: np.random.RandomState
    _emulator: NESEmulator
    _rom_path: str
    _has_backup: bool

    # relevant meta-data about the environment
    metadata: ClassVar[Dict[str, Any]] = {
        'render.modes': ['rgb_array', 'human'],
        'video.frames_per_second': 60
    }

    # the legal range for rewards for this environment
    reward_range: ClassVar[Tuple[float, float]] = (-float('inf'), float('inf'))

    # observation space for the environment is static across all instances
    observation_space: ClassVar[Box] = Box(
        low=0,
        high=255,
        shape=(NESEmulator.height, NESEmulator.width, 3),
        dtype=np.uint8
    )

    # action space is a bitmap of button press values for the 8 NES buttons
    action_space: ClassVar[Discrete] = Discrete(256)

    def __init__(self, rom_path: str):
        super().__init__()
        check_rom_compatibility(ROM.from_path(rom_path))

        self._rom_path = rom_path
        self._emulator = NESEmulator(self._rom_path)
        self._np_random = np.random.RandomState()
        self.viewer = None
        self.done = True
        self._has_backup = False

    @property
    def screen(self) -> np.ndarray:
        return self._emulator.screen_buffer()

    @property
    def ram(self) -> np.ndarray:
        return self._emulator.memory_buffer()    
    
    @property
    def controllers(self) -> List[np.ndarray]:
        return [self._emulator.controller(port) for port in range(2)]
    
    @property
    def backup_slots(self) -> int:
        return self._emulator.backup_slots


    def _frame_advance(self, action):
        """
        Advance a frame in the emulator with an action.

        Args:
            action (byte): the action to press on the joy-pad

        Returns:
            None

        """
        # set the action on the controller
        self.controllers[0][:] = action

        # perform a step on the emulator
        self._emulator.step()


    def _backup(self, slot_id: int = -1):
        """Backup the NES state in the emulator."""
        if slot_id < -1 or slot_id > self.backup_slots:
            raise RuntimeError(f'Only {self.backup_slots} backup slots available')

        self._emulator.backup(slot_id)
        self._has_backup = True

    def _restore(self, slot_id: int = -1):
        """Restore the backup state into the NES emulator."""
        if slot_id < -1 or slot_id > self.backup_slots:
            raise RuntimeError(f'Only {self.backup_slots} backup slots available')

        self._emulator.restore(slot_id)

    def _will_reset(self):
        """Handle any RAM hacking after a reset occurs."""
        pass

    def seed(self, seed=None):
        """
        Set the seed for this environment's random number generator.

        Returns:
            list<bigint>: Returns the list of seeds used in this env's random
              number generators. The first value in the list should be the
              "main" seed, or the value which a reproducer should pass to
              'seed'. Often, the main seed equals the provided 'seed', but
              this won't be true if seed=None, for example.

        """
        # if there is no seed, return an empty list
        if seed is None:
            return []
        # set the random number seed for the NumPy random number generator
        self.np_random.seed(seed)
        # return the list of seeds used by RNG(s) in the environment
        return [seed]

    def reset(self, seed=None, options=None, return_info=None):
        """
        Reset the state of the environment and returns an initial observation.

        Args:
            seed (int): an optional random number seed for the next episode
            options (any): unused
            return_info (any): unused

        Returns:
            state (np.ndarray): next frame as a result of the given action

        """
        # Set the seed.
        self.seed(seed)

        # call the before reset callback
        self._will_reset()

        # reset the emulator
        if self._has_backup:
            self._restore()
        else:
            self._emulator.reset()

        # call the after reset callback
        self._did_reset()

        # set the done flag to false
        self.done = False

        # return the screen from the emulator
        return self.screen

    def snapshot(self, slot_id: int):
        self._backup(slot_id)

    def restore_snapshot(self, slot_id: int):
        self._restore(slot_id)
        self._did_reset()
        self.done = False

    def _did_reset(self):
        """Handle any RAM hacking after a reset occurs."""
        pass

    def step(self, action):
        """
        Run one frame of the NES and return the relevant observation data.

        Args:
            action (byte): the bitmap determining which buttons to press

        Returns:
            a tuple of:
            - state (np.ndarray): next frame as a result of the given action
            - reward (float) : amount of reward returned after given action
            - done (boolean): whether the episode has ended
            - info (dict): contains auxiliary diagnostic information

        """
        # if the environment is done, raise an error
        if self.done:
            raise ValueError('cannot step in a done environment! call `reset`')
        
        self._frame_advance(action)

        # get the reward for this step
        reward = float(self._get_reward())

        # get the done flag for this step
        self.done = bool(self._get_done())

        # get the info for this step
        info = self._get_info()

        # call the after step callback
        self._did_step(self.done)
        # bound the reward in [min, max]
        if reward < self.reward_range[0]:
            reward = self.reward_range[0]
        elif reward > self.reward_range[1]:
            reward = self.reward_range[1]
        # return the screen from the emulator and other relevant data
        return self.screen, reward, self.done, False, info

    def _get_reward(self):
        """Return the reward after a step occurs."""
        return 0

    def _get_done(self):
        """Return True if the episode is over, False otherwise."""
        return False

    def _get_info(self):
        """Return the info after a step occurs."""
        return {}

    def _did_step(self, done):
        """
        Handle any RAM hacking after a step occurs.

        Args:
            done (bool): whether the done flag is set to true

        Returns:
            None

        """
        pass

    def close(self):
        """Close the environment."""
        # make sure the environment hasn't already been closed
        if self._emulator is None:
            raise ValueError('env has already been closed.')
        # purge the environment from C++ memory
        del self._emulator
        # deallocate the object locally
        self._emulator = None
        # if there is an image viewer open, delete it
        if self.viewer is not None:
            self.viewer.close()

    def render(self, mode='human'):
        """
        Render the environment.

        Args:
            mode (str): the mode to render with:
            - human: render to the current display
            - rgb_array: Return an numpy.ndarray with shape (x, y, 3),
              representing RGB values for an x-by-y pixel image

        Returns:
            a numpy array if mode is 'rgb_array', None otherwise

        """
        if mode == 'human':
            # if the viewer isn't setup, import it and create one
            if self.viewer is None:
                # get the caption for the ImageViewer
                if self.spec is None:
                    # if there is no spec, just use the .nes filename
                    caption = self._rom_path.split('/')[-1]
                else:
                    # set the caption to the OpenAI Gym id
                    caption = self.spec.id
                # create the ImageViewer to display frames
                self.viewer = ImageViewer(
                    caption=caption,
                    height=self._emulator.height(),
                    width=self._emulator.width(),
                )
            # show the screen on the image viewer
            self.viewer.show(self.screen)
        elif mode == 'rgb_array':
            return self.screen
        else:
            # unpack the modes as comma delineated strings ('a', 'b', ...)
            render_modes = [repr(x) for x in self.metadata['render.modes']]
            msg = 'valid render modes are: {}'.format(', '.join(render_modes))
            raise NotImplementedError(msg)

    def get_keys_to_action(self):
        """Return the dictionary of keyboard keys to actions."""
        # keyboard keys in an array ordered by their byte order in the bitmap
        # i.e. right = 7, left = 6, ..., B = 1, A = 0
        buttons = np.array([
            ord('d'),  # right
            ord('a'),  # left
            ord('s'),  # down
            ord('w'),  # up
            ord('\r'), # start
            ord(' '),  # select
            ord('p'),  # B
            ord('o'),  # A
        ])
        # the dictionary of key presses to controller codes
        keys_to_action = {}
        # the combination map of values for the controller
        values = 8 * [[0, 1]]
        # iterate over all the combinations
        for combination in itertools.product(*values):
            # unpack the tuple of bits into an integer
            byte = int(''.join(map(str, combination)), 2)
            # unwrap the pressed buttons based on the bitmap
            pressed = buttons[list(map(bool, combination))]
            # assign the pressed buttons to the output byte
            keys_to_action[tuple(sorted(pressed))] = byte

        return keys_to_action

    def get_action_meanings(self):
        """Return a list of actions meanings."""
        return ['NOOP']


# explicitly define the outward facing API of this module
__all__ = [NESEnv.__name__]
