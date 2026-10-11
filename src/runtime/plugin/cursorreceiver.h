#ifndef CURSORRECEIVER_H
#define CURSORRECEIVER_H

#include <QObject>
#include <QUrl>

class CursorReceiver : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QUrl script READ script WRITE setScript NOTIFY scriptChanged)
    Q_PROPERTY(qreal x READ x NOTIFY positionChanged)
    Q_PROPERTY(qreal y READ y NOTIFY positionChanged)
    Q_PROPERTY(bool tracking READ tracking NOTIFY positionChanged)

public:
    explicit CursorReceiver(QObject *parent = nullptr);
    ~CursorReceiver();

    QUrl script() const { return m_script; }
    void setScript(const QUrl &script);

    qreal x() const;
    qreal y() const;
    bool tracking() const;

signals:
    void scriptChanged();
    void positionChanged();

private:
    QUrl m_script;
    bool m_attached = false;
};

#endif
