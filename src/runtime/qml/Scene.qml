import QtQuick
import Qt5Compat.GraphicalEffects

Item {
    id: scene

    property string projectPath: ""
    property var layers: []
    property var effects: []
    property real cursorX: 0.5
    property real cursorY: 0.5
    readonly property real blurSigmaPerRadius: 0.46

    // ID check for layers & effects
    function getLayerEffects(layerId) {
        var result = []
        for (var i = 0; i < scene.effects.length; i++) {
            if (scene.effects[i].layer_id === layerId) {
                result.push(scene.effects[i])
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

    // Baklava
    Repeater {
        model: scene.layers

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
            width: (layerData.size ? layerData.size.width : scene.width)
            height: (layerData.size ? layerData.size.height : scene.height)
            x: (layerData.position ? layerData.position.x : 0)
               + scene.calcOffset(scene.cursorX, layerData.speed || 0,
                                  layerData.limit ? layerData.limit.x || 0 : 0, width)
            y: (layerData.position ? layerData.position.y : 0)
               + scene.calcOffset(scene.cursorY, layerData.speed || 0,
                                  layerData.limit ? layerData.limit.y || 0 : 0, height)
            color: layerData.color || "#ffffff"
        }
    }


    Component {
        id: imageComponent

        Item {
            id: imageRoot

            property var myEffects: scene.getLayerEffects(layerData.id)
            property var _effectObjects: []

            width: (layerData.size ? layerData.size.width : scene.width)
            height: (layerData.size ? layerData.size.height : scene.height)
            x: (layerData.position ? layerData.position.x : 0)
               + scene.calcOffset(scene.cursorX, layerData.speed || 0,
                                  layerData.limit ? layerData.limit.x || 0 : 0, width)
            y: (layerData.position ? layerData.position.y : 0)
               + scene.calcOffset(scene.cursorY, layerData.speed || 0,
                                  layerData.limit ? layerData.limit.y || 0 : 0, height)


            Image {
                id: baseImage
                anchors.fill: parent
                source: layerData.image
                    ? ("file://" + scene.projectPath + "/" + layerData.image
                       + (layerData.image_stamp ? "#" + layerData.image_stamp : "")) : ""
                fillMode: Image.Stretch
                asynchronous: true
                visible: imageRoot.myEffects.length === 0
                layer.enabled: imageRoot.myEffects.length > 0
            }

            onMyEffectsChanged: rebuildEffectChain()
            Component.onCompleted: rebuildEffectChain()

            Component { id: grayscaleComponent
                Desaturate { anchors.fill: parent } }
            Component { id: hueShiftComponent
                HueSaturation { anchors.fill: parent; saturation: 0.0; lightness: 0.0 } }
            Component { id: saturationComponent
                HueSaturation { anchors.fill: parent; hue: 0.0; lightness: 0.0 } }
            Component { id: brightnessComponent
                BrightnessContrast { anchors.fill: parent; contrast: 0.0 } }
            Component { id: tintComponent
                ColorOverlay { anchors.fill: parent } }
            Component { id: blurComponent
                GaussianBlur { anchors.fill: parent; cached: true } }

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
                var comp = null
                var props = { source: src, visible: isLast }

                if (effectType === "grayscale") {
                    comp = grayscaleComponent
                    props.desaturation = params.strength !== undefined ? params.strength : 1.0
                }
                else if (effectType === "hue_shift") {
                    comp = hueShiftComponent
                    props.hue = params.shift !== undefined ? params.shift : 0.0
                }
                else if (effectType === "saturation") {
                    comp = saturationComponent
                    props.saturation = params.strength !== undefined ? (params.strength - 1.0) : 0.0
                }
                else if (effectType === "brightness") {
                    comp = brightnessComponent
                    props.brightness = params.brightness !== undefined ? params.brightness : 0.0
                }
                else if (effectType === "tint") {
                    comp = tintComponent
                    var tintColor = String(params.color || "#ffffff")
                    var tintStrength = params.strength !== undefined ? params.strength : 0.5
                    var alpha = Math.round(tintStrength * 255)
                    var alphaHex = ("0" + alpha.toString(16)).slice(-2)
                    var rgb = tintColor.replace(/^#/, "").slice(0, 6)
                    props.color = "#" + alphaHex + rgb
                }
                else if (effectType === "blur") {
                    comp = blurComponent
                    var sigma = (params.radius !== undefined ? params.radius : 5) * scene.blurSigmaPerRadius
                    props.deviation = sigma
                    props.radius = Math.ceil(sigma * 3)
                    props.samples = 1 + props.radius * 2
                }
                else {
                    // Unknown type means skip - don't talk to strangers
                    return null
                }

                try {
                    var obj = comp.createObject(imageRoot, props)
                    return obj
                } catch(e) {
                    console.warn("AWE: Failed to create effect:", effectType, e)
                    return null
                }
            }
        }
    }
}
