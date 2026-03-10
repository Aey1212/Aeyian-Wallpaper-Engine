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

    FileReader { id: fileReader }

    property string selectedProject: root.configuration.selectedProject ?? ""
    property var layersData: []

    onSelectedProjectChanged: loadProject()
    Component.onCompleted: loadProject()

    function loadProject() {
        if (!selectedProject) {
            layersData = []
            return
        }
        var raw = fileReader.readFile(selectedProject + "/layers.json")
        if (!raw) {
            layersData = []
            return
        }
        try {
            var data = JSON.parse(raw)
            var layers = data.layers || []
            layers.sort(function(a, b) {
                return (a.hierarchy || 0) - (b.hierarchy || 0)
            })
            layersData = layers
        } catch(e) {
            layersData = []
        }
    }

    // Fallback background when no project is selected
    Rectangle {
        anchors.fill: parent
        color: "#3A41E1" // hehe aeyian color go brrr!
        visible: layersData.length === 0
    }

    // Baklava
    Repeater {
        model: layersData

        Loader {
            property var layerData: modelData
            property bool isCanvas: (layerData.id === 0) || (layerData.type === "canvas")

            active: !isCanvas
            visible: !isCanvas && (layerData.visible !== false)
            z: layerData.hierarchy || 0

            sourceComponent: {
                if (layerData.type === "solid_color") return solidColorComponent
                if (layerData.type === "image") return imageComponent
                return null
            }
        }
    }

    Component {
        id: solidColorComponent

        Rectangle {
            x: (layerData.position ? layerData.position.x : 0)
            y: (layerData.position ? layerData.position.y : 0)
            width: (layerData.size ? layerData.size.width : root.width)
            height: (layerData.size ? layerData.size.height : root.height)
            color: layerData.color || "#ffffff"
        }
    }

    Component {
        id: imageComponent

        Image {
            x: (layerData.position ? layerData.position.x : 0)
            y: (layerData.position ? layerData.position.y : 0)
            width: (layerData.size ? layerData.size.width : root.width)
            height: (layerData.size ? layerData.size.height : root.height)
            source: layerData.image ? ("file://" + selectedProject + "/" + layerData.image) : ""
            fillMode: Image.Stretch
            asynchronous: true
        }
    }

    Text {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 12
        text: "X: " + cursor.mouseX.toFixed(3) + "  Y: " + cursor.mouseY.toFixed(3)
        color: "#e1e1e1" // white go brr!
        font.pixelSize: 14
        z: 9999
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
        z: 9998
    }
}
