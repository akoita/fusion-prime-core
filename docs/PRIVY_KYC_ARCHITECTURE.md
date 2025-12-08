# Privy + KYC Integration Architecture

**Date**: November 4, 2025
**Status**: Planning Document
**Stack**: Privy (Auth) + Persona (KYC)

---

## 📊 Database Schema

### Users Table

```sql
CREATE TABLE users (
  -- Primary Identity (from Privy)
  id VARCHAR(255) PRIMARY KEY,           -- Privy user ID (DID)
  wallet_address VARCHAR(255) UNIQUE,    -- Primary wallet address
  email VARCHAR(255),                    -- From social login (optional)

  -- Authentication
  privy_did VARCHAR(255) UNIQUE NOT NULL, -- Privy Decentralized ID
  auth_method VARCHAR(50),                -- 'wallet', 'google', 'email', etc.
  created_at TIMESTAMP DEFAULT NOW(),
  last_login_at TIMESTAMP,

  -- KYC Status
  kyc_status VARCHAR(50) DEFAULT 'none', -- 'none', 'pending', 'approved', 'rejected'
  kyc_provider VARCHAR(50),              -- 'persona', 'synaps', etc.
  kyc_inquiry_id VARCHAR(255),           -- Persona inquiry ID
  kyc_submitted_at TIMESTAMP,
  kyc_verified_at TIMESTAMP,
  kyc_rejection_reason TEXT,

  -- Profile (from KYC)
  full_name VARCHAR(255),
  date_of_birth DATE,
  country_code VARCHAR(3),               -- ISO 3166-1 alpha-3

  -- Compliance
  sanctions_check VARCHAR(50),           -- 'passed', 'failed', 'pending'
  risk_score INTEGER,                    -- 0-100 from AML checks

  -- Feature Access Flags
  can_use_fiat_onramp BOOLEAN DEFAULT FALSE,
  can_use_fiat_offramp BOOLEAN DEFAULT FALSE,
  can_use_large_transactions BOOLEAN DEFAULT FALSE,

  -- Metadata
  updated_at TIMESTAMP DEFAULT NOW(),
  deleted_at TIMESTAMP                   -- Soft delete for GDPR
);

-- Indexes
CREATE INDEX idx_users_wallet ON users(wallet_address);
CREATE INDEX idx_users_privy_did ON users(privy_did);
CREATE INDEX idx_users_kyc_status ON users(kyc_status);
CREATE INDEX idx_users_email ON users(email);
```

### KYC Events Table (Audit Trail)

```sql
CREATE TABLE kyc_events (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) REFERENCES users(id),
  event_type VARCHAR(100) NOT NULL,      -- 'inquiry.created', 'inquiry.completed', etc.
  provider VARCHAR(50) NOT NULL,         -- 'persona', 'synaps'
  provider_event_id VARCHAR(255),        -- External event ID
  status VARCHAR(50),                    -- 'started', 'completed', 'failed'
  data JSONB,                            -- Full webhook payload
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_kyc_events_user ON kyc_events(user_id);
CREATE INDEX idx_kyc_events_type ON kyc_events(event_type);
```

---

## 🔐 Backend API Endpoints

### Authentication Endpoints

**POST /api/auth/login**
```typescript
// Verify Privy JWT token and create/update user
Request:
{
  "privyToken": "eyJhbGciOiJSUzI1NiIs..." // From Privy SDK
}

Response:
{
  "user": {
    "id": "did:privy:abc123",
    "walletAddress": "0x742d35Cc...",
    "email": "user@gmail.com",
    "kycStatus": "none",
    "canUseFiatOnramp": false
  },
  "accessToken": "your-jwt-token" // Your backend JWT
}
```

**GET /api/auth/me**
```typescript
// Get current user profile
Headers: Authorization: Bearer <token>

Response:
{
  "id": "did:privy:abc123",
  "walletAddress": "0x742d35Cc...",
  "email": "user@gmail.com",
  "kycStatus": "verified",
  "kycVerifiedAt": "2025-11-04T10:30:00Z",
  "features": {
    "cryptoEscrow": true,
    "fiatOnramp": true,
    "fiatOfframp": true,
    "largeTransactions": true
  }
}
```

### KYC Endpoints

**POST /api/kyc/initiate**
```typescript
// Create Persona inquiry and return session token
Headers: Authorization: Bearer <token>

Response:
{
  "inquiryId": "inq_abc123",
  "sessionToken": "sess_xyz789", // For Persona widget
  "status": "pending"
}
```

