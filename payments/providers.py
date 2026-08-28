"""
Thin provider adapters over the existing integrations. The heavy lifting still lives
in main.py (Stripe/ITEC) and paypal_service.py — this module gives a common shape and
a registry so new providers can be added without touching the order pipeline.
"""
import os


class PaymentProvider:
    name = "base"

    def is_configured(self) -> bool:
        raise NotImplementedError

    def describe(self) -> dict:
        return {"name": self.name, "configured": self.is_configured()}


class StripeProvider(PaymentProvider):
    name = "stripe"

    def is_configured(self) -> bool:
        key = os.getenv("STRIPE_SECRET_KEY", "")
        return bool(key) and not key.startswith("sk_test_your")


class PayPalProvider(PaymentProvider):
    name = "paypal"

    def is_configured(self) -> bool:
        try:
            from paypal_service import paypal_service
            return bool(getattr(paypal_service, "client_id", None))
        except Exception:
            return bool(os.getenv("PAYPAL_CLIENT_ID"))


class ItecProvider(PaymentProvider):
    name = "itec"

    def is_configured(self) -> bool:
        return bool(os.getenv("ITEC_API_KEY"))


REGISTRY = {
    "stripe": StripeProvider(),
    "paypal": PayPalProvider(),
    "itec": ItecProvider(),
    "momo": ItecProvider(),
    "card": ItecProvider(),
}


def available_providers() -> list[dict]:
    seen = {}
    for p in REGISTRY.values():
        seen[p.name] = p.describe()
    return list(seen.values())
