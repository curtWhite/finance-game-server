import threading
from contextlib import contextmanager

# A reentrant lock ensures nested save/load calls in the same thread do not deadlock,
# while still allowing only one thread to perform DB operations at a time.
_db_call_lock = threading.RLock()
_db_call_flag = {"active": False}


@contextmanager
def db_call_guard(label: str = "db_call"):
    """
    Serialize DB save/load operations across classes.

    The flag tracks whether a DB call is active; the RLock ensures only one
    thread enters at a time while allowing re-entrancy within the same thread.
    """
    with _db_call_lock:
        was_active = _db_call_flag["active"]
        _db_call_flag["active"] = True
        try:
            yield
        finally:
            if not was_active:
                _db_call_flag["active"] = False

