#include "cursorprovider.h"
#include <QDebug>
#include <QProcess>
#include <QFile>
#include <QThread>
#include <QRegularExpression>
#include <fcntl.h>
#include <unistd.h>
#include <libudev.h>
#include <QElapsedTimer>

int CursorProvider::openRestricted(const char *path, int flags, void *)
{
    int fd = open(path, flags);
    return fd < 0 ? -errno : fd;
}

void CursorProvider::closeRestricted(int fd, void *)
{
    close(fd);
}

static const libinput_interface iface = {
    CursorProvider::openRestricted,
    CursorProvider::closeRestricted,
};

CursorProvider::CursorProvider(QObject *parent)
: QObject(parent)
{
    m_udev = udev_new();
    if (!m_udev) {
        qWarning() << "Failed to create udev context";
        return;
    }

    m_li = libinput_udev_create_context(&iface, nullptr, m_udev);
    if (!m_li) {
        qWarning() << "Failed to create libinput context";
        return;
    }

    if (libinput_udev_assign_seat(m_li, "seat0") < 0) {
        qWarning() << "Failed to assign seat (is user in 'input' group?)";
        return;
    }

    int fd = libinput_get_fd(m_li);
    m_notifier = new QSocketNotifier(fd, QSocketNotifier::Read, this);
    connect(m_notifier, &QSocketNotifier::activated, this, &CursorProvider::handleEvents);

    handleEvents();

    calibrate();

    m_lastCalibration.start();
    m_lastMovement.start();

    setupCalibrationTimer();
}

CursorProvider::~CursorProvider()
{
    if (m_li) libinput_unref(m_li);
    if (m_udev) udev_unref(m_udev);
}

void CursorProvider::setupCalibrationTimer()
{
    m_calibrationTimer = new QTimer(this);
    connect(m_calibrationTimer, &QTimer::timeout, this, &CursorProvider::calibrate);
    m_calibrationTimer->start(3600000); // 1 hour in milliseconds
}

void CursorProvider::calibrate()
{
    // Cooldown: minimum 5 seconds between calibrations - 2 was too fucking small to not decaliber by mistake
    if (m_lastCalibration.isValid() && m_lastCalibration.elapsed() < 5000) {
        qDebug() << "Calibration cooldown, skipping";
        return;
    }

    // Don't calibrate if mouse moved in last 200ms
    if (m_lastMovement.isValid() && m_lastMovement.elapsed() < 200) {
        qDebug() << "Mouse moving, skipping calibration";
        return;
    }

    m_lastCalibration.restart();

    QString scriptPath = "/tmp/aeyian-cursor-calibrate.qml";
    QFile scriptFile(scriptPath);
    if (scriptFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        scriptFile.write(
            "import QtQuick\n"
            "import org.kde.kwin as KWin\n"
            "Item {\n"
            "    Component.onCompleted: {\n"
            "        var pos = KWin.Workspace.cursorPos;\n"
            "        console.log(\"AEYIAN_CURSOR:\" + pos.x + \",\" + pos.y);\n"
            "    }\n"
            "}\n"
        );
        scriptFile.close();
    } else {
        qWarning() << "Failed to create calibration script";
        return;
    }

    QProcess loadProc;
    loadProc.start("qdbus", {"org.kde.KWin", "/Scripting",
        "org.kde.kwin.Scripting.loadDeclarativeScript", scriptPath, "aeyian-calibrate"});
    loadProc.waitForFinished(1000);

    QProcess startProc;
    startProc.start("qdbus", {"org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.start"});
    startProc.waitForFinished(1000);
    QThread::msleep(50);
    QProcess journalProc;
    journalProc.start("journalctl", {"-t", "kwin_wayland", "-o", "cat", "--since", "5 seconds ago"});
    journalProc.waitForFinished(1000);
    QString output = journalProc.readAllStandardOutput();

    QProcess unloadProc;
    unloadProc.start("qdbus", {"org.kde.KWin", "/Scripting",
        "org.kde.kwin.Scripting.unloadScript", "aeyian-calibrate"});
    unloadProc.waitForFinished(1000);

    QRegularExpression re("AEYIAN_CURSOR:(\\d+),(\\d+)");
    QRegularExpressionMatch match = re.match(output);
    if (match.hasMatch()) {
        m_rawX = match.captured(1).toDouble();
        m_rawY = match.captured(2).toDouble();
        m_mouseX = m_rawX / m_screenWidth;
        m_mouseY = m_rawY / m_screenHeight;
        emit positionChanged();
        qDebug() << "Calibrated cursor position:" << m_rawX << m_rawY;
    } else {
        qWarning() << "Failed to parse cursor position from journal";
    }
}

void CursorProvider::handleEvents()
{
    if (!m_li) return;

    libinput_dispatch(m_li);

    libinput_event *ev;
    while ((ev = libinput_get_event(m_li))) {
        auto type = libinput_event_get_type(ev);

        if (type == LIBINPUT_EVENT_POINTER_MOTION) {
            auto *pev = libinput_event_get_pointer_event(ev);
            m_rawX += libinput_event_pointer_get_dx(pev);
            m_rawY += libinput_event_pointer_get_dy(pev);

            m_rawX = qBound(0.0, m_rawX, m_screenWidth);
            m_rawY = qBound(0.0, m_rawY, m_screenHeight);

            m_mouseX = m_rawX / m_screenWidth;
            m_mouseY = m_rawY / m_screenHeight;
            emit positionChanged();
            m_lastMovement.restart();
        }
        else if (type == LIBINPUT_EVENT_POINTER_MOTION_ABSOLUTE) {
            auto *pev = libinput_event_get_pointer_event(ev);
            m_mouseX = libinput_event_pointer_get_absolute_x_transformed(pev, 1.0);
            m_mouseY = libinput_event_pointer_get_absolute_y_transformed(pev, 1.0);
            m_rawX = m_mouseX * m_screenWidth;
            m_rawY = m_mouseY * m_screenHeight;
            emit positionChanged();
            m_lastMovement.restart();
        }

        libinput_event_destroy(ev);
    }
}
