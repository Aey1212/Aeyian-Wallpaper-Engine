import QtQuick
import org.kde.plasma.plasmoid

WallpaperItem {
    id: root

    property real mouseXcord: 0.0
    property real mouseYcord: 0.0

    Rectangle {
        anchors.fill: parent
        color: "#3A41E1" // hehe aeyian color go brrr!
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        propagateComposedEvents: true // IDK what this is - seen on reddit
        acceptedButtons: Qt.LeftButton
        onPositionChanged: function(mouse) {
            root.mouseXcord = mouse.x / width
            root.mouseYcord = mouse.y / height
        }

        // get data from cursor.qml

    }

    Text {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 12
        text: "X: " + root.mouseXcord.toFixed(3) + "  Y: " + root.mouseYcord.toFixed(3)
        color: "#e1e1e1" // white go brr!
        font.pixelSize: 14
    }
}
