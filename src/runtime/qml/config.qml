import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: configRoot

    property var configDialog
    property var wallpaperConfiguration: wallpaper.configuration

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

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text {
                    text: "Sidebar"
                    color: "#e1e1e1"
                    font.pixelSize: 16
                    Layout.alignment: Qt.AlignHCenter
                }

                Item { Layout.fillHeight: true }

                Rectangle {
                    Layout.preferredWidth: 120
                    Layout.preferredHeight: 40
                    Layout.alignment: Qt.AlignHCenter
                    color: "white"
                    radius: 4

                    Text {
                        anchors.centerIn: parent
                        text: "Calibrate"
                        font.pixelSize: 14
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            var current = wallpaperConfiguration.triggerCalibrate ?? 0
                            wallpaperConfiguration.triggerCalibrate = current + 1
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
}
