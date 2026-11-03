import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

import sys

from application.app import MyMoneyApp

from MySpaceShared.core.deep_links import parse_cli_route

application = MyMoneyApp(initial_route=parse_cli_route(sys.argv[1:]))
application.run()
