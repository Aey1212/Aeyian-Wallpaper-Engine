#include "cursorreceiver.h"
#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDBusMessage>
#include <QDBusServiceWatcher>
#include <QTimer>

static const QString SERVICE = QStringLiteral("org.aey.wallpaperengine");
static const QString OBJECT_PATH = QStringLiteral("/Cursor");
static const QString SCRIPT_NAME = QStringLiteral("aeyian_cursor_v1");
static const QString KWIN_SERVICE = QStringLiteral("org.kde.KWin");
static const int KWIN_CALL_TIMEOUT_MS = 500;
static const int KWIN_SETTLE_MS = 3000;

static void callScripting(const QString &method, const QVariantList &arguments, QDBus::CallMode mode)
{
    QDBusMessage message = QDBusMessage::createMethodCall(
        KWIN_SERVICE, QStringLiteral("/Scripting"), QStringLiteral("org.kde.kwin.Scripting"), method);
    message.setArguments(arguments);
    QDBusConnection::sessionBus().call(message, mode, KWIN_CALL_TIMEOUT_MS);
}

class CursorHub : public QObject
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "org.aey.wallpaperengine.Cursor")

public:
    explicit CursorHub(const QString &scriptPath)
    : m_scriptPath(scriptPath)
    {
        QDBusConnection bus = QDBusConnection::sessionBus();
        bus.interface()->registerService(SERVICE, QDBusConnectionInterface::ReplaceExistingService,
                                         QDBusConnectionInterface::AllowReplacement);
        bus.registerObject(OBJECT_PATH, this, QDBusConnection::ExportScriptableSlots);

        auto *kwinWatcher = new QDBusServiceWatcher(KWIN_SERVICE, bus,
                                                    QDBusServiceWatcher::WatchForRegistration, this);
        connect(kwinWatcher, &QDBusServiceWatcher::serviceRegistered, this, [this]() {
            QTimer::singleShot(KWIN_SETTLE_MS, this, &CursorHub::loadScript);
        });

        loadScript();
    }

    ~CursorHub()
    {
        callScripting(QStringLiteral("unloadScript"), {SCRIPT_NAME}, QDBus::Block);
        QDBusConnection bus = QDBusConnection::sessionBus();
        bus.unregisterObject(OBJECT_PATH);
        bus.unregisterService(SERVICE);
    }

    qreal x() const { return m_x; }
    qreal y() const { return m_y; }
    bool tracking() const { return m_tracking; }

public slots:
    Q_SCRIPTABLE void position(int x, int y)
    {
        m_x = x;
        m_y = y;
        m_tracking = true;
        emit positionChanged();
    }

signals:
    void positionChanged();

private:
    void loadScript()
    {
        callScripting(QStringLiteral("loadDeclarativeScript"), {m_scriptPath, SCRIPT_NAME}, QDBus::NoBlock);
        callScripting(QStringLiteral("start"), {}, QDBus::NoBlock);
    }

    QString m_scriptPath;
    qreal m_x = 0.0;
    qreal m_y = 0.0;
    bool m_tracking = false;
};

static CursorHub *s_hub = nullptr;
static int s_hubUsers = 0;

CursorReceiver::CursorReceiver(QObject *parent)
: QObject(parent)
{
}

CursorReceiver::~CursorReceiver()
{
    if (m_attached && --s_hubUsers == 0) {
        delete s_hub;
        s_hub = nullptr;
    }
}

void CursorReceiver::setScript(const QUrl &script)
{
    if (script == m_script)
        return;
    m_script = script;
    emit scriptChanged();
    if (m_attached || script.isEmpty())
        return;

    if (!s_hub)
        s_hub = new CursorHub(script.toLocalFile());
    s_hubUsers++;
    m_attached = true;
    connect(s_hub, &CursorHub::positionChanged, this, &CursorReceiver::positionChanged);
    emit positionChanged();
}

qreal CursorReceiver::x() const
{
    return m_attached ? s_hub->x() : 0.0;
}

qreal CursorReceiver::y() const
{
    return m_attached ? s_hub->y() : 0.0;
}

bool CursorReceiver::tracking() const
{
    return m_attached && s_hub->tracking();
}

#include "cursorreceiver.moc"
