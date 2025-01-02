"""A CTypes interface to the C++ NES environment."""
import itertools
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import Union
from typing import ClassVar
from typing import Optional
from typing import NamedTuple
from typing import SupportsFloat
from dataclasses import dataclass

import numpy as np
import gymnasium as gym
import lz4.block as lz4
from gymnasium.spaces import Box
from gymnasium.spaces import Discrete

from nes_py._rom import ROM
from nes_py.emulator import NESEmulator
from nes_py._image_viewer import ImageViewer



class NESGameCallbacks:
    def _will_reset(self):
        """Handle any RAM hacking after a reset occurs."""
        pass

    def _did_reset(self):
        """Handle any RAM hacking after a reset occurs."""
        pass

    def _will_restore(self):
        """Handle any RAM hacking after a restore occurs."""
        pass

    def _did_restore(self):
        """Handle any RAM hacking after a restore occurs."""
        pass

    def _will_step(self):
        """Handle any RAM hacking after a step occurs."""
        pass    

    def _did_step(self, done: bool):
        """Handle any RAM hacking after a step occurs."""
        pass

    def _get_reward(self) -> float:
        """Return the reward after a step occurs."""
        return 0

    def _get_done(self) -> bool:
        """Return True if the episode is over, False otherwise."""
        return False

    def _get_info(self) -> Dict[str, Any]:
        """Return the info after a step occurs."""
        return {}
    
@dataclass(init=False)
class NESEmulatorWrapper(NESGameCallbacks):    
    _rom_path: str
    _emulator: NESEmulator    

    height: int = NESEmulator.height
    width: int = NESEmulator.width

    def __init__(self, rom_path: str):    
        NESEmulatorWrapper.check_rom_compatibility(ROM.from_path(rom_path))
        
        self._rom_path = rom_path
        self._emulator = NESEmulator(rom_path)
        
    @staticmethod
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
        

    @property
    def _screen_buffer(self) -> np.ndarray:
        return self._emulator.screen_buffer()

    @property
    def _memory_buffer(self) -> np.ndarray:
        return self._emulator.memory_buffer()
    
    @property
    def _controller_buffers(self) -> List[np.ndarray]:
        return [self._emulator.controller(port) for port in range(2)]
    
    @property
    def ram(self) -> np.ndarray:
        return self._memory_buffer
    
    @property
    def screen(self) -> bytes:
        return self._screen_buffer
       
    def dump_state(self) -> np.ndarray:
        return self._emulator.dump_state()

    def load_state(self, snapshot: np.ndarray):
        self._will_restore()
        self._emulator.load_state(snapshot)
        self._did_restore()

    def frame_advance(self, action: Union[int, Tuple[int, int]]) -> None:
        """
        Advance a frame in the emulator with an action.

        Args:
            action (byte): the action to press on the joy-pad

        Returns:
            None

        """
        # set the action on the controller
        if isinstance(action, (int, np.integer)):
            self._controller_buffers[0][:] = action
        elif isinstance(action, tuple) and len(action) == 2:
            self._controller_buffers[0][:] = action[0]
            self._controller_buffers[1][:] = action[1]
        else:
            raise ValueError(f'Invalid action type or length: {type(action)}')

        # perform a step on the emulator
        self._emulator.step()        





class StepResult(NamedTuple):
    observation: np.ndarray
    reward: float
    terminated: bool
    truncated: bool
    info: Dict[str, Any]


@dataclass(init=False)
class NESEnv(NESEmulatorWrapper, gym.Env[np.ndarray, int]):
    """An NES environment based on the LaiNES emulator."""
    _done: bool    
    _viewer: Optional[ImageViewer]
    _np_random: np.random.RandomState
    _snapshot: Optional[np.ndarray]

    # relevant meta-data about the environment
    metadata: ClassVar[Dict[str, Any]] = {
        'render.modes': ['rgb_array', 'human'],
        'render_fps': 60
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
        super().__init__(rom_path)

        self._viewer = None
        self._done = True
        self._snapshot = None


    def reset(
        self,
        *,
        seed: Union[int, None] = None,
        options: Union[Dict[str, Any], None] = None,            
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Reset the state of the environment and returns an initial observation.

        Args:
            seed (int): an optional random number seed for the next episode
            options (any): unused

        Returns:
            state (np.ndarray): next frame as a result of the given action

        """
        # Set the seed.
        super().reset(seed=seed)

        # call the before reset callback
        self._will_reset()

        # reset the emulator
        if self._snapshot is not None:
            self._restore()
        else:
            self._emulator.reset()

        # call the after reset callback
        self._did_reset()

        # set the done flag to false
        self._done = False

        # return the _screen_buffer from the emulator
        return self._screen_buffer, self._get_info()


    def step(self, action: int) -> Tuple[np.ndarray, SupportsFloat, bool, bool, Dict[str, Any]]:
        """
        Run one frame of the NES and return the relevant observation data.

        Args:
            action (byte): the bitmap determining which buttons to press

        Returns:
            a tuple of:
            - state (np.ndarray): next frame as a result of the given action
            - reward (float) : amount of reward returned after given action
            - done (boolean): whether the episode has ended
            - truncated (boolean): whether the episode has been truncated
            - info (dict): contains auxiliary diagnostic information

        """
        # if the environment is done, raise an error
        if self._done:
            raise ValueError('cannot step in a done environment! call `reset`')
        
        self.frame_advance(action)

        # get the reward for this step
        reward = float(self._get_reward())
        reward = min(max(reward, self.reward_range[0]), self.reward_range[1])

        # get the done flag for this step
        self._done = bool(self._get_done())

        # get the info for this step
        info = self._get_info()

        # call the after step callback
        self._did_step(self._done)

        # return the _screen_buffer from the emulator and other relevant data
        return StepResult(
            observation=self._screen_buffer,
            reward=reward,
            terminated=self._done,
            truncated=False,
            info=info
        )


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
        if self._viewer is not None:
            self._viewer.close()

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
            if self._viewer is None:
                # get the caption for the ImageViewer
                if self.spec is None:
                    # if there is no spec, just use the .nes filename
                    caption = self._rom_path.split('/')[-1]
                else:
                    # set the caption to the OpenAI Gym id
                    caption = self.spec.id
                # create the ImageViewer to display frames
                self._viewer = ImageViewer(
                    caption=caption,
                    height=self._emulator.height,
                    width=self._emulator.width,
                )
            # show the _screen_buffer on the image viewer
            self._viewer.show(self._screen_buffer)
        elif mode == 'rgb_array':
            return self._screen_buffer
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
    
    def _backup(self):
        self._snapshot = self.dump_state()

    def _restore(self):
        if self._snapshot is None:
            raise ValueError('no snapshot to restore')
        
        self.load_state(self._snapshot)


# explicitly define the outward facing API of this module
__all__ = [NESEnv.__name__]