**GET /api/kyc/status**
```typescript
// Get current KYC status
Headers: Authorization: Bearer <token>

Response:
{
  "status": "approved", // or 'none', 'pending', 'rejected'
  "inquiryId": "inq_abc123",
  "submittedAt": "2025-11-04T10:00:00Z",
  "verifiedAt": "2025-11-04T10:30:00Z",
  "provider": "persona"
}
```

**POST /api/webhooks/persona**
```typescript
// Persona webhook endpoint (called by Persona)
// Updates user KYC status based on verification results

Request (from Persona):
{
  "data": {
    "type": "event",
    "id": "evt_abc123",
    "attributes": {
      "name": "inquiry.completed",
      "payload": {
        "data": {
          "id": "inq_abc123",
          "type": "inquiry",
          "attributes": {
            "status": "approved",
            "reference-id": "did:privy:abc123"
          }
        }
      }
    }
  }
}

Response:
{
  "received": true
}
```

---

## 🎨 Frontend Implementation

### 1. Install Dependencies

```bash
cd frontend/risk-dashboard
pnpm add @privy-io/react-auth @privy-io/wagmi-connector
pnpm add persona  # Persona SDK
```

### 2. Privy Provider Setup

**`src/providers/PrivyProvider.tsx`**

```typescript
import { PrivyProvider as BasePrivyProvider } from '@privy-io/react-auth';
import { WagmiProvider } from '@privy-io/wagmi-connector';
import { sepolia } from 'wagmi/chains';
import { polygonAmoy } from '@/config/chains';

export function PrivyProvider({ children }: { children: React.ReactNode }) {
  return (
    <BasePrivyProvider
      appId={import.meta.env.VITE_PRIVY_APP_ID}
      config={{
        // Login methods
        loginMethods: ['email', 'google', 'wallet'],

        // Appearance
        appearance: {
          theme: 'light',
          accentColor: '#3B82F6', // Blue
          logo: '/logo.png',
        },

        // Embedded wallets
        embeddedWallets: {
          createOnLogin: 'users-without-wallets', // Auto-create wallet
          noPromptOnSignature: false, // Show confirmation for transactions
        },

        // Supported chains
        supportedChains: [sepolia, polygonAmoy],

        // Callbacks
        onSuccess: (user) => {
          console.log('Privy login success:', user);
          // Optional: Send to your backend
        },
      }}
    >
      <WagmiProvider>
        {children}
      </WagmiProvider>
    </BasePrivyProvider>
  );
}
```

### 3. Authentication Hook

**`src/hooks/useAuth.ts`**

```typescript
import { usePrivy } from '@privy-io/react-auth';
import { useEffect, useState } from 'react';
import axios from 'axios';

interface User {
  id: string;
  walletAddress: string;
  email?: string;
  kycStatus: 'none' | 'pending' | 'approved' | 'rejected';
  features: {
    cryptoEscrow: boolean;
    fiatOnramp: boolean;
    fiatOfframp: boolean;
    largeTransactions: boolean;
  };
}

export function useAuth() {
  const {
    ready,
    authenticated,
    user: privyUser,
    login,
    logout: privyLogout,
    getAccessToken,
  } = usePrivy();

  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch user profile from backend
  useEffect(() => {
    if (authenticated && privyUser) {
      fetchUserProfile();
    } else {
      setUser(null);
      setLoading(false);
    }
  }, [authenticated, privyUser]);

  const fetchUserProfile = async () => {
    try {
      setLoading(true);
      const token = await getAccessToken();

      // Call your backend
      const response = await axios.post('/api/auth/login', {
        privyToken: token,
      });

      setUser(response.data.user);

      // Store backend token for API calls
      localStorage.setItem('backend_token', response.data.accessToken);
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    await privyLogout();
    localStorage.removeItem('backend_token');
    setUser(null);
  };

  return {
    ready,
    authenticated,
    user,
    privyUser,
    loading,
    login,
    logout,
    refreshProfile: fetchUserProfile,
  };
}
```

### 4. KYC Hook

**`src/hooks/useKYC.ts`**

