//  Program:      nes-py
//  File:         common.hpp
//  Description:  This file defines common types used in the project
//
//  Copyright (c) 2019 Christian Kauten. All rights reserved.
//

#ifndef COMMON_HPP
#define COMMON_HPP

// resolve an issue with MSVC overflow during compilation (Windows)
#define _CRT_DECLARE_NONSTDC_NAMES 0
#include <cstdint>
#include <array>
#include <algorithm>

namespace NES {

/// A shortcut for a byte
typedef uint8_t NES_Byte;
/// A shortcut for a memory address (16-bit)
typedef uint16_t NES_Address;
/// A shortcut for a single pixel in memory
typedef uint32_t NES_Pixel;

template<typename T, std::size_t N>
class static_vector : public std::array<T, N> {
private:
    std::size_t current_size{0};
    std::size_t reserved_size{N};

public:
    static_vector() : std::array<T, N>() {}
    static_vector(std::initializer_list<T> list) : std::array<T, N>(list) {}

    void push_back(const T& value) {
        if (current_size >= reserved_size)
            throw std::length_error("static_vector: container is full");
        (*this)[current_size++] = value;
    }

    void reserve(std::size_t new_capacity) {
        if (new_capacity > N)
            throw std::length_error("static_vector: cannot reserve beyond max capacity");
        reserved_size = new_capacity;
        current_size = std::min(current_size, reserved_size);
    }

    void resize(std::size_t new_size) {
        if (new_size > reserved_size)
            throw std::length_error("static_vector: cannot resize beyond reserved capacity");
        current_size = new_size;
    }

    void clear() { current_size = 0; }

    // Iterator support
    typename std::array<T, N>::iterator begin() noexcept { 
        return this->std::array<T, N>::begin(); 
    }
    
    typename std::array<T, N>::iterator end() noexcept { 
        return begin() + current_size;  // Only iterate up to current_size
    }
    
    typename std::array<T, N>::const_iterator begin() const noexcept { 
        return this->std::array<T, N>::begin(); 
    }
    
    typename std::array<T, N>::const_iterator end() const noexcept { 
        return begin() + current_size;  // Only iterate up to current_size
    }
};

}  // namespace NES

#endif  // COMMON_HPP