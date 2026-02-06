from pydoover.docker import run_app

from .application import AgbotApplication
from .app_config import AgbotConfig

def main():
    """
    Run the application.
    """
    run_app(AgbotApplication(config=AgbotConfig()))
