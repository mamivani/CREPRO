"""Direct unit tests for OIDCProvider.verify, independent of any particular provider's
real JWKS endpoint. A fake jwks_client stands in for PyJWKClient so these tests sign and
verify RS256 id_tokens entirely offline.
"""

import jwt
import pytest
from crepro_identity.oauth import GoogleOAuthProvider, OAuthVerificationError
from cryptography.hazmat.primitives.asymmetric import rsa


class _FakeSigningKey:
    def __init__(self, key) -> None:
        self.key = key


class _FakeJwksClient:
    def __init__(self, public_key) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(self._public_key)


@pytest.fixture(scope="module")
def keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _provider(public_key) -> GoogleOAuthProvider:
    return GoogleOAuthProvider(
        issuer="https://accounts.google.com",
        audience="test-client-id",
        jwks_url="https://unused.example.com/keys",
        jwks_client=_FakeJwksClient(public_key),
    )


def _sign(private_key, **claims) -> str:
    return jwt.encode(claims, private_key, algorithm="RS256")


def test_verify_returns_identity_from_valid_id_token(keypair) -> None:
    private_key, public_key = keypair
    token = _sign(
        private_key,
        iss="https://accounts.google.com",
        aud="test-client-id",
        sub="google-subject-1",
        email="jordan@example.com",
        name="Jordan Who",
    )

    identity = _provider(public_key).verify(token)

    assert identity.subject == "google-subject-1"
    assert identity.email == "jordan@example.com"
    assert identity.full_name == "Jordan Who"


def test_verify_defaults_full_name_to_email_when_name_claim_missing(keypair) -> None:
    private_key, public_key = keypair
    token = _sign(
        private_key,
        iss="https://accounts.google.com",
        aud="test-client-id",
        sub="google-subject-2",
        email="noname@example.com",
    )

    identity = _provider(public_key).verify(token)

    assert identity.full_name == "noname@example.com"


def test_verify_rejects_token_missing_email(keypair) -> None:
    private_key, public_key = keypair
    token = _sign(
        private_key, iss="https://accounts.google.com", aud="test-client-id", sub="google-subject-3"
    )

    with pytest.raises(OAuthVerificationError):
        _provider(public_key).verify(token)


def test_verify_rejects_wrong_audience(keypair) -> None:
    private_key, public_key = keypair
    token = _sign(
        private_key,
        iss="https://accounts.google.com",
        aud="someone-elses-client-id",
        sub="google-subject-4",
        email="jordan@example.com",
    )

    with pytest.raises(OAuthVerificationError):
        _provider(public_key).verify(token)


def test_verify_rejects_wrong_issuer(keypair) -> None:
    private_key, public_key = keypair
    token = _sign(
        private_key,
        iss="https://not-google.example.com",
        aud="test-client-id",
        sub="google-subject-5",
        email="jordan@example.com",
    )

    with pytest.raises(OAuthVerificationError):
        _provider(public_key).verify(token)
