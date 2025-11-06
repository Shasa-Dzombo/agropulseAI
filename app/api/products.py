"""
🛒 Products API

FastAPI endpoints for agricultural product catalog, supplier management, and marketplace.

Endpoints:
- GET /products - List products
- POST /products - Create product
- GET /products/{product_id} - Get product details
- PATCH /products/{product_id} - Update product
- DELETE /products/{product_id} - Delete product
- GET /products/search - Search products
- GET /products/categories - List categories
- GET /suppliers - List suppliers
- POST /suppliers - Create supplier
- GET /suppliers/{supplier_id} - Get supplier details
- PATCH /suppliers/{supplier_id} - Update supplier
- POST /products/{product_id}/review - Add product review
- GET /products/{product_id}/reviews - Get product reviews

Author: AgroPulse Engineering Team
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.db_config import get_production_db_dependency
from app.api.auth import get_current_user


router = APIRouter(prefix="/products", tags=["Products"])
suppliers_router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ProductCreateRequest(BaseModel):
    """Create product request."""
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    category: str = Field(..., max_length=100)
    subcategory: Optional[str] = None
    supplier_id: Optional[int] = None
    sku: Optional[str] = None
    
    # Pricing
    price: Decimal = Field(..., gt=0)
    currency: str = Field("KES", max_length=3)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    
    # Stock
    stock_quantity: int = Field(0, ge=0)
    unit: str = Field(..., max_length=50)
    min_order_quantity: int = Field(1, ge=1)
    
    # Details
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    organic_certified: bool = False
    specifications: Optional[dict] = None
    image_urls: Optional[List[str]] = None


class ProductUpdateRequest(BaseModel):
    """Update product request."""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    stock_quantity: Optional[int] = Field(None, ge=0)
    is_available: Optional[bool] = None
    specifications: Optional[dict] = None


class ProductListResponse(BaseModel):
    """Product list response."""
    id: int
    uuid: str
    name: str
    category: str
    price: Decimal
    discount_percentage: Optional[Decimal]
    final_price: Decimal
    currency: str
    stock_quantity: int
    unit: str
    is_available: bool
    rating: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProductDetailResponse(BaseModel):
    """Detailed product response."""
    id: int
    uuid: str
    supplier_id: Optional[int]
    name: str
    description: Optional[str]
    category: str
    subcategory: Optional[str]
    sku: Optional[str]
    
    # Pricing
    price: Decimal
    currency: str
    discount_percentage: Optional[Decimal]
    final_price: Decimal
    
    # Stock
    stock_quantity: int
    unit: str
    min_order_quantity: int
    
    # Details
    brand: Optional[str]
    manufacturer: Optional[str]
    organic_certified: bool
    specifications: Optional[dict]
    
    # Media
    image_urls: Optional[List[str]]
    
    # Ratings
    rating: Optional[float]
    review_count: int
    
    # Status
    is_available: bool
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SupplierCreateRequest(BaseModel):
    """Create supplier request."""
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    county: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)


class SupplierUpdateRequest(BaseModel):
    """Update supplier request."""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    is_verified: Optional[bool] = None


class SupplierListResponse(BaseModel):
    """Supplier list response."""
    id: int
    uuid: str
    name: str
    county: Optional[str]
    rating: Optional[float]
    product_count: int
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class SupplierDetailResponse(BaseModel):
    """Detailed supplier response."""
    id: int
    uuid: str
    name: str
    description: Optional[str]
    contact_person: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    county: Optional[str]
    website: Optional[str]
    rating: Optional[float]
    product_count: int
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductReviewRequest(BaseModel):
    """Product review request."""
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: str = Field(..., min_length=10)
    would_recommend: bool = True


class ProductReviewResponse(BaseModel):
    """Product review response."""
    id: int
    uuid: str
    product_id: int
    user_id: int
    username: str
    rating: int
    title: Optional[str]
    comment: str
    would_recommend: bool
    helpful_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaginatedProductsResponse(BaseModel):
    """Paginated products response."""
    items: List[ProductListResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CategoryResponse(BaseModel):
    """Product category response."""
    name: str
    product_count: int
    subcategories: List[str]


# ============================================================================
# PRODUCT ENDPOINTS
# ============================================================================

@router.get("", response_model=PaginatedProductsResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    available_only: bool = True,
    organic_only: bool = False,
    supplier_id: Optional[int] = None,
    sort_by: str = Query("created_at", pattern="^(price|rating|name|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List products with pagination and filters.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **category**: Filter by category (optional)
    - **min_price**: Minimum price (optional)
    - **max_price**: Maximum price (optional)
    - **available_only**: Show only available products (default: true)
    - **organic_only**: Show only organic certified (default: false)
    - **supplier_id**: Filter by supplier (optional)
    - **sort_by**: Sort field (price, rating, name, created_at)
    - **sort_order**: Sort order (asc, desc)
    """
    from app.models.database import Product
    
    query = db.query(Product).filter(Product.is_deleted == False)
    
    if available_only:
        query = query.filter(Product.is_available == True)
    
    if organic_only:
        query = query.filter(Product.organic_certified == True)
    
    if category:
        query = query.filter(Product.category == category)
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    if supplier_id:
        query = query.filter(Product.supplier_id == supplier_id)
    
    # Sorting
    sort_field = getattr(Product, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field.asc())
    
    total = query.count()
    
    skip = (page - 1) * page_size
    products = query.offset(skip).limit(page_size).all()
    
    return PaginatedProductsResponse(
        items=products,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=ProductDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    request: ProductCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Create new product.
    
    Requires admin role or supplier account.
    """
    from app.models.database import Product
    
    if current_user['role'] not in ['admin', 'supplier', 'superuser']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or supplier access required"
        )
    
    # Calculate final price
    final_price = request.price
    if request.discount_percentage:
        final_price = request.price * (1 - request.discount_percentage / 100)
    
    product = Product(
        supplier_id=request.supplier_id,
        name=request.name,
        description=request.description,
        category=request.category,
        subcategory=request.subcategory,
        sku=request.sku,
        price=request.price,
        currency=request.currency,
        discount_percentage=request.discount_percentage,
        final_price=final_price,
        stock_quantity=request.stock_quantity,
        unit=request.unit,
        min_order_quantity=request.min_order_quantity,
        brand=request.brand,
        manufacturer=request.manufacturer,
        organic_certified=request.organic_certified,
        specifications=request.specifications,
        image_urls=request.image_urls,
        is_available=True,
        review_count=0
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return product


@router.get("/search", response_model=List[ProductListResponse])
async def search_products(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Search products by name or description.
    
    - **q**: Search query (min 2 characters)
    - **limit**: Maximum results (default: 20, max: 100)
    """
    from app.models.database import Product
    
    search_term = f"%{q}%"
    products = db.query(Product).filter(
        Product.is_deleted == False,
        (Product.name.ilike(search_term) | Product.description.ilike(search_term))
    ).limit(limit).all()
    
    return products


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List product categories with counts.
    """
    from app.models.database import Product
    from sqlalchemy import func
    
    # Get categories with counts
    categories = db.query(
        Product.category,
        func.count(Product.id).label('product_count')
    ).filter(
        Product.is_deleted == False
    ).group_by(Product.category).all()
    
    results = []
    for cat, count in categories:
        # Get subcategories
        subcats = db.query(Product.subcategory).filter(
            Product.category == cat,
            Product.subcategory.isnot(None),
            Product.is_deleted == False
        ).distinct().all()
        
        results.append(CategoryResponse(
            name=cat,
            product_count=count,
            subcategories=[sc[0] for sc in subcats if sc[0]]
        ))
    
    return results


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get product details by ID.
    """
    from app.models.database import Product
    
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_deleted == False
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return product


@router.patch("/{product_id}", response_model=ProductDetailResponse)
async def update_product(
    product_id: int,
    request: ProductUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Update product details.
    
    Requires admin role or supplier ownership.
    """
    from app.models.database import Product
    
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_deleted == False
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    if current_user['role'] not in ['admin', 'superuser']:
        # Check supplier ownership
        if not product.supplier_id or product.supplier_id != current_user.get('supplier_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Update fields
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    for key, value in update_data.items():
        setattr(product, key, value)
    
    # Recalculate final price if needed
    if 'price' in update_data or 'discount_percentage' in update_data:
        product.final_price = product.price
        if product.discount_percentage:
            product.final_price = product.price * (1 - product.discount_percentage / 100)
    
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Delete product (soft delete).
    
    Requires admin role or supplier ownership.
    """
    from app.models.database import Product
    
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_deleted == False
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    if current_user['role'] not in ['admin', 'superuser']:
        if not product.supplier_id or product.supplier_id != current_user.get('supplier_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    product.is_deleted = True
    product.deleted_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Product deleted successfully"}


@router.post("/{product_id}/review", response_model=ProductReviewResponse, status_code=status.HTTP_201_CREATED)
async def add_product_review(
    product_id: int,
    request: ProductReviewRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Add product review.
    
    - **rating**: Rating 1-5 (required)
    - **title**: Review title (optional)
    - **comment**: Review comment (required, min 10 chars)
    - **would_recommend**: Would recommend (default: true)
    """
    from app.models.database import Product, ProductReview, User
    
    # Verify product exists
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_deleted == False
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if user already reviewed
    existing = db.query(ProductReview).filter(
        ProductReview.product_id == product_id,
        ProductReview.user_id == current_user['id']
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this product"
        )
    
    # Create review
    review = ProductReview(
        product_id=product_id,
        user_id=current_user['id'],
        rating=request.rating,
        title=request.title,
        comment=request.comment,
        would_recommend=request.would_recommend,
        helpful_count=0
    )
    
    db.add(review)
    
    # Update product rating
    from sqlalchemy import func
    avg_rating = db.query(func.avg(ProductReview.rating)).filter(
        ProductReview.product_id == product_id
    ).scalar()
    
    product.rating = float(avg_rating) if avg_rating else request.rating
    product.review_count += 1
    
    db.commit()
    db.refresh(review)
    
    # Add username
    user = db.query(User).filter(User.id == current_user['id']).first()
    review.username = user.username if user else "Anonymous"
    
    return review


@router.get("/{product_id}/reviews", response_model=List[ProductReviewResponse])
async def get_product_reviews(
    product_id: int,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get product reviews.
    
    - **limit**: Maximum results (default: 50, max: 100)
    """
    from app.models.database import ProductReview, User
    
    reviews = db.query(
        ProductReview.id,
        ProductReview.uuid,
        ProductReview.product_id,
        ProductReview.user_id,
        User.username,
        ProductReview.rating,
        ProductReview.title,
        ProductReview.comment,
        ProductReview.would_recommend,
        ProductReview.helpful_count,
        ProductReview.created_at
    ).join(User, ProductReview.user_id == User.id).filter(
        ProductReview.product_id == product_id
    ).order_by(ProductReview.created_at.desc()).limit(limit).all()
    
    return [
        ProductReviewResponse(
            id=r[0],
            uuid=r[1],
            product_id=r[2],
            user_id=r[3],
            username=r[4],
            rating=r[5],
            title=r[6],
            comment=r[7],
            would_recommend=r[8],
            helpful_count=r[9],
            created_at=r[10]
        )
        for r in reviews
    ]


# ============================================================================
# SUPPLIER ENDPOINTS
# ============================================================================

@suppliers_router.get("", response_model=List[SupplierListResponse])
async def list_suppliers(
    county: Optional[str] = None,
    verified_only: bool = False,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List suppliers with filters.
    
    - **county**: Filter by county (optional)
    - **verified_only**: Show only verified suppliers (default: false)
    - **limit**: Maximum results (default: 50, max: 100)
    """
    from app.models.database import Supplier, Product
    from sqlalchemy import func
    
    query = db.query(
        Supplier.id,
        Supplier.uuid,
        Supplier.name,
        Supplier.county,
        Supplier.rating,
        func.count(Product.id).label('product_count'),
        Supplier.is_verified,
        Supplier.created_at
    ).outerjoin(Product, Supplier.id == Product.supplier_id).filter(
        Supplier.is_deleted == False
    ).group_by(
        Supplier.id,
        Supplier.uuid,
        Supplier.name,
        Supplier.county,
        Supplier.rating,
        Supplier.is_verified,
        Supplier.created_at
    )
    
    if county:
        query = query.filter(Supplier.county == county)
    
    if verified_only:
        query = query.filter(Supplier.is_verified == True)
    
    suppliers = query.limit(limit).all()
    
    return [
        SupplierListResponse(
            id=s[0],
            uuid=s[1],
            name=s[2],
            county=s[3],
            rating=s[4],
            product_count=s[5],
            is_verified=s[6],
            created_at=s[7]
        )
        for s in suppliers
    ]


@suppliers_router.post("", response_model=SupplierDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    request: SupplierCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Create new supplier.
    
    Requires admin role.
    """
    from app.models.database import Supplier
    
    if current_user['role'] not in ['admin', 'superuser']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    supplier = Supplier(
        name=request.name,
        description=request.description,
        contact_person=request.contact_person,
        email=request.email,
        phone=request.phone,
        address=request.address,
        county=request.county,
        website=request.website,
        rating=request.rating,
        product_count=0,
        is_verified=False
    )
    
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    
    return supplier


@suppliers_router.get("/{supplier_id}", response_model=SupplierDetailResponse)
async def get_supplier(
    supplier_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get supplier details by ID.
    """
    from app.models.database import Supplier
    
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.is_deleted == False
    ).first()
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    return supplier


@suppliers_router.patch("/{supplier_id}", response_model=SupplierDetailResponse)
async def update_supplier(
    supplier_id: int,
    request: SupplierUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Update supplier details.
    
    Requires admin role.
    """
    from app.models.database import Supplier
    
    if current_user['role'] not in ['admin', 'superuser']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.is_deleted == False
    ).first()
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    # Update fields
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    for key, value in update_data.items():
        setattr(supplier, key, value)
    
    supplier.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(supplier)
    
    return supplier
