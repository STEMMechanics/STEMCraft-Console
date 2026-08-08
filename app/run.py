import os

import uvicorn

from dotenv import load_dotenv


load_dotenv(
    os.getenv(
        "STEMCRAFT_CONSOLE_ENV",
        ".env",
    )
)


def main():

    host = os.getenv(
        "STEMCRAFT_CONSOLE_HOST",
        "127.0.0.1",
    )

    port = int(
        os.getenv(
            "STEMCRAFT_CONSOLE_PORT",
            "8000",
        )
    )

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()