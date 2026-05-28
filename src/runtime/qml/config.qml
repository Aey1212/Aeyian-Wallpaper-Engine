import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.aey.wallpaperengine 1.0

Item {
    id: configRoot

    property var configDialog
    property var wallpaperConfiguration: wallpaper.configuration

    FileReader { id: fileReader }

    property string wallpapersPath: fileReader.homePath() + "/.local/share/interactive-wallpapers"
    property var projectList: []

    Component.onCompleted: scanProjects()

    function scanProjects() {
        var folders = fileReader.listDirs(wallpapersPath)
        var projects = []
        for (var i = 0; i < folders.length; i++) {
            var folderPath = wallpapersPath + "/" + folders[i]
            var raw = fileReader.readFile(folderPath + "/project.json")
            if (!raw) continue
            try {
                var data = JSON.parse(raw)
                projects.push({
                    name: data.name || "Unnamed",
                    id: data.id || "",
                    path: folderPath
                })
            } catch(e) {
                continue
            }
        }
        projectList = projects
        projectGrid.model = projectList
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Wallpaper choosing thing
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#1e1e1e"

            GridView {
                id: projectGrid
                anchors.fill: parent
                anchors.margins: 12
                cellWidth: 180
                cellHeight: 160
                clip: true

                delegate: Item {
                    width: projectGrid.cellWidth
                    height: projectGrid.cellHeight

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 6
                        radius: 6
                        color: wallpaperConfiguration.selectedProject === modelData.path ? "#3A41E1" : "#2a2a2a"
                        border.color: wallpaperConfiguration.selectedProject === modelData.path ? "#5A61FF" : "#3a3a3a"
                        border.width: 1

                        Column {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 4

                            Image {
                                width: parent.width
                                height: parent.height - nameLabel.height - 4
                                source: "file://" + modelData.path + "/preview.png"
                                fillMode: Image.PreserveAspectFit
                                asynchronous: true
                            }

                            Text {
                                id: nameLabel
                                width: parent.width
                                text: modelData.name
                                color: "#e1e1e1"
                                font.pixelSize: 12
                                horizontalAlignment: Text.AlignHCenter
                                elide: Text.ElideRight
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                wallpaperConfiguration.selectedProject = modelData.path
                            }
                        }
                    }
                }
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

                Rectangle {
                    Layout.preferredWidth: 120
                    Layout.preferredHeight: 40
                    Layout.alignment: Qt.AlignHCenter
                    color: "white"
                    radius: 4

                    Text {
                        anchors.centerIn: parent
                        text: (wallpaperConfiguration.showCoordinates ?? true) ? "Hide Coords" : "Show Coords"
                        font.pixelSize: 14
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            wallpaperConfiguration.showCoordinates = !(wallpaperConfiguration.showCoordinates ?? true)
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 120
                    Layout.preferredHeight: 40
                    Layout.alignment: Qt.AlignHCenter
                    color: "white"
                    radius: 4

                    Text {
                        anchors.centerIn: parent
                        text: (wallpaperConfiguration.showCursorFollower ?? true) ? "Hide Follower" : "Show Follower"
                        font.pixelSize: 14
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            wallpaperConfiguration.showCursorFollower = !(wallpaperConfiguration.showCursorFollower ?? true)
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
}
