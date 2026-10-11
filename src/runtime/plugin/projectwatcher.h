#ifndef PROJECTWATCHER_H
#define PROJECTWATCHER_H

#include <QObject>
#include <QString>
#include <QDir>
#include <QFileSystemWatcher>
#include <QTimer>

class ProjectWatcher : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString path READ path WRITE setPath NOTIFY pathChanged)

public:
    explicit ProjectWatcher(QObject *parent = nullptr) : QObject(parent)
    {
        m_debounce.setSingleShot(true);
        m_debounce.setInterval(150);
        connect(&m_watcher, &QFileSystemWatcher::directoryChanged,
                &m_debounce, qOverload<>(&QTimer::start));
        connect(&m_watcher, &QFileSystemWatcher::fileChanged,
                &m_debounce, qOverload<>(&QTimer::start));
        connect(&m_debounce, &QTimer::timeout, this, [this]() {
            watchFiles();
            emit changed();
        });
    }

    QString path() const { return m_path; }

    void setPath(const QString &path)
    {
        if (path == m_path)
            return;
        if (!m_watcher.directories().isEmpty())
            m_watcher.removePaths(m_watcher.directories());
        m_path = path;
        if (!m_path.isEmpty())
            m_watcher.addPaths({m_path, m_path + QStringLiteral("/assets")});
        watchFiles();
        emit pathChanged();
    }

signals:
    void pathChanged();
    void changed();

private:
    void watchFiles()
    {
        if (!m_watcher.files().isEmpty())
            m_watcher.removePaths(m_watcher.files());
        if (m_path.isEmpty())
            return;
        QStringList files;
        for (const QString &folder : {m_path, m_path + QStringLiteral("/assets")}) {
            const QDir dir(folder);
            for (const QString &name : dir.entryList(QDir::Files))
                files << dir.filePath(name);
        }
        if (!files.isEmpty())
            m_watcher.addPaths(files);
    }

    QFileSystemWatcher m_watcher;
    QTimer m_debounce;
    QString m_path;
};

#endif
