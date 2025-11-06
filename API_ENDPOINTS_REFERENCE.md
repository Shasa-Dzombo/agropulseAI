# 📚 API Endpoints Quick Reference

**AgroPulse REST API v1**  
Base URL: `/api/v1`

---

## 👤 Users API (`/users`)

### User Management
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/users` | List users with pagination | ✓ |
| GET | `/users/search?q={query}` | Search users by name/email/phone | ✓ |
| GET | `/users/statistics` | Admin statistics dashboard | Admin |
| GET | `/users/{user_id}` | Get user details | ✓ |
| PATCH | `/users/{user_id}` | Update user profile | Owner/Admin |
| DELETE | `/users/{user_id}` | Delete user (soft/hard) | Owner/Admin |

### Related Resources
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/users/{user_id}/farms` | Get user's farms | ✓ |
| GET | `/users/{user_id}/referrals` | Get referral list | Owner/Admin |
| POST | `/users/{user_id}/subscription` | Update subscription | Owner/Admin |
| POST | `/users/{user_id}/avatar` | Upload avatar | Owner |

**Total**: 13 endpoints

---

## 🚜 Farms API (`/farms`)

### Farm Management
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/farms` | List farms with filters | ✓ |
| POST | `/farms` | Create new farm | ✓ |
| GET | `/farms/nearby` | Find farms by location (PostGIS) | ✓ |
| GET | `/farms/search?q={query}` | Search farms | ✓ |
| GET | `/farms/statistics` | Farm statistics | Expert |
| GET | `/farms/{farm_id}` | Get farm details | ✓ |
| PATCH | `/farms/{farm_id}` | Update farm | Owner/Admin |
| DELETE | `/farms/{farm_id}` | Delete farm | Owner/Admin |

### Farm Resources
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/farms/{farm_id}/fields` | List farm fields | ✓ |
| POST | `/farms/{farm_id}/fields` | Create field | Owner |
| GET | `/farms/{farm_id}/plantings` | Get crop plantings | ✓ |
| POST | `/farms/{farm_id}/verify` | Verify farm | Expert |

**Total**: 15 endpoints

### Geographic Queries (PostGIS)
```bash
# Find farms within 10km radius
GET /farms/nearby?latitude=-1.2864&longitude=36.8172&radius_km=10

# Parameters:
- latitude: -90 to 90
- longitude: -180 to 180
- radius_km: 0.1 to 100 (default: 10)
- limit: 1 to 100 (default: 50)
```

---

## 🤝 Chamas API (`/chamas`)

### Chama Management
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/chamas` | List chamas with filters | ✓ |
| POST | `/chamas` | Create new chama | ✓ |
| GET | `/chamas/{chama_id}` | Get chama details | ✓ |
| PATCH | `/chamas/{chama_id}` | Update chama | Leader |
| DELETE | `/chamas/{chama_id}` | Delete chama | Founder/Admin |

### Membership
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/chamas/{chama_id}/join` | Join chama | ✓ |
| POST | `/chamas/{chama_id}/leave` | Leave chama | Member |
| GET | `/chamas/{chama_id}/members` | List members | Member |
| POST | `/chamas/{chama_id}/members/{user_id}/role` | Update role | Leader |

### Financial Operations
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/chamas/{chama_id}/transactions` | Record transaction | Member |
| GET | `/chamas/{chama_id}/transactions` | List transactions | Member |
| GET | `/chamas/{chama_id}/financial-summary` | Financial dashboard | Member |

### Loan Management
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/chamas/{chama_id}/loans` | Request loan | Member |
| GET | `/chamas/{chama_id}/loans` | List loans | Member |
| GET | `/chamas/{chama_id}/loans/{loan_id}` | Get loan details | Member |
| POST | `/chamas/{chama_id}/loans/{loan_id}/approve` | Approve loan | Leader |
| POST | `/chamas/{chama_id}/loans/{loan_id}/reject` | Reject loan | Leader |
| POST | `/chamas/{chama_id}/loans/{loan_id}/repay` | Make repayment | Borrower |

