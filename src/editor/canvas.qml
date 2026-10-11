import QtQuick
import "../runtime/qml"

Item {
    id: canvas

    property string projectPath: ""
    property var layers: []
    property var effects: []
    property real cursorX: 0.5
    property real cursorY: 0.5
    property real canvasWidth: 1920
    property real canvasHeight: 1080
    property real viewScale: 1
    property real offsetX: 0
    property real offsetY: 0
    property real frameHue: 0
    property url hexSource: ""
    property url canvasSource: ""

    Rectangle {
        anchors.fill: parent
        color: "#1e1e1e"
    }

    Item {
        id: sheet
        x: canvas.offsetX
        y: canvas.offsetY
        width: canvas.canvasWidth * canvas.viewScale
        height: canvas.canvasHeight * canvas.viewScale

        Image {
            anchors.fill: parent
            source: canvas.hexSource
            cache: false
            smooth: false
        }

        Image {
            anchors.fill: parent
            source: canvas.canvasSource
        }
    }

    Scene {
        id: scene
        objectName: "scene"
        x: canvas.offsetX
        y: canvas.offsetY
        width: canvas.canvasWidth
        height: canvas.canvasHeight
        scale: canvas.viewScale
        transformOrigin: Item.TopLeft
        projectPath: canvas.projectPath
        layers: canvas.layers
        effects: canvas.effects
        cursorX: canvas.cursorX
        cursorY: canvas.cursorY
    }

    Rectangle {
        x: sheet.x - 1
        y: sheet.y - 1
        width: sheet.width + 2
        height: sheet.height + 2
        color: "transparent"
        border.width: 2
        border.color: Qt.hsla(canvas.frameHue, 1, 0.5, 1)
    }
}
