from risk_rules import label_risk, score_transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_tx(**overrides):
    """Minimal transaction with every risk signal at its non-triggering value."""
    tx = {
        "device_risk_score": 0,
        "is_international": 0,
        "amount_usd": 0,
        "velocity_24h": 0,
        "failed_logins_24h": 0,
        "prior_chargebacks": 0,
    }
    tx.update(overrides)
    return tx


# ---------------------------------------------------------------------------
# label_risk — threshold and boundary tests
# ---------------------------------------------------------------------------

def test_label_risk_thresholds():
    assert label_risk(10) == "low"
    assert label_risk(35) == "medium"
    assert label_risk(75) == "high"


def test_label_risk_boundary_at_30():
    assert label_risk(29) == "low"
    assert label_risk(30) == "medium"


def test_label_risk_boundary_at_60():
    assert label_risk(59) == "medium"
    assert label_risk(60) == "high"


# ---------------------------------------------------------------------------
# score_transaction — device risk score
# ---------------------------------------------------------------------------

def test_device_risk_below_40_adds_nothing():
    assert score_transaction(_base_tx(device_risk_score=39)) == 0


def test_device_risk_at_40_adds_10():
    assert score_transaction(_base_tx(device_risk_score=40)) == 10


def test_device_risk_mid_range_adds_10():
    assert score_transaction(_base_tx(device_risk_score=55)) == 10


def test_device_risk_at_69_adds_10():
    assert score_transaction(_base_tx(device_risk_score=69)) == 10


def test_device_risk_at_70_adds_25():
    assert score_transaction(_base_tx(device_risk_score=70)) == 25


def test_device_risk_above_70_adds_25():
    assert score_transaction(_base_tx(device_risk_score=85)) == 25


def test_high_device_risk_increases_score():
    # Regression: bug 1 had high device risk subtracting 25 instead of adding.
    low_device = score_transaction(_base_tx(device_risk_score=10))
    high_device = score_transaction(_base_tx(device_risk_score=85))
    assert high_device > low_device


# ---------------------------------------------------------------------------
# score_transaction — international flag
# ---------------------------------------------------------------------------

def test_domestic_transaction_adds_nothing():
    assert score_transaction(_base_tx(is_international=0)) == 0


def test_international_transaction_adds_15():
    assert score_transaction(_base_tx(is_international=1)) == 15


def test_international_flag_increases_score():
    # Regression: bug 2 had international transactions subtracting 15.
    domestic = score_transaction(_base_tx(is_international=0))
    international = score_transaction(_base_tx(is_international=1))
    assert international > domestic


# ---------------------------------------------------------------------------
# score_transaction — transaction amount
# ---------------------------------------------------------------------------

def test_large_amount_adds_risk():
    tx = {
        "device_risk_score": 10,
        "is_international": 0,
        "amount_usd": 1200,
        "velocity_24h": 1,
        "failed_logins_24h": 0,
        "prior_chargebacks": 0,
    }
    assert score_transaction(tx) >= 25


def test_amount_below_500_adds_nothing():
    assert score_transaction(_base_tx(amount_usd=499)) == 0


def test_amount_at_500_adds_10():
    assert score_transaction(_base_tx(amount_usd=500)) == 10


def test_amount_mid_range_adds_10():
    assert score_transaction(_base_tx(amount_usd=750)) == 10


def test_amount_at_999_adds_10():
    assert score_transaction(_base_tx(amount_usd=999)) == 10


def test_amount_at_1000_adds_25():
    assert score_transaction(_base_tx(amount_usd=1000)) == 25


def test_amount_above_1000_adds_25():
    assert score_transaction(_base_tx(amount_usd=2000)) == 25


# ---------------------------------------------------------------------------
# score_transaction — transaction velocity
# ---------------------------------------------------------------------------

def test_velocity_below_3_adds_nothing():
    assert score_transaction(_base_tx(velocity_24h=2)) == 0


def test_velocity_at_3_adds_5():
    assert score_transaction(_base_tx(velocity_24h=3)) == 5


def test_velocity_mid_range_adds_5():
    assert score_transaction(_base_tx(velocity_24h=4)) == 5


def test_velocity_at_5_adds_5():
    assert score_transaction(_base_tx(velocity_24h=5)) == 5


def test_velocity_at_6_adds_20():
    assert score_transaction(_base_tx(velocity_24h=6)) == 20


