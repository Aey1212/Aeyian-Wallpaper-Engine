import QtQuick
import Qt5Compat.GraphicalEffects
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
    property var effectsData: []
    property var blurMap: []

    onSelectedProjectChanged: loadProject()
    Component.onCompleted: {
        loadBlurMap()
        loadProject()
    }

    function loadBlurMap() {
        var raw = fileReader.readFile(
            fileReader.homePath()
            + "/.config/aeyian-wallpaper-engine/blur_transliteration.json"
        )
        if (raw) {
            try {
                var data = JSON.parse(raw)
                blurMap = data.gaussian_to_fastblur || []
            } catch(e) {
                blurMap = []
            }
        }
    }

    function translateBlurRadius(gaussianRadius) {
        if (blurMap.length === 0) return gaussianRadius
        var idx = Math.floor(gaussianRadius)
        if (idx < 0) return 0
        if (idx >= blurMap.length - 1) return blurMap[blurMap.length - 1]
        var frac = gaussianRadius - idx
        return blurMap[idx] + (blurMap[idx + 1] - blurMap[idx]) * frac
    }

    function loadProject() {
        if (!selectedProject) {
            layersData = []
            effectsData = []
            return
        }

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

    // ID check for layers & effects
    function getLayerEffects(layerId) {
        var result = []
        for (var i = 0; i < effectsData.length; i++) {
            if (effectsData[i].layer_id === layerId) {
                result.push(effectsData[i])
            }
        }
        result.sort(function(a, b) {
            return (a.hierarchy || 0) - (b.hierarchy || 0)
        })
        return result
    }

    function calcOffset(mouseNorm, speed, limitPct, layerSize) {
        if (speed === 0 || limitPct === 0) return 0
        var mc = mouseNorm - 0.5
        var totalTravel = layerSize * (limitPct / 100)
        var halfTravel = totalTravel / 2
        var raw = mc * speed * totalTravel
        return Math.max(-halfTravel, Math.min(halfTravel, raw))
    }

    // Fallback so gotta keep it
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
            width: (layerData.size ? layerData.size.width : root.width)
            height: (layerData.size ? layerData.size.height : root.height)
            x: (layerData.position ? layerData.position.x : 0)
               + root.calcOffset(cursor.mouseX, layerData.speed || 0,
                                  layerData.limit ? layerData.limit.x || 0 : 0, width)
            y: (layerData.position ? layerData.position.y : 0)
               + root.calcOffset(cursor.mouseY, layerData.speed || 0,
                                  layerData.limit ? layerData.limit.y || 0 : 0, height)
            color: layerData.color || "#ffffff"
        }
    }


    Component {
        id: imageComponent

        Item {
            id: imageRoot

            property var myEffects: root.getLayerEffects(layerData.id)
            property var _effectObjects: []

            width: (layerData.size ? layerData.size.width : root.width)
            height: (layerData.size ? layerData.size.height : root.height)
            x: (layerData.position ? layerData.position.x : 0)
               + root.calcOffset(cursor.mouseX, layerData.speed || 0,
                                  layerData.limit ? layerData.limit.x || 0 : 0, width)
            y: (layerData.position ? layerData.position.y : 0)
               + root.calcOffset(cursor.mouseY, layerData.speed || 0,
                                  layerData.limit ? layerData.limit.y || 0 : 0, height)


            Image {
                id: baseImage
                anchors.fill: parent
                source: layerData.image
                    ? ("file://" + selectedProject + "/" + layerData.image) : ""
                fillMode: Image.Stretch
                asynchronous: true
                visible: imageRoot.myEffects.length === 0
                layer.enabled: imageRoot.myEffects.length > 0
            }

            onMyEffectsChanged: rebuildEffectChain()
            Component.onCompleted: rebuildEffectChain()

            function rebuildEffectChain() {
                for (var i = 0; i < _effectObjects.length; i++) {
                    _effectObjects[i].destroy()
                }
                _effectObjects = []

                if (myEffects.length === 0) return

                var prevSource = baseImage
                for (var j = 0; j < myEffects.length; j++) {
                    var fx = myEffects[j]
                    var params = fx.params || {}
                    var isLast = (j === myEffects.length - 1)
                    var obj = createEffect(fx.type, params, prevSource, isLast)
                    if (obj) {
                        _effectObjects.push(obj)
                        prevSource = obj
                    }
                }
            }

            function createEffect(effectType, params, src, isLast) {
                var qml = ""

                if (effectType === "grayscale") {
                    var strength = params.strength !== undefined ? params.strength : 1.0
                    qml = 'import QtQuick; import Qt5Compat.GraphicalEffects;'
                        + ' Desaturate {'
                        + ' anchors.fill: parent;'
                        + ' desaturation: ' + strength + ';'
                        + ' visible: ' + isLast + ';'
                        + ' }'
                }
                else if (effectType === "hue_shift") {
                    var shift = params.shift !== undefined ? params.shift : 0.0
                    qml = 'import QtQuick; import Qt5Compat.GraphicalEffects;'
                        + ' HueSaturation {'
                        + ' anchors.fill: parent;'
                        + ' hue: ' + shift + ';'
                        + ' saturation: 0.0; lightness: 0.0;'
                        + ' visible: ' + isLast + ';'
                        + ' }'
                }
                else if (effectType === "saturation") {
                    var sat = params.strength !== undefined ? (params.strength - 1.0) : 0.0
                    qml = 'import QtQuick; import Qt5Compat.GraphicalEffects;'
                        + ' HueSaturation {'
                        + ' anchors.fill: parent;'
                        + ' saturation: ' + sat + ';'
                        + ' hue: 0.0; lightness: 0.0;'
                        + ' visible: ' + isLast + ';'
                        + ' }'
                }
                else if (effectType === "brightness") {
                    var brt = params.brightness !== undefined ? params.brightness : 0.0
                    qml = 'import QtQuick; import Qt5Compat.GraphicalEffects;'
                        + ' BrightnessContrast {'
                        + ' anchors.fill: parent;'
                        + ' brightness: ' + brt + ';'
                        + ' contrast: 0.0;'
                        + ' visible: ' + isLast + ';'
                        + ' }'
                }
                else if (effectType === "tint") {
                    var tintColor = params.color || "#ffffff"
                    var tintStrength = params.strength !== undefined ? params.strength : 0.5
                    var alpha = Math.round(tintStrength * 255)
                    var alphaHex = ("0" + alpha.toString(16)).slice(-2)
                    var rgb = tintColor.replace(/^#/, "").slice(0, 6)
                    var argbColor = "#" + alphaHex + rgb
                    qml = 'import QtQuick; import Qt5Compat.GraphicalEffects;'
                        + ' ColorOverlay {'
                        + ' anchors.fill: parent;'
                        + ' color: "' + argbColor + '";'
                        + ' visible: ' + isLast + ';'
                        + ' }'
                }
                else if (effectType === "blur") {
                    var rawRadius = params.radius !== undefined ? params.radius : 5
                    var radius = root.translateBlurRadius(rawRadius)
                    qml = 'import QtQuick; import Qt5Compat.GraphicalEffects;'
                        + ' FastBlur {'
                        + ' anchors.fill: parent;'
                        + ' radius: ' + radius + ';'
                        + ' visible: ' + isLast + ';'
                        + ' }'
                }
                else {
                    // Unknown type means skip - don't talk to strangers
                    return null
                }

                try {
                    var obj = Qt.createQmlObject(qml, imageRoot, "effect_" + effectType)
                    obj.source = src
                    return obj
                } catch(e) {
                    console.warn("AWE: Failed to create effect:", effectType, e)
                    return null
                }
            }
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
