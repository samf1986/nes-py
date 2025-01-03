//  Program:      nes-py
//  File:         emulator.cpp
//  Description:  This class houses the logic and data for an NES emulator
//
//  Copyright (c) 2019 Christian Kauten. All rights reserved.
//

#include "emulator.hpp"
#include "mapper_factory.hpp"
#include "log.hpp"

#include <cstring>

namespace NES {

void Core::initialize(Controller* const controllers) 
{
    // set the read callbacks
    bus.set_read_callback(PPUSTATUS, [&](void) { return ppu.get_status();          });
    bus.set_read_callback(PPUDATA,   [&](void) { return ppu.get_data(picture_bus); });
    bus.set_read_callback(JOY1,      [&](void) { return controllers[0].read();     });
    bus.set_read_callback(JOY2,      [&](void) { return controllers[1].read();     });
    bus.set_read_callback(OAMDATA,   [&](void) { return ppu.get_OAM_data();        });

    // set the write callbacks
    bus.set_write_callback(PPUCTRL,  [&](NES_Byte b) { ppu.control(b);                                             });
    bus.set_write_callback(PPUMASK,  [&](NES_Byte b) { ppu.set_mask(b);                                            });
    bus.set_write_callback(OAMADDR,  [&](NES_Byte b) { ppu.set_OAM_address(b);                                     });
    bus.set_write_callback(PPUADDR,  [&](NES_Byte b) { ppu.set_data_address(b);                                    });
    bus.set_write_callback(PPUSCROL, [&](NES_Byte b) { ppu.set_scroll(b);                                          });
    bus.set_write_callback(PPUDATA,  [&](NES_Byte b) { ppu.set_data(picture_bus, b);                               });
    bus.set_write_callback(OAMDMA,   [&](NES_Byte b) { cpu.skip_DMA_cycles(); ppu.do_DMA(bus.get_page_pointer(b)); });
    bus.set_write_callback(JOY1,     [&](NES_Byte b) { controllers[0].strobe(b); controllers[1].strobe(b);         });
    bus.set_write_callback(OAMDATA,  [&](NES_Byte b) { ppu.set_OAM_data(b);                                        });

    // set the interrupt callback for the PPU
    ppu.set_interrupt_callback([&]() { cpu.interrupt(bus, CPU::NMI_INTERRUPT); });
}

void Core::reset() {
    cpu.reset(bus);
    ppu.reset();
}

void Core::set_mapper(Mapper *mapper) {
    bus.set_mapper(mapper);
    picture_bus.set_mapper(mapper);
}

void Core::ppu_step(NESFrameBufferT* const framebuffer) {
    // 3 PPU steps per CPU step
    ppu.cycle(picture_bus, framebuffer);
    ppu.cycle(picture_bus, framebuffer);
    ppu.cycle(picture_bus, framebuffer);
}

void Core::step(NESFrameBufferT* const framebuffer) {
    // 3 PPU steps per CPU step
    ppu_step(framebuffer);
    cpu.cycle(bus);
}

Emulator::Emulator(std::string rom_path) 
{
    // set the read callbacks
    core.bus.set_read_callback(PPUSTATUS, [&](void) { return core.ppu.get_status();          });
    core.bus.set_read_callback(PPUDATA,   [&](void) { return core.ppu.get_data(core.picture_bus); });
    core.bus.set_read_callback(JOY1,      [&](void) { return controllers[0].read();     });
    core.bus.set_read_callback(JOY2,      [&](void) { return controllers[1].read();     });
    core.bus.set_read_callback(OAMDATA,   [&](void) { return core.ppu.get_OAM_data();        });

    // set the write callbacks
    core.bus.set_write_callback(PPUCTRL,  [&](NES_Byte b) { core.ppu.control(b);                                             });
    core.bus.set_write_callback(PPUMASK,  [&](NES_Byte b) { core.ppu.set_mask(b);                                            });
    core.bus.set_write_callback(OAMADDR,  [&](NES_Byte b) { core.ppu.set_OAM_address(b);                                     });
    core.bus.set_write_callback(PPUADDR,  [&](NES_Byte b) { core.ppu.set_data_address(b);                                    });
    core.bus.set_write_callback(PPUSCROL, [&](NES_Byte b) { core.ppu.set_scroll(b);                                          });
    core.bus.set_write_callback(PPUDATA,  [&](NES_Byte b) { core.ppu.set_data(core.picture_bus, b);                               });
    core.bus.set_write_callback(OAMDMA,   [&](NES_Byte b) { core.cpu.skip_DMA_cycles(); core.ppu.do_DMA(core.bus.get_page_pointer(b)); });
    core.bus.set_write_callback(JOY1,     [&](NES_Byte b) { controllers[0].strobe(b); controllers[1].strobe(b);         });
    core.bus.set_write_callback(OAMDATA,  [&](NES_Byte b) { core.ppu.set_OAM_data(b);                                        });

    // set the interrupt callback for the PPU
    core.ppu.set_interrupt_callback([&]() { core.cpu.interrupt(core.bus, CPU::NMI_INTERRUPT); });

    // initialize the framebuffer to all black
    std::memset(&framebuffer, 0, sizeof(framebuffer));

    // load the ROM from disk, expect that the Python code has validated it
    cartridge.loadFromFile(rom_path);

    // create the mapper based on the mapper ID in the iNES header of the ROM
    auto mapper = MapperFactory(&cartridge, [&](){ core.picture_bus.update_mirroring(); });

    // give the IO buses a pointer to the mapper
    core.set_mapper(mapper);
}


void Emulator::step() {
    // render a single frame on the emulator
    for (int i = 0; i < CYCLES_PER_FRAME; i++) {
        core.step(&framebuffer);
    }
}

void Emulator::ppu_step() {
    // render a single frame on the emulator
    for (int i = 0; i < CYCLES_PER_FRAME; i++) {
        core.ppu_step(&framebuffer);
    }
}

}  // namespace NES
