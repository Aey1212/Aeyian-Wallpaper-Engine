import QtQuick
import org.kde.plasma.plasmoid
import "aeyian" // My beloved wayland mouse cursor plugin!

WallpaperItem {
    id: root

    CursorReceiver {
        id: cursor
        script: Qt.resolvedUrl("../kwin/v1/aeyian_cursor_v1.qml")
        onPositionChanged: root.holdScreenFraction()
    }

    FileReader { id: fileReader }

    ProjectWatcher {
        path: root.selectedProject
        onChanged: root.loadProject()
    }

    property string selectedProject: root.configuration.selectedProject ?? ""
    property var layersData: []
    property var effectsData: []
    property var projectResolution: null
    property string cursorRange: "desktop"
    property point heldFraction: Qt.point(0.5, 0.5)
    property point cursorFraction: cursorRange === "screen"
        ? heldFraction : desktopFraction(cursor.x, cursor.y, Qt.application.screens)
    property real cursorX: cursorFraction.x
    property real cursorY: cursorFraction.y

    onSelectedProjectChanged: loadProject()
    Component.onCompleted: loadProject()

    function holdScreenFraction() {
        var x = (cursor.x - Screen.virtualX) / root.width
        var y = (cursor.y - Screen.virtualY) / root.height
        if (cursor.tracking && x >= 0 && x < 1 && y >= 0 && y < 1) {
            heldFraction = Qt.point(x, y)
        }
    }

    function desktopFraction(x, y, screens) {
        var left = Infinity
        var top = Infinity
        var right = -Infinity
        var bottom = -Infinity
        for (var i = 0; i < screens.length; i++) {
            left = Math.min(left, screens[i].virtualX)
            top = Math.min(top, screens[i].virtualY)
            right = Math.max(right, screens[i].virtualX + screens[i].width)
            bottom = Math.max(bottom, screens[i].virtualY + screens[i].height)
        }
        if (!cursor.tracking || right <= left || bottom <= top) {
            return Qt.point(0.5, 0.5)
        }
        return Qt.point(Math.max(0, Math.min(1, (x - left) / (right - left))),
                        Math.max(0, Math.min(1, (y - top) / (bottom - top))))
    }

    function loadProject() {
        if (!selectedProject) {
            layersData = []
            effectsData = []
            projectResolution = null
            cursorRange = "desktop"
            return
        }

        var resolution = null
        var range = "desktop"
        var rawProject = fileReader.readFile(selectedProject + "/project.json")
        if (rawProject) {
            try {
                var manifest = JSON.parse(rawProject)
                var res = manifest.resolution
                if (res && res.width > 0 && res.height > 0) {
                    resolution = res
                }
                if (manifest.cursor_range === "screen") {
                    range = "screen"
                }
            } catch(e) {
                resolution = null
            }
        }
        projectResolution = resolution
        cursorRange = range

        // Load layers
        var rawLayers = fileReader.readFile(selectedProject + "/layers.json")
        if (!rawLayers) {
            layersData = []
        } else {
            try {
                var ld = JSON.parse(rawLayers)
                var layers = ld.layers || []
                layers.sort(function(a, b) {
                    return (a.hierarchy || 0) - (b.hierarchy || 0)
                })
                for (var i = 0; i < layers.length; i++) {
                    if (layers[i].image) {
                        layers[i].image_stamp = fileReader.modified(selectedProject + "/" + layers[i].image)
                    }
                }
                layersData = layers
            } catch(e) {
                layersData = []
            }
        }

        // Load effects
        var rawEffects = fileReader.readFile(selectedProject + "/effects.json")
        if (!rawEffects) {
            effectsData = []
        } else {
            try {
                var ed = JSON.parse(rawEffects)
                effectsData = ed.effects || []
            } catch(e) {
                effectsData = []
            }
        }
    }

    // Fallback so gotta keep it
    Rectangle {
        anchors.fill: parent
        color: "#3A41E1" // hehe aeyian color go brrr!
        visible: layersData.length === 0
    }

    Scene {
        width: root.projectResolution ? root.projectResolution.width : root.width
        height: root.projectResolution ? root.projectResolution.height : root.height
        x: (root.width - width) / 2
        y: (root.height - height) / 2
        scale: width > 0 && height > 0 ? Math.max(root.width / width, root.height / height) : 1
        projectPath: root.selectedProject
        layers: root.layersData
        effects: root.effectsData
        cursorX: root.cursorX
        cursorY: root.cursorY
    }

    Text {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 12
        text: "X: " + root.cursorX.toFixed(3) + "  Y: " + root.cursorY.toFixed(3)
        color: "#e1e1e1" // white go brr!
        font.pixelSize: 14
        z: 9999
        visible: root.configuration.showCoordinates ?? true
    }

    Rectangle {
        id: cursorfollow
        width: 40
        height: 40
        radius: 20
        color: "#e13b3e" // red dot, sniper confirmed!
        x: cursor.x - Screen.virtualX - 20
        y: cursor.y - Screen.virtualY - 20
        z: 9998
        visible: cursor.tracking && (root.configuration.showCursorFollower ?? true)
    }
}
