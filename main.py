import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from application.app import MyMoneyApp  # noqa: E402

application = MyMoneyApp()
application.run()