### Meetings
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/chamas/{chama_id}/meetings` | Schedule meeting | Leader |
| GET | `/chamas/{chama_id}/meetings` | List meetings | Member |

**Total**: 21 endpoints

---

## 🎯 Common Parameters

### Pagination
```bash
?page=1&page_size=20
```
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

### Filtering
```bash
# Users
?role=farmer&county=Nairobi&verified=true

# Farms
?county=Kiambu&crop=maize&min_size=5&max_size=50&organic_only=true

# Chamas
?chama_type=savings&active_only=true&my_chamas=true
```

### Search
```bash
?q=search_term
```

---

## 🔐 Authentication

All endpoints require authentication via JWT token:

```http
Authorization: Bearer <your_jwt_token>
```

### Role-Based Access
- **User**: Standard access to own resources
- **Farmer**: Farm management capabilities
- **Agronomist**: Expert review and verification
- **Admin**: Full system access
- **Superuser**: System administration

---

## 📊 Response Formats

### Success Response
```json
{
  "id": 123,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Resource name",
  "created_at": "2024-12-01T10:30:00Z"
}
```

### Paginated Response
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8
}
```

### Error Response
```json
{
  "detail": "Error message description"
}
```

---

## 🚀 Example Requests

### Create Farm
```bash
POST /api/v1/farms
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Green Valley Farm",
  "latitude": -1.2864,
  "longitude": 36.8172,
  "size_acres": 25.5,
  "county": "Kiambu",
  "primary_crop": "maize",
  "soil_type": "clay loam",
  "has_irrigation": true
}
```

### Request Chama Loan
```bash
POST /api/v1/chamas/123/loans
Content-Type: application/json
Authorization: Bearer <token>

{
  "amount": 50000,
  "purpose": "Purchase seeds and fertilizer for planting season",
  "repayment_period_months": 6,
  "guarantor_ids": [45, 67],
  "collateral_description": "Farm equipment and harvest"
}
```

### Find Nearby Farms
```bash
GET /api/v1/farms/nearby?latitude=-1.2864&longitude=36.8172&radius_km=15
Authorization: Bearer <token>

# Returns farms within 15km radius
```

---

## 📈 Status Codes

- `200 OK`: Successful GET/PATCH/DELETE
- `201 Created`: Successful POST
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing/invalid token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource doesn't exist
- `422 Unprocessable Entity`: Validation error

---

## 🎨 Response Models

### User Types
- `UserListResponse`: Basic user info for lists
- `UserDetailResponse`: Complete user profile
- `PaginatedUsersResponse`: Paginated user list

### Farm Types
- `FarmListResponse`: Basic farm info
- `FarmDetailResponse`: Complete farm data
- `FieldResponse`: Field information

### Chama Types
- `ChamaListResponse`: Basic chama info
- `ChamaDetailResponse`: Complete chama data
- `MemberResponse`: Member information
- `LoanResponse`: Loan details
- `TransactionResponse`: Transaction record
- `FinancialSummaryResponse`: Financial dashboard

---

## 🔧 Integration Examples

### Python (requests)
```python
import requests

# Get nearby farms
response = requests.get(
    "https://api.agropulse.com/api/v1/farms/nearby",
    params={
        "latitude": -1.2864,
        "longitude": 36.8172,
        "radius_km": 10
    },
    headers={"Authorization": f"Bearer {token}"}
)
farms = response.json()
```

### JavaScript (fetch)
```javascript
// Create chama transaction
const response = await fetch('/api/v1/chamas/123/transactions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    transaction_type: 'contribution',
    amount: 5000,
    payment_method: 'mpesa',
    reference_number: 'MPESA123456'
  })
});
const transaction = await response.json();
```

### cURL
```bash
# Get user's farms
curl -X GET "https://api.agropulse.com/api/v1/users/123/farms" \
  -H "Authorization: Bearer <token>"
```

---

**Total Endpoints**: 49 production-ready APIs  
**Version**: v1  
**Documentation**: Auto-generated via FastAPI (visit `/docs` for Swagger UI)