def test_velocity_above_6_adds_20():
    assert score_transaction(_base_tx(velocity_24h=10)) == 20


def test_high_velocity_increases_score():
    # Regression: bug 3 had velocity >= 6 subtracting 20 instead of adding.
    low_vel = score_transaction(_base_tx(velocity_24h=1))
    high_vel = score_transaction(_base_tx(velocity_24h=10))
    assert high_vel > low_vel


# ---------------------------------------------------------------------------
# score_transaction — failed logins
# ---------------------------------------------------------------------------

def test_failed_logins_below_2_adds_nothing():
    assert score_transaction(_base_tx(failed_logins_24h=1)) == 0


def test_failed_logins_at_2_adds_10():
    assert score_transaction(_base_tx(failed_logins_24h=2)) == 10


def test_failed_logins_mid_range_adds_10():
    assert score_transaction(_base_tx(failed_logins_24h=3)) == 10


def test_failed_logins_at_4_adds_10():
    assert score_transaction(_base_tx(failed_logins_24h=4)) == 10


def test_failed_logins_at_5_adds_20():
    assert score_transaction(_base_tx(failed_logins_24h=5)) == 20


def test_failed_logins_above_5_adds_20():
    assert score_transaction(_base_tx(failed_logins_24h=8)) == 20


# ---------------------------------------------------------------------------
# score_transaction — prior chargebacks
# ---------------------------------------------------------------------------

def test_no_prior_chargebacks_adds_nothing():
    assert score_transaction(_base_tx(prior_chargebacks=0)) == 0


def test_one_prior_chargeback_adds_5():
    assert score_transaction(_base_tx(prior_chargebacks=1)) == 5


def test_two_prior_chargebacks_adds_20():
    assert score_transaction(_base_tx(prior_chargebacks=2)) == 20


def test_many_prior_chargebacks_adds_20():
    assert score_transaction(_base_tx(prior_chargebacks=5)) == 20


def test_prior_chargebacks_increase_score():
    # Regression: bug 4 had prior chargebacks subtracting points instead of adding.
    clean = score_transaction(_base_tx(prior_chargebacks=0))
    repeat = score_transaction(_base_tx(prior_chargebacks=3))
    assert repeat > clean


# ---------------------------------------------------------------------------
# score_transaction — score bounds
# ---------------------------------------------------------------------------

def test_score_floor_is_zero():
    assert score_transaction(_base_tx()) == 0


def test_score_ceiling_is_100():
    # All high-risk signals fire: 25+15+25+20+20+20 = 125, clamped to 100.
    tx = _base_tx(
        device_risk_score=85,
        is_international=1,
        amount_usd=1500,
        velocity_24h=10,
        failed_logins_24h=7,
        prior_chargebacks=3,
    )
    assert score_transaction(tx) == 100


# ---------------------------------------------------------------------------
# score_transaction — real-world scenario profiles
# ---------------------------------------------------------------------------

def test_confirmed_fraud_profile_scores_high():
    # Matches transaction 50011 from the dataset: $1,400 crypto, Russia,
    # device score 85, 8 transactions in 24h, 7 failed logins, 1 prior chargeback.
    # Expected score: 25+15+25+20+20+5 = 110 → clamped to 100.
    tx = _base_tx(
        device_risk_score=85,
        is_international=1,
        amount_usd=1400,
        velocity_24h=8,
        failed_logins_24h=7,
        prior_chargebacks=1,
    )
    assert score_transaction(tx) == 100
    assert label_risk(score_transaction(tx)) == "high"


def test_clean_low_value_profile_scores_low():
    # Matches transaction 50001: $45 grocery, domestic, clean device, 1 txn, no history.
    tx = _base_tx(
        device_risk_score=8,
        is_international=0,
        amount_usd=45,
        velocity_24h=1,
        failed_logins_24h=0,
        prior_chargebacks=0,
    )
    assert score_transaction(tx) == 0
    assert label_risk(score_transaction(tx)) == "low"


def test_moderate_risk_profile_scores_medium():
    # Large purchase, medium-risk device, no other red flags.
    tx = _base_tx(
        device_risk_score=55,
        is_international=0,
        amount_usd=2000,
        velocity_24h=1,
        failed_logins_24h=0,
        prior_chargebacks=0,
    )
    # Score: 10 (device) + 25 (amount) = 35
    assert score_transaction(tx) == 35
    assert label_risk(score_transaction(tx)) == "medium"
