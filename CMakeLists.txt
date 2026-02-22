# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 - Aey

cmake_minimum_required(VERSION 3.20)

project(AeyianWallpaperEngine
    VERSION 0.0.3
    DESCRIPTION "Interactive wallpaper engine for KDE Plasma"
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Quick Qml)

message(STATUS "Aeyian Wallpaper Engine v${PROJECT_VERSION}")
