"""Allow running the application with ``python3 -m icinga_modern_notifications``."""

import sys

from .cli import main

sys.exit(main())