```typescript
import { useState } from 'react';
import { Client as PersonaClient } from 'persona';
import axios from 'axios';
import { useAuth } from './useAuth';

export function useKYC() {
  const { user, refreshProfile } = useAuth();
  const [isVerifying, setIsVerifying] = useState(false);

  const initiateKYC = async () => {
    try {
      setIsVerifying(true);

      // Get session token from backend
      const token = localStorage.getItem('backend_token');
      const response = await axios.post(
        '/api/kyc/initiate',
        {},
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const { inquiryId, sessionToken } = response.data;

      // Launch Persona widget
      const client = new PersonaClient({
        templateId: import.meta.env.VITE_PERSONA_TEMPLATE_ID,
        environmentId: import.meta.env.VITE_PERSONA_ENVIRONMENT_ID,
        inquiryId,
        sessionToken,

        onLoad: () => {
          console.log('Persona widget loaded');
        },

        onComplete: ({ inquiryId, status }) => {
          console.log('KYC completed:', inquiryId, status);
          // Refresh user profile to get updated KYC status
          setTimeout(() => refreshProfile(), 2000);
        },

        onCancel: () => {
          console.log('KYC cancelled');
          setIsVerifying(false);
        },

        onError: (error) => {
          console.error('KYC error:', error);
          setIsVerifying(false);
        },
      });

      client.open();
    } catch (error) {
      console.error('Failed to initiate KYC:', error);
      setIsVerifying(false);
    }
  };

  const checkKYCStatus = async () => {
    try {
      const token = localStorage.getItem('backend_token');
      const response = await axios.get('/api/kyc/status', {
        headers: { Authorization: `Bearer ${token}` },
      });

      return response.data;
    } catch (error) {
      console.error('Failed to check KYC status:', error);
      return null;
    }
  };

  return {
    kycStatus: user?.kycStatus || 'none',
    isVerifying,
    initiateKYC,
    checkKYCStatus,
    canUseFiat: user?.features.fiatOnramp || false,
  };
}
```

### 5. Protected Feature Component

**`src/components/ProtectedFeature.tsx`**

```typescript
import { useKYC } from '@/hooks/useKYC';
import { ReactNode } from 'react';

interface ProtectedFeatureProps {
  children: ReactNode;
  requiresKYC?: boolean;
  featureName?: string;
}

export function ProtectedFeature({
  children,
  requiresKYC = false,
  featureName = 'this feature',
}: ProtectedFeatureProps) {
  const { kycStatus, initiateKYC, canUseFiat } = useKYC();

  if (!requiresKYC) {
    return <>{children}</>;
  }

  if (kycStatus === 'approved' && canUseFiat) {
    return <>{children}</>;
  }

  if (kycStatus === 'pending') {
    return (
      <div className="p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
        <h3 className="text-lg font-semibold text-yellow-900 mb-2">
          Verification Pending
        </h3>
        <p className="text-yellow-800">
          Your identity verification is being reviewed. This usually takes 5-10 minutes.
          We'll notify you once it's complete.
        </p>
      </div>
    );
  }

  if (kycStatus === 'rejected') {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <h3 className="text-lg font-semibold text-red-900 mb-2">
          Verification Failed
        </h3>
        <p className="text-red-800 mb-4">
          We were unable to verify your identity. Please contact support for assistance.
        </p>
        <button
          onClick={initiateKYC}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  // kycStatus === 'none'
  return (
    <div className="p-6 bg-blue-50 border border-blue-200 rounded-lg">
      <h3 className="text-lg font-semibold text-blue-900 mb-2">
        Identity Verification Required
      </h3>
      <p className="text-blue-800 mb-4">
        To use {featureName}, you need to complete identity verification.
        This is required by law for fiat currency transactions.
      </p>
      <div className="space-y-2 mb-4 text-sm text-blue-700">
        <p>✓ Takes 5-10 minutes</p>
        <p>✓ Government-issued ID required</p>
        <p>✓ Your data is encrypted and secure</p>
      </div>
      <button
        onClick={initiateKYC}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Verify Identity
      </button>
    </div>
  );
}
```

### 6. Usage in Fiat Gateway Page

**`src/pages/fiat/OnRamp.tsx`**

```typescript
import { ProtectedFeature } from '@/components/ProtectedFeature';

export default function FiatOnRamp() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Fiat On-Ramp</h1>

      <ProtectedFeature
        requiresKYC={true}
        featureName="fiat deposits"
      >
        {/* This only shows if user is KYC verified */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Deposit USD</h2>

          {/* Circle on-ramp widget */}
          <form>
            <label>Amount (USD)</label>
            <input type="number" placeholder="100.00" />

            <label>Payment Method</label>
            <select>
              <option>Bank Transfer (ACH)</option>
              <option>Debit Card</option>
              <option>Wire Transfer</option>
            </select>

            <button type="submit">Continue</button>
          </form>
        </div>
      </ProtectedFeature>
    </div>
  );
}
```

