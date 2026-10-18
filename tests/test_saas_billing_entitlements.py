"""Stripe entitlements are tied to the configured recurring product, not metadata."""

from webapp.saas import _is_pro_subscription


def test_exact_price_required_for_pro_entitlement():
    valid = {
        "id": "sub_demo",
        "status": "active",
        "metadata": {"dqd_user_id": "not_a_valid_user"},
        "items": {
            "data": [
                {"price": {"id": "price_real_pro", "type": "recurring"}}
            ]
        },
    }
    assert _is_pro_subscription(valid, "price_real_pro") is True
    assert _is_pro_subscription(valid, "price_unrelated") is False


def test_stripe_signature_and_user_metadata_are_not_sufficient():
    unrelated = {
        "id": "sub_for_different_product",
        "status": "active",
        "metadata": {"dqd_user_id": "the_customer_uuid"},
        "items": {"data": [{"price": {"id": "price_other"}}]},
    }
    assert _is_pro_subscription(unrelated, "price_real_pro") is False
    assert _is_pro_subscription({"items": {"data": []}}, "price_real_pro") is False
    assert _is_pro_subscription({"items": "invalid"}, "price_real_pro") is False
    assert _is_pro_subscription(None, "price_real_pro") is False
    assert _is_pro_subscription(unrelated, "") is False
