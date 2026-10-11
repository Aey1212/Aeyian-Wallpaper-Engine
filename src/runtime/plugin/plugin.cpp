#include <QQmlExtensionPlugin>
#include <QQmlEngine>
#include "cursorreceiver.h"
#include "filereader.h"
#include "projectwatcher.h"

class AeyianWallpaperPlugin : public QQmlExtensionPlugin
{
    Q_OBJECT
    Q_PLUGIN_METADATA(IID QQmlExtensionInterface_iid)

public:
    void registerTypes(const char *uri) override
    {
        qmlRegisterType<CursorReceiver>(uri, 1, 0, "CursorReceiver");
        qmlRegisterType<FileReader>(uri, 1, 0, "FileReader");
        qmlRegisterType<ProjectWatcher>(uri, 1, 0, "ProjectWatcher");
    }
};

#include "plugin.moc"
