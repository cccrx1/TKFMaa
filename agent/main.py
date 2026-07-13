import sys

from bootstrap import configure_runtime

configure_runtime()

from maa.agent.agent_server import AgentServer
from maa.tasker import Tasker

import stamina  # noqa: F401
import training  # noqa: F401
import recruitment  # noqa: F401
import daily_shop  # noqa: F401


def main():
    Tasker.set_log_dir("./debug")

    if len(sys.argv) < 2:
        print("Usage: python main.py <socket_id>")
        print("socket_id is provided by AgentIdentifier.")
        sys.exit(1)

    socket_id = sys.argv[-1]

    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":
    main()
