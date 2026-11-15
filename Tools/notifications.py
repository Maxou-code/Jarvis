from winotify import Notification, audio

NOTIFICATION_SENT = False
def notify_user(title="JARVIS", message="Tâche terminée."):
    global NOTIFICATION_SENT

    notification = Notification(
        app_id="JARVIS Assistant",
        title=title,
        msg=message,
        duration="short"
    )

    notification.set_audio(
        audio.Default,
        loop=False
    )

    notification.show()

    NOTIFICATION_SENT = True

    return "Notification Windows envoyée."
