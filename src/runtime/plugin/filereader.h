#ifndef FILEREADER_H
#define FILEREADER_H

#include <QObject>
#include <QString>
#include <QFile>
#include <QDir>

class FileReader : public QObject
{
    Q_OBJECT

public:
    explicit FileReader(QObject *parent = nullptr) : QObject(parent) {}

    Q_INVOKABLE QString readFile(const QString &path) const
    {
        QFile file(path);
        if (!file.open(QIODevice::ReadOnly | QIODevice::Text))
            return QString();
        return QString::fromUtf8(file.readAll());
    }

    Q_INVOKABLE QString homePath() const
    {
        return QDir::homePath();
    }

    Q_INVOKABLE QStringList listDirs(const QString &path) const
    {
        QDir dir(path);
        if (!dir.exists())
            return QStringList();
        return dir.entryList(QDir::Dirs | QDir::NoDotAndDotDot);
    }
};

#endif
