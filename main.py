from src.chat_service import ChatService
from src.config import AppConfig
from src.lmstudio_client import LMStudioClient
from src.ui import ChatUI


def main() -> None:
    config = AppConfig()
    client = LMStudioClient()
    service = ChatService()
    app = ChatUI(config=config, client=client, chat_service=service)
    app.run()


if __name__ == "__main__":
    main()
