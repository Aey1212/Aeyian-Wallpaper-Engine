import QtQuick
import org.kde.kwin as KWin

Item {
    Timer {
        interval: 100  // 10fps TODO: change after test
        running: true
        repeat: true
        onTriggered: {
            var pos = KWin.Workspace.cursorPos;
            console.log("Cursor:", pos.x, pos.y);
        }
    }

    Component.onCompleted: {
        console.log("Cursor relay started");
    }
}
