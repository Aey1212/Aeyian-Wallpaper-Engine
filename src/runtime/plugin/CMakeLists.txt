cmake_minimum_required(VERSION 3.16)
project(aeyian-wallpaper-plugin)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Quick Qml DBus)

add_library(aeyian-wallpaper-plugin MODULE
    plugin.cpp
    cursorreceiver.cpp
    filereader.h
    projectwatcher.h
)

target_link_libraries(aeyian-wallpaper-plugin
    Qt6::Core
    Qt6::Quick
    Qt6::Qml
    Qt6::DBus
)
