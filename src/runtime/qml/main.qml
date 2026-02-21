import QtQuick
import org.kde.plasma.plasmoid
import org.aey.wallpaperengine 1.0 // My beloved wayland mouse cursor plugin!

WallpaperItem {
    id: root

    CursorProvider {
        id: cursor
        screenWidth: root.width
        screenHeight: root.height
    }

    Rectangle {
        anchors.fill: parent
        color: "#3A41E1" // hehe aeyian color go brrr!
    }

    Text {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 12
        text: "X: " + cursor.mouseX.toFixed(3) + "  Y: " + cursor.mouseY.toFixed(3)
        color: "#e1e1e1" // white go brr!
        font.pixelSize: 14
    }

    // Calibrate button is instant thanks to this
    property int triggerCalibrate: root.configuration.triggerCalibrate ?? 0
    onTriggerCalibrateChanged: {
        if (triggerCalibrate > 0) {
            cursor.calibrate()
        }
    }

    Rectangle {
        id: cursorfollow
        width: 40
        height: 40
        radius: 20
        color: "#e13b3e" // red dot, sniper confirmed!
        x: cursor.mouseX * parent.width - 20
        y: cursor.mouseY * parent.height - 20
    }
}
