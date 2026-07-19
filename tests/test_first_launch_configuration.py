from decimal import Decimal

import pytest

from trader_assist_v0.first_launch.configuration import ConfigurationError, RiskConfiguration


def test_strict_external_configuration_and_hard_cap() -> None:
    config = RiskConfiguration.from_json(
        '{"CONFIGURATION_VERSION":"r3.0","ACCOUNT_EQUITY_USD":"100.00",'
        '"RISK_PER_TRADE_PCT":"0.2500","MAX_NOTIONAL_USD":null}'
    )
    assert config.effective_max_notional == Decimal("2500.00")
    assert config.configuration_hash == RiskConfiguration.digest(
        "r3.0", Decimal("100.00"), Decimal("0.2500"), None
    )


@pytest.mark.parametrize(
    "raw",
    (
        '{"CONFIGURATION_VERSION":"r","ACCOUNT_EQUITY_USD":100,"RISK_PER_TRADE_PCT":"0.25","MAX_NOTIONAL_USD":null}',
        '{"CONFIGURATION_VERSION":"r","ACCOUNT_EQUITY_USD":"100.00","RISK_PER_TRADE_PCT":"2e-1","MAX_NOTIONAL_USD":null}',
        '{"CONFIGURATION_VERSION":"r","ACCOUNT_EQUITY_USD":"100.00","RISK_PER_TRADE_PCT":"0.25","MAX_NOTIONAL_USD":"10.00","extra":null}',
    ),
)
def test_configuration_rejects_coercion_and_extra_keys(raw: str) -> None:
    with pytest.raises(ConfigurationError):
        RiskConfiguration.from_json(raw)