---

## 🔧 Backend Implementation

### 1. Environment Variables

**`.env`**
```bash
# Privy
PRIVY_APP_ID=your-privy-app-id
PRIVY_APP_SECRET=your-privy-app-secret
PRIVY_VERIFICATION_KEY=your-verification-key

# Persona
PERSONA_API_KEY=your-persona-api-key
PERSONA_TEMPLATE_ID=itmpl_abc123
PERSONA_ENVIRONMENT_ID=env_abc123
PERSONA_WEBHOOK_SECRET=your-webhook-secret

# Database
DATABASE_URL=postgresql://user:pass@host:5432/fusion_prime
```

### 2. Privy JWT Verification (Middleware)

**`services/auth/middleware/verify_privy.py`**

```python
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import requests
import os

security = HTTPBearer()

# Cache Privy public keys (refresh every hour)
_privy_public_keys = None

def get_privy_public_keys():
    global _privy_public_keys
    if _privy_public_keys is None:
        # Fetch Privy's public keys (JWKS)
        response = requests.get("https://auth.privy.io/.well-known/jwks.json")
        _privy_public_keys = response.json()
    return _privy_public_keys

async def verify_privy_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """
    Verify Privy JWT token and return user claims
    """
    try:
        token = credentials.credentials

        # Get public keys
        jwks = get_privy_public_keys()

        # Decode JWT (Privy uses RS256)
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=os.getenv("PRIVY_APP_ID"),
            issuer="https://auth.privy.io",
        )

        return claims
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
```

### 3. User Service

**`services/auth/app/services/user_service.py`**

```python
from sqlalchemy.orm import Session
from app.models import User
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_user(self, privy_claims: dict) -> User:
        """
        Get existing user or create new one from Privy claims
        """
        privy_did = privy_claims.get("sub")  # Privy user ID

        # Check if user exists
        user = self.db.query(User).filter(User.privy_did == privy_did).first()

        if user:
            # Update last login
            user.last_login_at = datetime.utcnow()
            self.db.commit()
            return user

        # Create new user
        user = User(
            id=privy_did,
            privy_did=privy_did,
            wallet_address=privy_claims.get("wallet_address"),
            email=privy_claims.get("email"),
            auth_method=privy_claims.get("linked_accounts", [{}])[0].get("type"),
            kyc_status="none",
            can_use_fiat_onramp=False,
            can_use_fiat_offramp=False,
            can_use_large_transactions=False,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info(f"Created new user: {privy_did}")
        return user

    def update_kyc_status(
        self,
        user_id: str,
        status: str,
        inquiry_id: Optional[str] = None,
        full_name: Optional[str] = None,
        country_code: Optional[str] = None,
    ) -> User:
        """
        Update user's KYC status
        """
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user:
            raise ValueError(f"User not found: {user_id}")

        user.kyc_status = status
        user.kyc_inquiry_id = inquiry_id

        if status == "approved":
            user.kyc_verified_at = datetime.utcnow()
            user.can_use_fiat_onramp = True
            user.can_use_fiat_offramp = True
            user.can_use_large_transactions = True

            if full_name:
                user.full_name = full_name
            if country_code:
                user.country_code = country_code

        self.db.commit()
        self.db.refresh(user)

        logger.info(f"Updated KYC status for user {user_id}: {status}")
        return user
```

### 4. KYC Service

**`services/auth/app/services/kyc_service.py`**

```python
import requests
import os
from typing import Dict

class PersonaKYCService:
    def __init__(self):
        self.api_key = os.getenv("PERSONA_API_KEY")
        self.base_url = "https://withpersona.com/api/v1"
        self.template_id = os.getenv("PERSONA_TEMPLATE_ID")

    def create_inquiry(self, user_id: str, user_email: str) -> Dict:
        """
        Create a Persona inquiry for user verification
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "data": {
                "type": "inquiry",
                "attributes": {
                    "inquiry-template-id": self.template_id,
                    "reference-id": user_id,  # Your user ID
                    "email-address": user_email,
                },
            },
        }

        response = requests.post(
            f"{self.base_url}/inquiries",
            json=payload,
            headers=headers,
        )

        response.raise_for_status()
        data = response.json()

        return {
            "inquiry_id": data["data"]["id"],
            "session_token": data["data"]["attributes"]["session-token"],
            "status": data["data"]["attributes"]["status"],
        }

    def get_inquiry_status(self, inquiry_id: str) -> Dict:
        """
        Get current status of an inquiry
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        response = requests.get(
            f"{self.base_url}/inquiries/{inquiry_id}",
            headers=headers,
        )

        response.raise_for_status()
        data = response.json()

        return {
            "status": data["data"]["attributes"]["status"],
            "name": data["data"]["attributes"].get("name-first"),
            "country": data["data"]["attributes"].get("address-country-code"),
        }
```

