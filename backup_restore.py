import time
from PIL import Image
from IPython.display import display
from nes_py._rom import ROM
from nes_py.nes_env import NESEnv
from nes_py.lib_emu import NESEmulator

import numpy as np
rom = ROM.from_path('./nes_py/tests/games/super-mario-bros-1.nes')

rom.chr_rom

emu = NESEmulator('./nes_py/tests/games/super-mario-bros-1.nes')
emu.reset()
screen = emu.screen_buffer()

start_time = time.perf_counter()
for i in range(60*10):
    emu.step()
end_time = time.perf_counter()
fps = 60*10/(end_time-start_time)
fps/60

from nes_py import NESEnv
import tqdm
env = NESEnv.from_rom('./nes_py/tests/games/super-mario-bros-1.nes')
#env.reset()

done = False
try:
    for i in tqdm.tqdm(range(5000)):
        if done:
            state = env.reset()
            done = False
        else:
            state, reward, done, _, info = env.step(env.action_space.sample())
        if (i + 1) % 12:
            env._backup()
        if (i + 1) % 27:
            env._restore()
except KeyboardInterrupt:
    pass

env.action_space.sample()

env.get_keys_to_action()


