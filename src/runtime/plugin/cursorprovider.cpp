#include "cursorprovider.h"
#include <QDebug>
#include <QProcess>
#include <QFile>
#include <QFileInfo>
#include <QRegularExpression>
#include <QStandardPaths>
#include <fcntl.h>
#include <unistd.h>
#include <libudev.h>

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


static QString findQdbus()
{
    for (const auto &cmd : {"qdbus6", "qdbus", "qdbus-qt5"}) {
        QString path = QStandardPaths::findExecutable(cmd);
        if (!path.isEmpty())
            return path;
    }
    return QStringLiteral("qdbus");  // I hope this is a proper fallback
}

CursorProvider::CursorProvider(QObject *parent)
: QObject(parent)
{
    m_qdbusCmd = findQdbus();

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

    setupEmitTimer();
    setupCalibrationTimer();

    calibrate();

    m_lastCalibration.start();
    m_lastMovement.start();
}

CursorProvider::~CursorProvider()
{
    if (m_li) libinput_unref(m_li);
    if (m_udev) udev_unref(m_udev);
}

void CursorProvider::setupEmitTimer()
{
    m_emitTimer = new QTimer(this);
    m_emitTimer->setTimerType(Qt::PreciseTimer);
    m_emitTimer->setSingleShot(true);
    m_emitTimer->setInterval(16);  // ~60fps
    connect(m_emitTimer, &QTimer::timeout, this, &CursorProvider::emitIfDirty);
}

void CursorProvider::emitIfDirty()
{
    if (m_dirty) {
        m_dirty = false;
        emit positionChanged();
    }
}


static inline void schedulePositionUpdate(QTimer *timer, bool &dirty)
{
    dirty = true;
    if (!timer->isActive())
        timer->start();
}


void CursorProvider::setupCalibrationTimer()
{
    m_calibrationTimer = new QTimer(this);
    connect(m_calibrationTimer, &QTimer::timeout, this, &CursorProvider::calibrate);
    m_calibrationTimer->start(3600000); // 1 hour in milliseconds
}

static const QString CALIBRATION_SCRIPT_PATH = QStringLiteral("/tmp/aeyian-cursor-calibrate.qml");

void CursorProvider::calibrate()
{
    // Don't overlap calibrations please?
    if (m_calibrating) {
        qDebug() << "Calibration already in progress, skipping";
        return;
    }

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

    m_calibrating = true;
    m_lastCalibration.restart();

    // reuse recycle repurpose
    if (!QFileInfo::exists(CALIBRATION_SCRIPT_PATH)) {
        QFile scriptFile(CALIBRATION_SCRIPT_PATH);
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
            m_calibrating = false;
            return;
        }
    }

    // Step 1: Load the KWin script
    auto *loadProc = new QProcess(this);
    connect(loadProc, qOverload<int, QProcess::ExitStatus>(&QProcess::finished),
            this, [this, loadProc](int exitCode, QProcess::ExitStatus) {
        loadProc->deleteLater();
        onScriptLoaded(exitCode);
    });
    loadProc->start(m_qdbusCmd, {"org.kde.KWin", "/Scripting",
        "org.kde.kwin.Scripting.loadDeclarativeScript", CALIBRATION_SCRIPT_PATH, "aeyian-calibrate"});
}

void CursorProvider::onScriptLoaded(int exitCode)
{
    if (exitCode != 0) {
        qWarning() << "Failed to load calibration script (exit" << exitCode << ")";
        m_calibrating = false;
        return;
    }

    // Step 2: Start the KWin script
    auto *startProc = new QProcess(this);
    connect(startProc, qOverload<int, QProcess::ExitStatus>(&QProcess::finished),
            this, [this, startProc](int exitCode, QProcess::ExitStatus) {
        startProc->deleteLater();
        onScriptStarted(exitCode);
    });
    startProc->start(m_qdbusCmd, {"org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.start"});
}

void CursorProvider::onScriptStarted(int exitCode)
{
    if (exitCode != 0) {
        qWarning() << "Failed to start calibration script (exit" << exitCode << ")";
        m_calibrating = false;
        return;
    }

    // Step 3: Wait 50ms, read, profit!
    QTimer::singleShot(50, this, [this]() {
        auto *journalProc = new QProcess(this);
        connect(journalProc, qOverload<int, QProcess::ExitStatus>(&QProcess::finished),
                this, [this, journalProc](int exitCode, QProcess::ExitStatus) {

            QString output = journalProc->readAllStandardOutput();
            journalProc->deleteLater();
            onJournalRead(exitCode, output);
        });
        journalProc->start("journalctl", {"-t", "kwin_wayland", "-o", "cat", "--since", "5 seconds ago"});
    });
}

void CursorProvider::onJournalRead(int exitCode, const QString &output)
{
    QRegularExpression re("AEYIAN_CURSOR:(\\d+),(\\d+)");
    QRegularExpressionMatch match = re.match(output);
    if (match.hasMatch()) {
        m_rawX = match.captured(1).toDouble();
        m_rawY = match.captured(2).toDouble();
        m_mouseX = m_rawX / m_screenWidth;
        m_mouseY = m_rawY / m_screenHeight;
        emit positionChanged();  // Calibration is infrequent, emit immediately
        qDebug() << "Calibrated cursor position:" << m_rawX << m_rawY;
    } else {
        qWarning() << "Failed to parse cursor position from journal (exit" << exitCode << ")";
    }

    // disengage
    auto *unloadProc = new QProcess(this);
    connect(unloadProc, qOverload<int, QProcess::ExitStatus>(&QProcess::finished),
            this, [this, unloadProc](int exitCode, QProcess::ExitStatus) {
        unloadProc->deleteLater();
        onScriptUnloaded(exitCode);
    });
    unloadProc->start(m_qdbusCmd, {"org.kde.KWin", "/Scripting",
        "org.kde.kwin.Scripting.unloadScript", "aeyian-calibrate"});
}

void CursorProvider::onScriptUnloaded(int exitCode)
{
    Q_UNUSED(exitCode);
    m_calibrating = false;
    qDebug() << "Calibration complete";
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
            schedulePositionUpdate(m_emitTimer, m_dirty);
            m_lastMovement.restart();
        }
        else if (type == LIBINPUT_EVENT_POINTER_MOTION_ABSOLUTE) {
            auto *pev = libinput_event_get_pointer_event(ev);
            m_mouseX = libinput_event_pointer_get_absolute_x_transformed(pev, 1.0);
            m_mouseY = libinput_event_pointer_get_absolute_y_transformed(pev, 1.0);
            m_rawX = m_mouseX * m_screenWidth;
            m_rawY = m_mouseY * m_screenHeight;
            schedulePositionUpdate(m_emitTimer, m_dirty);
            m_lastMovement.restart();
        }

        libinput_event_destroy(ev);
    }
}

// I HATE C++
