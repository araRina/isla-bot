from common import setup_logging
from isla import Isla


with setup_logging():
    Isla.with_config().run()
