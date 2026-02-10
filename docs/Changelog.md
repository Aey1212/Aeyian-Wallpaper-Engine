## Version:  BCP-0.0.1

- Changed from QML cursor approach to C++ approach. This is way faster than a bash-based IPC connection via background .sh commands that can't work in 60 fps.

- First working version with a blue screen and cursor coordinates at top left.

- **BUG 1** - Cursor starting position is assumed, causing the coordinates to be not accurate when starting position of the cursor is not starting at the center. Can be calibrated when dragged to top-left corner.

- **BUG 2** - CRITICAL! When trackpad is disabled by KDE, but then is used, coordinates still gets updated! Creating a misallignment!



## Version: BCP-0.0.2

- Added a /tmp log to calbrate at important situations, periodically, and manually. This catches and shrinks the drift over time.

- Calibration tool to test on bottom right.

- **BUG 1** is fixed. **BUG 2** is still there.
