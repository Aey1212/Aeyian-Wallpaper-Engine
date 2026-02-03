#ifndef CURSORPROVIDER_H
#define CURSORPROVIDER_H

#include <QObject>
#include <QSocketNotifier>
#include <libinput.h>

class CursorProvider : public QObject
{
    Q_OBJECT
    Q_PROPERTY(qreal mouseX READ mouseX NOTIFY positionChanged)
    Q_PROPERTY(qreal mouseY READ mouseY NOTIFY positionChanged)
    Q_PROPERTY(qreal screenWidth READ screenWidth WRITE setScreenWidth)
    Q_PROPERTY(qreal screenHeight READ screenHeight WRITE setScreenHeight)

public:
    explicit CursorProvider(QObject *parent = nullptr);
    ~CursorProvider();

    qreal mouseX() const { return m_mouseX; }
    qreal mouseY() const { return m_mouseY; }
    qreal screenWidth() const { return m_screenWidth; }
    qreal screenHeight() const { return m_screenHeight; }

    void setScreenWidth(qreal w) { m_screenWidth = w; }
    void setScreenHeight(qreal h) { m_screenHeight = h; }

    // Must be public for libinput_interface
    static int openRestricted(const char *path, int flags, void *userData);
    static void closeRestricted(int fd, void *userData);

signals:
    void positionChanged();

private slots:
    void handleEvents();

private:
    libinput *m_li = nullptr;
    udev *m_udev = nullptr;
    QSocketNotifier *m_notifier = nullptr;
    
    qreal m_rawX = 0.0;
    qreal m_rawY = 0.0;
    qreal m_mouseX = 0.0;
    qreal m_mouseY = 0.0;
    qreal m_screenWidth = 1920.0;
    qreal m_screenHeight = 1080.0;
};

#endif
