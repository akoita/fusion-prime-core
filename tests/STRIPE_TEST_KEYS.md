# Stripe Test Keys

These are test API keys for Stripe integration testing.

## Test Keys

**Public Key (Frontend):**
```
pk_test_51SPLGvIg5vewLec7YBrzCiKIDjNiTukigUxsi5X6EASHcCnaOMcBxmVq6sRWjliKrSqejtPoBGGaBx3MpGmoWyjB00ba9UFMXL
```

**Secret Key (Backend):**
```
sk_test_51SPLGvIg5vewLec7RcRKbVoXEfDmmz16yzd0svw1BvQSqX7oxf4Lh7vyYb1YoPbtUj18xGZxoBd3FfSNX8KA4Uqh00BBlZrifw
```

## Usage

To run Fiat Gateway tests with Stripe:

```bash
export STRIPE_SECRET_KEY='sk_test_51SPLGvIg5vewLec7RcRKbVoXEfDmmz16yzd0svw1BvQSqX7oxf4Lh7vyYb1YoPbtUj18xGZxoBd3FfSNX8KA4Uqh00BBlZrifw'
pytest tests/test_fiat_gateway_integration.py::TestFiatGatewayTransactions -v
```

## Note

These are test keys and can only be used in Stripe test mode. They will not process real payments.
