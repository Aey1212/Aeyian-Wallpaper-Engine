import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: configRoot

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Wallpapers here
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#1e1e1e" // Reverse white

            Text {
                anchors.centerIn: parent
                text: "Content Area"
                color: "#e1e1e1"
                font.pixelSize: 16
            }
        }

        // The config thing Engine will have
        Rectangle {
            Layout.preferredWidth: 250
            Layout.fillHeight: true
            color: "#3A41E1" // I love this blue

            Text {
                anchors.centerIn: parent
                text: "Sidebar"
                color: "#e1e1e1"
                font.pixelSize: 16
            }
        }
    }
}