### 5. API Endpoints

**`services/auth/app/routes/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.middleware.verify_privy import verify_privy_token
from app.services.user_service import UserService
from app.database import get_db
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    privyToken: str

@router.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Verify Privy token and create/update user
    """
    try:
        # Verify Privy token
        claims = await verify_privy_token(request.privyToken)

        # Get or create user
        user_service = UserService(db)
        user = user_service.get_or_create_user(claims)

        # Create your own JWT for API calls (optional)
        access_token = create_access_token(user.id)

        return {
            "user": {
                "id": user.id,
                "walletAddress": user.wallet_address,
                "email": user.email,
                "kycStatus": user.kyc_status,
                "canUseFiatOnramp": user.can_use_fiat_onramp,
            },
            "accessToken": access_token,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/me")
async def get_me(
    claims: dict = Depends(verify_privy_token),
    db: Session = Depends(get_db),
):
    """
    Get current user profile
    """
    user_service = UserService(db)
    user = user_service.get_or_create_user(claims)

    return {
        "id": user.id,
        "walletAddress": user.wallet_address,
        "email": user.email,
        "kycStatus": user.kyc_status,
        "kycVerifiedAt": user.kyc_verified_at,
        "features": {
            "cryptoEscrow": True,  # Always available after auth
            "fiatOnramp": user.can_use_fiat_onramp,
            "fiatOfframp": user.can_use_fiat_offramp,
            "largeTransactions": user.can_use_large_transactions,
        },
    }
```

**`services/auth/app/routes/kyc.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.middleware.verify_privy import verify_privy_token
from app.services.kyc_service import PersonaKYCService
from app.services.user_service import UserService
from app.database import get_db

router = APIRouter(prefix="/kyc", tags=["kyc"])

@router.post("/initiate")
async def initiate_kyc(
    claims: dict = Depends(verify_privy_token),
    db: Session = Depends(get_db),
):
    """
    Create Persona inquiry for KYC verification
    """
    user_service = UserService(db)
    user = user_service.get_or_create_user(claims)

    # Check if already verified
    if user.kyc_status == "approved":
        raise HTTPException(status_code=400, detail="User already verified")

    # Create Persona inquiry
    kyc_service = PersonaKYCService()
    inquiry = kyc_service.create_inquiry(user.id, user.email or "")

    # Update user status to pending
    user.kyc_status = "pending"
    user.kyc_inquiry_id = inquiry["inquiry_id"]
    user.kyc_submitted_at = datetime.utcnow()
    db.commit()

    return {
        "inquiryId": inquiry["inquiry_id"],
        "sessionToken": inquiry["session_token"],
        "status": "pending",
    }

@router.get("/status")
async def get_kyc_status(
    claims: dict = Depends(verify_privy_token),
    db: Session = Depends(get_db),
):
    """
    Get current KYC status
    """
    user_service = UserService(db)
    user = user_service.get_or_create_user(claims)

    return {
        "status": user.kyc_status,
        "inquiryId": user.kyc_inquiry_id,
        "submittedAt": user.kyc_submitted_at,
        "verifiedAt": user.kyc_verified_at,
        "provider": user.kyc_provider or "persona",
    }
```

### 6. Persona Webhook Handler

**`services/auth/app/routes/webhooks.py`**

