cmake_minimum_required(VERSION 3.16)
project(aeyian-wallpaper-plugin)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Quick Qml)
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBINPUT REQUIRED libinput libudev)

add_library(aeyian-wallpaper-plugin MODULE
    plugin.cpp
    cursorprovider.cpp
)

target_link_libraries(aeyian-wallpaper-plugin
    Qt6::Core
    Qt6::Quick
    Qt6::Qml
    ${LIBINPUT_LIBRARIES}
)

target_include_directories(aeyian-wallpaper-plugin PRIVATE ${LIBINPUT_INCLUDE_DIRS})
