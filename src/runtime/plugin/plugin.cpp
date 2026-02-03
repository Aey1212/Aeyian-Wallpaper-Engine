#include <QQmlExtensionPlugin>
#include <QQmlEngine>
#include "cursorprovider.h"

class AeyianWallpaperPlugin : public QQmlExtensionPlugin
{
    Q_OBJECT
    Q_PLUGIN_METADATA(IID QQmlExtensionInterface_iid)

public:
    void registerTypes(const char *uri) override
    {
        qmlRegisterType<CursorProvider>(uri, 1, 0, "CursorProvider");
    }
};

#include "plugin.moc"
