import QtQuick
import org.kde.kwin as KWin

Item {
    id: pusher

    readonly property int sendInterval: 16
    readonly property int retryInterval: 2000
    property bool moved: false

    function send() {
        var pos = KWin.Workspace.cursorPos
        positionCall.arguments = [pos.x, pos.y]
        positionCall.call()
        moved = false
        sendTimer.start()
    }

    KWin.DBusCall {
        id: positionCall
        service: "org.aey.wallpaperengine"
        path: "/Cursor"
        dbusInterface: "org.aey.wallpaperengine.Cursor"
        method: "position"
        onFinished: sendTimer.interval = pusher.sendInterval
        onFailed: sendTimer.interval = pusher.retryInterval
    }

    Connections {
        target: KWin.Workspace
        function onCursorPosChanged() {
            if (sendTimer.running) {
                pusher.moved = true
            } else {
                pusher.send()
            }
        }
    }

    Timer {
        id: sendTimer
        interval: pusher.sendInterval
        onTriggered: {
            if (pusher.moved) {
                pusher.send()
            }
        }
    }

    Component.onCompleted: send()
}
