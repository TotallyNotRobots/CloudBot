import logging
import os
import signal
import sys
import time
from pathlib import Path

# import bot
from cloudbot.bot import CloudBot
from cloudbot.util import async_util

# store the original working directory, for use when restarting
original_wd = Path().resolve()

# set up environment - we need to make sure we are in the install directory
path0 = Path(sys.path[0] or ".").resolve()
install_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(install_dir))
os.chdir(str(install_dir))


def main():
    # Logging optimizations, doing it here because we only want to change this if we're the main file
    logging._srcfile = None
    logging.logThreads = 0
    logging.logProcesses = 0

    logger = logging.getLogger("cloudbot")
    logger.info("Starting CloudBot.")

    # create the bot
    _bot = CloudBot()

    # whether we are killed while restarting
    stopped_while_restarting = False

    # store the original SIGINT handler
    original_sigint = signal.getsignal(signal.SIGINT)

    # define closure for signal handling
    # The handler is called with two arguments: the signal number and the current stack frame
    # These parameters should NOT be removed
    # noinspection PyUnusedLocal
    def exit_gracefully(signum, frame):
        nonlocal stopped_while_restarting
        if not _bot:
            # we are currently in the process of restarting
            stopped_while_restarting = True
        else:
            async_util.run_coroutine_threadsafe(
                _bot.stop("Killed (Received SIGINT {})".format(signum)), _bot.loop
            )

        logger.warning("Bot received Signal Interrupt (%s)", signum)

        # restore the original handler so if they do it again it triggers
        signal.signal(signal.SIGINT, original_sigint)

    signal.signal(signal.SIGINT, exit_gracefully)

    # start the bot master

    # CloudBot.run() will return True if it should restart, False otherwise
    restart = _bot.run()

    # the bot has stopped, do we want to restart?
    if restart:
        # remove reference to cloudbot, so exit_gracefully won't try to stop it
        _bot = None
        # sleep one second for timeouts
        time.sleep(1)
        if stopped_while_restarting:
            logger.info("Received stop signal, no longer restarting")
        else:
            # actually restart
            os.chdir(str(original_wd))
            args = sys.argv
            logger.info("Restarting Bot")
            logger.debug("Restart arguments: %s", args)
            for f in [sys.stdout, sys.stderr]:
                f.flush()
            # close logging, and exit the program.
            logger.debug("Stopping logging engine")
            logging.shutdown()
            os.execv(sys.executable, [sys.executable] + args)  # nosec

    # close logging, and exit the program.
    logger.debug("Stopping logging engine")
    logging.shutdown()


if __name__ == "__main__":
    main()
