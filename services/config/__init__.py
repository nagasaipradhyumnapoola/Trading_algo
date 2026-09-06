"""config — typed application settings and the demo/real runtime boundary.

Nothing else in the system reads os.environ directly; everything goes through
`Settings`. In real mode, missing required configuration fails fast at startup.
"""

from .settings import (
    AppMode,
    ConfigError,
    Settings,
    get_settings,
    load_settings,
)

__all__ = ["AppMode", "ConfigError", "Settings", "get_settings", "load_settings"]
