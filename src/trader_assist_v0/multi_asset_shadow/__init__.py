"""Public-data-only multi-asset Shadow runtime foundations.

This namespace is intentionally separate from the frozen ETH runtime.  It owns
no credentials, signing, account access, or exchange-write capability.
"""

from .models import ClosedBar, MarketIdentity, RegistryMarket, RegistryTier
from .registry import MarketRegistryManager, RegistryError

__all__ = [
    "ClosedBar",
    "MarketIdentity",
    "MarketRegistryManager",
    "RegistryError",
    "RegistryMarket",
    "RegistryTier",
]
