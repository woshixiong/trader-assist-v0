"""Default-off bounded runtime entry points.

This package hosts the restricted public First Launch runtime composition
(``first_launch_public_runtime``), its local SQLite durability surface
(``first_launch_runtime_store``), the configured HTTPS webhook outbox
(``first_launch_notification``), and the existing in-memory public-frame
protocol and signal lifecycle (``first_launch_operator_assist``).

All entry points are default-off; activation requires both the
``--enable-restricted-public-runtime`` flag and the
``RESTRICTED_PUBLIC_LIVE_SHADOW`` runtime mode.
"""

