"""OIDC identity verification for the three SSO providers in the 15-day plan (Day 5):
Microsoft Entra ID, Google, and Apple Sign-In.

Each provider verifies a caller-supplied `id_token` against the provider's published JWKS
and expected issuer/audience, then returns a stable `ExternalIdentity`. The JWKS client is
injectable so verification never needs a live network call in tests (mirrors Day 6's plan
to mock IdP responses); production code paths still do a real fetch against each
provider's well-known JWKS endpoint.
"""

from dataclasses import dataclass

import jwt
from jwt import PyJWKClient


class OAuthVerificationError(RuntimeError):
    """Raised when an id_token fails signature, issuer, audience, or claim validation."""


@dataclass(frozen=True)
class ExternalIdentity:
    subject: str
    email: str
    full_name: str


class OIDCProvider:
    """Verifies RS256 id_tokens issued by a standards-compliant OIDC provider."""

    name = "oidc"

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        jwks_client: PyJWKClient | None = None,
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._jwks_client = jwks_client or PyJWKClient(jwks_url)

    def verify(self, id_token: str) -> ExternalIdentity:
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(id_token)
            payload = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
            )
        except jwt.PyJWTError as exc:
            raise OAuthVerificationError(f"{self.name}: {exc}") from exc
        try:
            email = payload["email"]
        except KeyError as exc:
            # Apple only includes `email` on a user's first authorization; a returning
            # Apple user without a stored mapping would fail here (tracked as a Day 16
            # follow-up: persist provider+subject, not just email, once Apple ships).
            raise OAuthVerificationError(f"{self.name}: id_token is missing the email claim") from exc
        return ExternalIdentity(subject=payload["sub"], email=email, full_name=payload.get("name", email))


class MicrosoftEntraProvider(OIDCProvider):
    name = "microsoft"


class GoogleOAuthProvider(OIDCProvider):
    name = "google"


class AppleSignInProvider(OIDCProvider):
    name = "apple"
