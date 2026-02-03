#include "cursorprovider.h"
#include <QDebug>
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
}

CursorProvider::~CursorProvider()
{
    if (m_li) libinput_unref(m_li);
    if (m_udev) udev_unref(m_udev);
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
        }
        else if (type == LIBINPUT_EVENT_POINTER_MOTION_ABSOLUTE) {
            auto *pev = libinput_event_get_pointer_event(ev);
            m_mouseX = libinput_event_pointer_get_absolute_x_transformed(pev, 1.0);
            m_mouseY = libinput_event_pointer_get_absolute_y_transformed(pev, 1.0);
            m_rawX = m_mouseX * m_screenWidth;
            m_rawY = m_mouseY * m_screenHeight;
            emit positionChanged();
        }
        
        libinput_event_destroy(ev);
    }
}
