import smtplib

from email.message import EmailMessage

from .settings_manager import (
    get_smtp_settings,
)


def send_email(
    db,
    to_address: str,
    subject: str,
    body: str,
):

    settings = get_smtp_settings(
        db
    )

    host = settings[
        "smtp_host"
    ].strip()

    if not host:
        raise RuntimeError(
            "SMTP is not configured"
        )

    port = int(
        settings[
            "smtp_port"
        ]
        or 587
    )

    username = settings[
        "smtp_username"
    ]

    password = settings[
        "smtp_password"
    ]

    security = settings[
        "smtp_security"
    ]

    from_name = settings[
        "smtp_from_name"
    ]

    from_address = settings[
        "smtp_from_address"
    ].strip()

    if not from_address:
        raise RuntimeError(
            "SMTP From Address is required"
        )


    message = EmailMessage()

    message["Subject"] = subject

    message["From"] = (
        f"{from_name} <{from_address}>"
        if from_name
        else from_address
    )

    message["To"] = to_address

    message.set_content(
        body
    )


    if security == "ssl":

        server = smtplib.SMTP_SSL(
            host,
            port,
            timeout=20,
        )

    else:

        server = smtplib.SMTP(
            host,
            port,
            timeout=20,
        )


    try:

        server.ehlo()

        if security == "starttls":

            server.starttls()

            server.ehlo()


        if username:

            server.login(
                username,
                password,
            )


        server.send_message(
            message
        )

    finally:

        server.quit()