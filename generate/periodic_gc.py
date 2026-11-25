"""Full garbage collection at a fixed interval during a projection."""

import gc
import signal


def start(interval):
    """Run gc.collect() every `interval` seconds, from a timer signal.

    Parameters
    ----------
    interval : float or None
        Seconds between collections. None turns it off.
    """
    if interval is None:
        return
    interval = float(interval)
    if interval <= 0:
        raise ValueError("gc-interval must be positive, got %s" % interval)

    signal.signal(signal.SIGALRM, lambda signum, frame: gc.collect())
    signal.siginterrupt(signal.SIGALRM, False)
    signal.setitimer(signal.ITIMER_REAL, interval, interval)
    print("Full garbage collection every %g s." % interval)