```python
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.database import get_db
import hmac
import hashlib
import os
import logging

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

def verify_persona_webhook(payload: bytes, signature: str) -> bool:
    """
    Verify Persona webhook signature
    """
    secret = os.getenv("PERSONA_WEBHOOK_SECRET").encode()
    expected_signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected_signature}", signature)

@router.post("/persona")
async def persona_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle Persona webhook events
    """
    # Get raw body for signature verification
    payload = await request.body()
    signature = request.headers.get("Persona-Signature")

    # Verify signature
    if not verify_persona_webhook(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON
    data = await request.json()

    # Extract event data
    event_type = data["data"]["attributes"]["name"]
    event_payload = data["data"]["attributes"]["payload"]["data"]

    inquiry_id = event_payload["id"]
    inquiry_attrs = event_payload["attributes"]
    user_id = inquiry_attrs.get("reference-id")  # Our user ID
    status = inquiry_attrs.get("status")

    logger.info(f"Persona webhook: {event_type}, inquiry: {inquiry_id}, status: {status}")

    # Handle different event types
    if event_type == "inquiry.completed":
        user_service = UserService(db)

        # Map Persona status to our status
        if status == "approved":
            user_service.update_kyc_status(
                user_id=user_id,
                status="approved",
                inquiry_id=inquiry_id,
                full_name=inquiry_attrs.get("name-first", "") + " " + inquiry_attrs.get("name-last", ""),
                country_code=inquiry_attrs.get("address-country-code"),
            )
        elif status in ["declined", "failed"]:
            user_service.update_kyc_status(
                user_id=user_id,
                status="rejected",
                inquiry_id=inquiry_id,
            )

    # Log event for audit trail
    # (Insert into kyc_events table)

    return {"received": True}
```

---

## 🔄 Complete User Flow

### Flow 1: New User Signs Up

```
1. User visits app
   → Clicks "Sign in"

2. Privy modal opens
   → User selects "Continue with Google"
   → Google auth popup
   → User approves

3. Privy creates account
   → Returns JWT token
   → Frontend receives: { user: { id, email }, accessToken }

4. Frontend calls /api/auth/login
   → Sends Privy JWT
   → Backend verifies JWT
   → Backend creates User in database:
      - privy_did: "did:privy:abc123"
      - email: "user@gmail.com"
      - wallet_address: "0x..." (embedded wallet)
      - kyc_status: "none"
   → Returns backend JWT

5. User sees dashboard
   → Can use crypto features immediately ✅
   → Cannot use fiat features (KYC required)
```

### Flow 2: User Initiates KYC

```
1. User clicks "Deposit USD"

2. App shows ProtectedFeature component
   → Checks: user.kycStatus === "approved"?
   → NO → Shows "Verify Identity" button

3. User clicks "Verify Identity"

4. Frontend calls /api/kyc/initiate
   → Backend creates Persona inquiry
   → Returns: { inquiryId, sessionToken }

5. Frontend launches Persona widget
   → User uploads ID (passport/driver's license)
   → User takes selfie
   → Persona verifies documents (30 seconds - 10 minutes)

6. Persona completes verification
   → Sends webhook to /api/webhooks/persona
   → Webhook updates User:
      - kyc_status: "approved"
      - can_use_fiat_onramp: true
      - can_use_fiat_offramp: true

7. Frontend refreshes user profile
   → Now shows: user.features.fiatOnramp = true
   → ProtectedFeature shows fiat UI ✅

8. User can now deposit/withdraw fiat 🎉
```

---

## 🎯 Key Integration Points

### 1. **Privy → Your Backend**
- Frontend gets Privy JWT
- Frontend sends to `/api/auth/login`
- Backend verifies JWT using Privy's public keys
- Backend creates/updates user record

### 2. **Your Backend → Persona**
- User initiates KYC
- Backend calls Persona API to create inquiry
- Backend returns session token to frontend
- Frontend launches Persona widget

### 3. **Persona → Your Backend**
- User completes KYC in widget
- Persona sends webhook to your backend
- Backend updates user KYC status
- User can now access gated features

### 4. **Data Association**
```
Privy User ID (DID) = Your User ID = Persona Reference ID

Example:
- Privy: did:privy:abc123xyz
- Your DB: user.id = "did:privy:abc123xyz"
- Persona: inquiry.reference_id = "did:privy:abc123xyz"

All connected by same ID! ✅
```

---

## 📊 Summary

**Architecture**: Privy (auth) + Persona (KYC) + Your Backend (orchestration)

**Data Flow**:
1. User authenticates via Privy → Gets JWT
2. Frontend calls your backend with Privy JWT
3. Backend verifies JWT → Creates user record
4. User initiates KYC → Backend creates Persona inquiry
5. User completes KYC → Persona webhook updates user
6. User can access fiat features ✅

**Timeline to Implement**:
- Privy integration: 1-2 days
- KYC integration: 1-2 days
- Testing: 1 day
- **Total**: 3-5 days

**Cost**:
- Privy: Free (< 1,000 MAU)
- Persona: $2 per verification (free sandbox)
- **Total for early stage**: $0!

---

Would you like me to start implementing this architecture? I can begin with the Privy authentication setup! 🚀
