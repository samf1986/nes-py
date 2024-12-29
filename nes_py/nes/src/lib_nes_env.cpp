//  Program:      nes-py
//  File:         lib_nes_env.cpp
//  Description:  file describes the outward facing ctypes API for Python
//
//  CHANGELOG:    - 2024-12-28: Changed from ctypes to pybind11 - Ali Mosavian
//
//  Copyright (c) 2019 Christian Kauten. All rights reserved.
//
#include "common.hpp"
#include "emulator.hpp"

#include <string>

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

namespace py = pybind11;

PYBIND11_MODULE(emulator, m) {   
    py::class_<NES::Emulator>(m, "NESEmulator")
        .def(py::init<const std::string&>())

        .def_property_readonly_static("width", [](py::object) { return NES::Emulator::WIDTH; })
        .def_property_readonly_static("height", [](py::object) { return NES::Emulator::HEIGHT; })
        .def_property_readonly_static("backup_slots", [](py::object) { return NES::Emulator::NUM_BACKUP_SLOTS; })

        .def("reset", &NES::Emulator::reset, "Reset the emulator")
        .def("step", &NES::Emulator::step, "Perform a step on the emulator")
        .def("backup", &NES::Emulator::backup, py::arg("slot"), "Backup the emulator state to the given slot")
        .def("restore", &NES::Emulator::restore, py::arg("slot"), "Restore the emulator state from the given slot")
        
        .def(
            "screen_buffer", 
            [](NES::Emulator& emu) -> py::array_t<uint8_t> {
                const int HEIGHT = NES::Emulator::HEIGHT;
                const int WIDTH = NES::Emulator::WIDTH;
                
                #if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
                    // On little-endian systems: BGRx -> RGB
                    return py::array_t<uint8_t>(
                        {HEIGHT, WIDTH, 3},                    // shape (3 channels)
                        {WIDTH * 4, 4, -1},                   // negative stride to reverse BGR->RGB
                        reinterpret_cast<uint8_t*>(emu.get_screen_buffer()) + 2,  // start at B
                        py::capsule(emu.get_screen_buffer(), [](void*) {})  // capsule with data pointer
                    );
                #else
                    // On big-endian systems: xRGB -> RGB
                    return py::array_t<uint8_t>(
                        {HEIGHT, WIDTH, 3},                    // shape (3 channels)
                        {WIDTH * 4, 4, 1},                    // normal stride
                        reinterpret_cast<uint8_t*>(emu.get_screen_buffer()) + 1,  // skip x
                        py::capsule(emu.get_screen_buffer(), [](void*) {})  // capsule with data pointer
                    );
                #endif
            }, 
            "Get the screen buffer as a HEIGHT x WIDTH x 3 numpy.ndarray in RGB format"
        )

        .def(
            "controller",
            [](NES::Emulator& emu, int port) -> py::array_t<uint8_t> {
                // Create a view of the controller buffer
                return py::array_t<uint8_t>(
                    {1},                                    // shape (1 controller)
                    {1},                                    // stride (1 byte per controller)
                    reinterpret_cast<uint8_t*>(emu.get_controller(port)),  // pointer to data
                    py::capsule(emu.get_controller(port), [](void*) {})    // capsule with data pointer
                );
            },
            py::arg("port"),
            "Get the controller buffer as numpy.ndarray"
        )

        .def(
            "memory_buffer", 
            [](NES::Emulator& emu) -> py::array_t<uint8_t> {
                // Create a view of the RAM buffer (0x800 bytes)
                return py::array_t<uint8_t>(
                    {0x800},                               // shape (2048 bytes)
                    {1},                                   // stride (1 byte)
                    reinterpret_cast<uint8_t*>(emu.get_memory_buffer()),  // pointer to data
                    py::capsule(emu.get_memory_buffer(), [](void*) {})    // capsule with data pointer
                );
            }, 
            "Get the memory buffer as numpy.ndarray"
        )
    ;
};
