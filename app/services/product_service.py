"""
Product Service Module

This service handles all business logic for the marketplace and product catalog, including:
- Product catalog management
- Supplier operations and verification
- Inventory tracking and stock management
- Product search and filtering
- Review and rating aggregation
- Pricing logic (discounts, bulk pricing)
- Product categorization
- Organic certification validation
- Stock alerts and reorder points
- Order management

Supports agricultural inputs, equipment, and produce marketplace.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean

from app.services.base import (
    BaseService,
    ValidationException,
    BusinessRuleException,
    ResourceNotFoundException,
    InsufficientPermissionsException
)
from app.repositories.user import UserRepository
from app.repositories.base import BaseRepository
from app.models.database import Product, Supplier, ProductReview, Order, OrderItem, User


class ProductService(BaseService):
    """
    Service class for product and marketplace business logic.
    
    This service provides comprehensive marketplace operations for
    agricultural products, supplies, and equipment.
    """
    
    # Product categories
    CATEGORIES = [
        "seeds",
        "fertilizers",
        "pesticides",
        "tools",
        "equipment",
        "irrigation",
        "organic_inputs",
        "produce",
        "livestock_feed",
        "other"
    ]
    
    # Measurement units
    UNITS = [
        "kg",
        "g",
        "liter",
        "ml",
        "piece",
        "bag",
        "box",
        "packet",
        "meter",
        "acre"
    ]
    
    def __init__(self, db: Session):
        """
        Initialize the product service.
        
        Args:
            db: SQLAlchemy database session
        """
        super().__init__(db)
        self.product_repo = BaseRepository(Product, db)
        self.supplier_repo = BaseRepository(Supplier, db)
        self.review_repo = BaseRepository(ProductReview, db)
        self.order_repo = BaseRepository(Order, db)
        self.order_item_repo = BaseRepository(OrderItem, db)
        self.user_repo = UserRepository(db)
    
    # ========================================================================
    # Product Catalog Management
    # ========================================================================
    
    def create_product(
        self,
        supplier_id: int,
        user_id: int,
        name: str,
        description: str,
        category: str,
        price: Decimal,
        unit: str,
        stock_quantity: int,
        min_order_quantity: int = 1,
        is_organic: bool = False,
        certification_number: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new product in the catalog.
        
        Business Rules:
        - User must be the supplier owner or admin
        - Supplier must be verified
        - Price must be positive
        - Stock quantity cannot be negative
        - Organic products should have certification
        - Category must be valid
        
        Args:
            supplier_id: ID of supplier
            user_id: ID of user creating product
            name: Product name
            description: Product description
            category: Product category
            price: Product price
            unit: Unit of measurement
            stock_quantity: Initial stock quantity
            min_order_quantity: Minimum order quantity (default: 1)
            is_organic: Whether product is organic certified
            certification_number: Organic certification number (optional)
            image_url: Product image URL (optional)
            
        Returns:
            Dictionary with product information
            
        Raises:
            ValidationException: If validation fails
            ResourceNotFoundException: If supplier not found
            BusinessRuleException: If business rules violated
        """
        with self.transaction():
            # Validate supplier
            supplier = self.check_resource_exists(
                self.supplier_repo.get_by_id(supplier_id),
                "Supplier",
                supplier_id
            )
            
            # Check user permissions (must own supplier or be admin)
            user = self.user_repo.get_by_id(user_id)
            if supplier.owner_id != user_id and user.role != "admin":
                raise InsufficientPermissionsException(
                    "You don't have permission to add products for this supplier"
                )
            
            # Check supplier is verified
            if not supplier.is_verified:
                raise BusinessRuleException(
                    "Supplier must be verified before adding products",
                    rule="verified_supplier_required"
                )
            
            # Validate inputs
            self.validate_string_length(name, 2, 200, "name")
            self.validate_string_length(description, 10, 2000, "description")
            
            if category not in self.CATEGORIES:
                raise ValidationException(
                    f"Invalid category. Must be one of: {', '.join(self.CATEGORIES)}",
                    field="category"
                )
            
            if unit not in self.UNITS:
                raise ValidationException(
                    f"Invalid unit. Must be one of: {', '.join(self.UNITS)}",
                    field="unit"
                )
            
            self.validate_positive(price, "price")
            
            if stock_quantity < 0:
                raise ValidationException(
                    "Stock quantity cannot be negative",
                    field="stock_quantity"
                )
            
            self.validate_positive(min_order_quantity, "min_order_quantity")
            
            # Validate organic certification
            if is_organic and not certification_number:
                raise BusinessRuleException(
                    "Organic products must have certification number",
                    rule="organic_certification_required"
                )
            
            # Create product
            product = Product(
                supplier_id=supplier_id,
                name=name,
                description=description,
                category=category,
                price=price,
                unit=unit,
                stock_quantity=stock_quantity,
                min_order_quantity=min_order_quantity,
                is_organic=is_organic,
                certification_number=certification_number,
                image_url=image_url,
                is_active=True,
                average_rating=Decimal("0.0"),
                total_reviews=0,
                total_sales=0
            )
            self.db.add(product)
            self.db.flush()
            
            self.log_activity("product_created", user_id, {
                "product_id": product.id,
                "supplier_id": supplier_id,
                "category": category
            })
            
            return self._format_product_response(product)
    
    def update_product(
        self,
        product_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[Decimal] = None,
        stock_quantity: Optional[int] = None,
        min_order_quantity: Optional[int] = None,
        is_active: Optional[bool] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update product information.
        
        Args:
            product_id: ID of product
            user_id: ID of user updating product
            name: New product name (optional)
            description: New description (optional)
            price: New price (optional)
            stock_quantity: New stock quantity (optional)
            min_order_quantity: New minimum order quantity (optional)
            is_active: Active status (optional)
            image_url: New image URL (optional)
            
        Returns:
            Updated product information
            
        Raises:
            ResourceNotFoundException: If product not found
            InsufficientPermissionsException: If user lacks permission
        """
        product = self.check_resource_exists(
            self.product_repo.get_by_id(product_id),
            "Product",
            product_id
        )
        
        # Check permissions
        supplier = self.supplier_repo.get_by_id(product.supplier_id)
        user = self.user_repo.get_by_id(user_id)
        if supplier.owner_id != user_id and user.role != "admin":
            raise InsufficientPermissionsException(
                "You don't have permission to update this product"
            )
        
        if name is not None:
            self.validate_string_length(name, 2, 200, "name")
            product.name = name
        
        if description is not None:
            self.validate_string_length(description, 10, 2000, "description")
            product.description = description
        
        if price is not None:
            self.validate_positive(price, "price")
            product.price = price
        
        if stock_quantity is not None:
            if stock_quantity < 0:
                raise ValidationException(
                    "Stock quantity cannot be negative",
                    field="stock_quantity"
                )
            product.stock_quantity = stock_quantity
        
        if min_order_quantity is not None:
            self.validate_positive(min_order_quantity, "min_order_quantity")
            product.min_order_quantity = min_order_quantity
        
        if is_active is not None:
            product.is_active = is_active
        
        if image_url is not None:
            product.image_url = image_url
        
        self.db.flush()
        
        self.log_activity("product_updated", user_id, {"product_id": product_id})
        
        return self._format_product_response(product)
    
    def update_stock(
        self,
        product_id: int,
        user_id: int,
        quantity_change: int,
        reason: str
    ) -> Dict[str, Any]:
        """
        Update product stock quantity.
        
        Args:
            product_id: ID of product
            user_id: ID of user updating stock
            quantity_change: Change in stock (positive or negative)
            reason: Reason for stock change
            
        Returns:
            Updated product with new stock level
            
        Raises:
            ResourceNotFoundException: If product not found
            ValidationException: If stock would become negative
        """
        product = self.check_resource_exists(
            self.product_repo.get_by_id(product_id),
            "Product",
            product_id
        )
        
        # Check permissions
        supplier = self.supplier_repo.get_by_id(product.supplier_id)
        user = self.user_repo.get_by_id(user_id)
        if supplier.owner_id != user_id and user.role != "admin":
            raise InsufficientPermissionsException(
                "You don't have permission to update stock for this product"
            )
        
        new_quantity = product.stock_quantity + quantity_change
        
        if new_quantity < 0:
            raise ValidationException(
                f"Stock cannot be negative. Current: {product.stock_quantity}, Change: {quantity_change}",
                field="quantity_change"
            )
        
        product.stock_quantity = new_quantity
        self.db.flush()
        
        self.log_activity("stock_updated", user_id, {
            "product_id": product_id,
            "quantity_change": quantity_change,
            "new_quantity": new_quantity,
            "reason": reason
        })
        
        return {
            "product_id": product_id,
            "previous_quantity": product.stock_quantity - quantity_change,
            "quantity_change": quantity_change,
            "new_quantity": new_quantity,
            "reason": reason
        }
    
    # ========================================================================
    # Supplier Management
    # ========================================================================
    
    def register_supplier(
        self,
        user_id: int,
        business_name: str,
        description: str,
        phone: str,
        email: str,
        county: str,
        physical_address: str,
        business_registration_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new supplier.
        
        Business Rules:
        - User must not already have a supplier account
        - Phone and email must be unique
        - Business registration number must be unique if provided
        
        Args:
            user_id: ID of user registering as supplier
            business_name: Name of business
            description: Business description
            phone: Contact phone
            email: Contact email
            county: Business location county
            physical_address: Physical address
            business_registration_number: Official registration number (optional)
            
        Returns:
            Dictionary with supplier information
            
        Raises:
            ValidationException: If validation fails
            BusinessRuleException: If user already has supplier account
        """
        with self.transaction():
            # Check if user already has supplier account
            existing = self.db.query(Supplier).filter(
                Supplier.owner_id == user_id
            ).first()
            
            if existing:
                raise BusinessRuleException(
                    "User already has a supplier account",
                    rule="one_supplier_per_user"
                )
            
            # Validate inputs
            self.validate_string_length(business_name, 2, 200, "business_name")
            self.validate_string_length(description, 10, 1000, "description")
            self.validate_phone_format(phone)
            self.validate_email_format(email)
            
            # Check phone uniqueness
            if self.db.query(Supplier).filter(Supplier.phone == phone).first():
                raise ValidationException(
                    "Phone number already registered",
                    field="phone"
                )
            
            # Check email uniqueness
            if self.db.query(Supplier).filter(Supplier.email == email).first():
                raise ValidationException(
                    "Email already registered",
                    field="email"
                )
            
            # Check business registration uniqueness if provided
            if business_registration_number:
                if self.db.query(Supplier).filter(
                    Supplier.business_registration_number == business_registration_number
                ).first():
                    raise ValidationException(
                        "Business registration number already registered",
                        field="business_registration_number"
                    )
            
            # Create supplier
            supplier = Supplier(
                owner_id=user_id,
                business_name=business_name,
                description=description,
                phone=phone,
                email=email,
                county=county,
                physical_address=physical_address,
                business_registration_number=business_registration_number,
                is_verified=False,
                total_sales=0,
                average_rating=Decimal("0.0")
            )
            self.db.add(supplier)
            self.db.flush()
            
            self.log_activity("supplier_registered", user_id, {
                "supplier_id": supplier.id
            })
            
            return self._format_supplier_response(supplier)
    
    def verify_supplier(
        self,
        supplier_id: int,
        admin_id: int,
        verification_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify a supplier (admin only).
        
        Args:
            supplier_id: ID of supplier
            admin_id: ID of admin performing verification
            verification_notes: Notes about verification (optional)
            
        Returns:
            Updated supplier information
            
        Raises:
            ResourceNotFoundException: If supplier not found
            InsufficientPermissionsException: If user is not admin
        """
        # Check admin permissions
        admin = self.user_repo.get_by_id(admin_id)
        self.check_permission(admin.role, "admin")
        
        supplier = self.check_resource_exists(
            self.supplier_repo.get_by_id(supplier_id),
            "Supplier",
            supplier_id
        )
        
        supplier.is_verified = True
        supplier.verified_at = datetime.utcnow()
        supplier.verified_by = admin_id
        self.db.flush()
        
        self.log_activity("supplier_verified", admin_id, {
            "supplier_id": supplier_id,
            "notes": verification_notes
        })
        
        return self._format_supplier_response(supplier)
    
    # ========================================================================
    # Product Search and Filtering
    # ========================================================================
    
    def search_products(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        is_organic: Optional[bool] = None,
        in_stock_only: bool = True,
        sort_by: str = "relevance",
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Search and filter products.
        
        Args:
            query: Search query (searches name and description)
            category: Filter by category
            min_price: Minimum price filter
            max_price: Maximum price filter
            is_organic: Filter organic products only
            in_stock_only: Show only in-stock products (default: True)
            sort_by: Sort order (relevance, price_low, price_high, rating, newest)
            page: Page number
            per_page: Items per page
            
        Returns:
            Dictionary with search results and pagination
        """
        # Build base query
        base_query = self.db.query(Product).filter(Product.is_active == True)
        
        # Apply filters
        if query:
            search_filter = or_(
                Product.name.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%")
            )
            base_query = base_query.filter(search_filter)
        
        if category:
            base_query = base_query.filter(Product.category == category)
        
        if min_price is not None:
            base_query = base_query.filter(Product.price >= min_price)
        
        if max_price is not None:
            base_query = base_query.filter(Product.price <= max_price)
        
        if is_organic is not None:
            base_query = base_query.filter(Product.is_organic == is_organic)
        
        if in_stock_only:
            base_query = base_query.filter(Product.stock_quantity > 0)
        
        # Apply sorting
        if sort_by == "price_low":
            base_query = base_query.order_by(Product.price.asc())
        elif sort_by == "price_high":
            base_query = base_query.order_by(Product.price.desc())
        elif sort_by == "rating":
            base_query = base_query.order_by(Product.average_rating.desc())
        elif sort_by == "newest":
            base_query = base_query.order_by(Product.created_at.desc())
        elif sort_by == "popular":
            base_query = base_query.order_by(Product.total_sales.desc())
        # Default: relevance (no additional sorting)
        
        # Get total count
        total_count = base_query.count()
        
        # Apply pagination
        products = base_query.limit(per_page).offset((page - 1) * per_page).all()
        
        return {
            "products": [self._format_product_response(p) for p in products],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total_count,
                "total_pages": (total_count + per_page - 1) // per_page
            },
            "filters_applied": {
                "query": query,
                "category": category,
                "min_price": float(min_price) if min_price else None,
                "max_price": float(max_price) if max_price else None,
                "is_organic": is_organic,
                "in_stock_only": in_stock_only,
                "sort_by": sort_by
            }
        }
    
    # ========================================================================
    # Reviews and Ratings
    # ========================================================================
    
    def add_product_review(
        self,
        product_id: int,
        user_id: int,
        rating: int,
        comment: str
    ) -> Dict[str, Any]:
        """
        Add a review for a product.
        
        Business Rules:
        - User must have purchased the product
        - Rating must be 1-5
        - User can only review each product once
        
        Args:
            product_id: ID of product
            user_id: ID of user reviewing
            rating: Rating (1-5)
            comment: Review comment
            
        Returns:
            Dictionary with review information
            
        Raises:
            ValidationException: If validation fails
            BusinessRuleException: If user hasn't purchased or already reviewed
        """
        with self.transaction():
            product = self.check_resource_exists(
                self.product_repo.get_by_id(product_id),
                "Product",
                product_id
            )
            
            # Validate rating
            if not (1 <= rating <= 5):
                raise ValidationException(
                    "Rating must be between 1 and 5",
                    field="rating"
                )
            
            self.validate_string_length(comment, 10, 1000, "comment")
            
            # Check if user has purchased this product
            has_purchased = self.db.query(OrderItem).join(Order).filter(
                OrderItem.product_id == product_id,
                Order.user_id == user_id,
                Order.status.in_(["completed", "delivered"])
            ).first()
            
            if not has_purchased:
                raise BusinessRuleException(
                    "You must purchase the product before reviewing",
                    rule="purchase_required_for_review"
                )
            
            # Check if user already reviewed
            existing_review = self.db.query(ProductReview).filter(
                ProductReview.product_id == product_id,
                ProductReview.user_id == user_id
            ).first()
            
            if existing_review:
                raise BusinessRuleException(
                    "You have already reviewed this product",
                    rule="one_review_per_product"
                )
            
            # Create review
            review = ProductReview(
                product_id=product_id,
                user_id=user_id,
                rating=rating,
                comment=comment
            )
            self.db.add(review)
            
            # Update product rating statistics
            self._update_product_rating(product)
            
            self.db.flush()
            
            self.log_activity("review_added", user_id, {
                "product_id": product_id,
                "rating": rating
            })
            
            return {
                "id": review.id,
                "product_id": review.product_id,
                "user_id": review.user_id,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at.isoformat()
            }
    
    def _update_product_rating(self, product: Product):
        """
        Update product's average rating and review count.
        
        Args:
            product: Product object
        """
        reviews = self.db.query(ProductReview).filter(
            ProductReview.product_id == product.id
        ).all()
        
        if reviews:
            ratings = [r.rating for r in reviews]
            product.average_rating = Decimal(str(mean(ratings)))
            product.total_reviews = len(reviews)
        else:
            product.average_rating = Decimal("0.0")
            product.total_reviews = 0
    
    def get_product_reviews(
        self,
        product_id: int,
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        Get reviews for a product.
        
        Args:
            product_id: ID of product
            page: Page number
            per_page: Items per page
            
        Returns:
            Dictionary with reviews and pagination
        """
        product = self.check_resource_exists(
            self.product_repo.get_by_id(product_id),
            "Product",
            product_id
        )
        
        # Get reviews with pagination
        query = self.db.query(ProductReview).filter(
            ProductReview.product_id == product_id
        ).order_by(ProductReview.created_at.desc())
        
        total_count = query.count()
        reviews = query.limit(per_page).offset((page - 1) * per_page).all()
        
        return {
            "product_id": product_id,
            "average_rating": float(product.average_rating),
            "total_reviews": product.total_reviews,
            "reviews": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "rating": r.rating,
                    "comment": r.comment,
                    "created_at": r.created_at.isoformat()
                }
                for r in reviews
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total_count,
                "total_pages": (total_count + per_page - 1) // per_page
            }
        }
    
    # ========================================================================
    # Order Management
    # ========================================================================
    
    def create_order(
        self,
        user_id: int,
        items: List[Dict[str, Any]],
        delivery_address: str,
        delivery_county: str,
        delivery_phone: str
    ) -> Dict[str, Any]:
        """
        Create a new order.
        
        Business Rules:
        - All products must be active and in stock
        - Order quantity must meet minimum order requirements
        - Stock is reserved upon order creation
        
        Args:
            user_id: ID of user placing order
            items: List of items [{product_id, quantity}]
            delivery_address: Delivery address
            delivery_county: Delivery county
            delivery_phone: Delivery phone
            
        Returns:
            Dictionary with order information
            
        Raises:
            ValidationException: If validation fails
            BusinessRuleException: If stock insufficient or minimum not met
        """
        with self.transaction():
            user = self.check_resource_exists(
                self.user_repo.get_by_id(user_id),
                "User",
                user_id
            )
            
            if not items:
                raise ValidationException("Order must contain at least one item")
            
            # Validate delivery info
            self.validate_phone_format(delivery_phone)
            self.validate_string_length(delivery_address, 10, 500, "delivery_address")
            
            # Validate and calculate order
            order_items = []
            total_amount = Decimal("0.00")
            
            for item_data in items:
                product_id = item_data.get("product_id")
                quantity = item_data.get("quantity")
                
                if not product_id or not quantity:
                    raise ValidationException("Each item must have product_id and quantity")
                
                product = self.check_resource_exists(
                    self.product_repo.get_by_id(product_id),
                    "Product",
                    product_id
                )
                
                # Validate product is active
                if not product.is_active:
                    raise BusinessRuleException(
                        f"Product '{product.name}' is not available",
                        rule="active_product_required"
                    )
                
                # Validate minimum order quantity
                if quantity < product.min_order_quantity:
                    raise BusinessRuleException(
                        f"Minimum order quantity for '{product.name}' is {product.min_order_quantity}",
                        rule="minimum_order_quantity"
                    )
                
                # Validate stock availability
                if quantity > product.stock_quantity:
                    raise BusinessRuleException(
                        f"Insufficient stock for '{product.name}'. Available: {product.stock_quantity}",
                        rule="insufficient_stock"
                    )
                
                # Calculate item total
                item_total = product.price * quantity
                total_amount += item_total
                
                order_items.append({
                    "product": product,
                    "quantity": quantity,
                    "unit_price": product.price,
                    "total_price": item_total
                })
            
            # Create order
            order = Order(
                user_id=user_id,
                total_amount=total_amount,
                delivery_address=delivery_address,
                delivery_county=delivery_county,
                delivery_phone=delivery_phone,
                status="pending",
                order_reference=self.generate_reference_number("ORD")
            )
            self.db.add(order)
            self.db.flush()
            
            # Create order items and update stock
            for item_info in order_items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item_info["product"].id,
                    quantity=item_info["quantity"],
                    unit_price=item_info["unit_price"],
                    total_price=item_info["total_price"]
                )
                self.db.add(order_item)
                
                # Reserve stock
                product = item_info["product"]
                product.stock_quantity -= item_info["quantity"]
                product.total_sales += item_info["quantity"]
            
            self.db.flush()
            
            self.log_activity("order_created", user_id, {
                "order_id": order.id,
                "total_amount": float(total_amount),
                "items_count": len(order_items)
            })
            
            return self._format_order_response(order)
    
    def update_order_status(
        self,
        order_id: int,
        user_id: int,
        status: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update order status.
        
        Args:
            order_id: ID of order
            user_id: ID of user updating status
            status: New status (confirmed, processing, shipped, delivered, cancelled)
            notes: Status update notes (optional)
            
        Returns:
            Updated order information
            
        Raises:
            ValidationException: If invalid status
            ResourceNotFoundException: If order not found
        """
        order = self.check_resource_exists(
            self.order_repo.get_by_id(order_id),
            "Order",
            order_id
        )
        
        valid_statuses = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]
        if status not in valid_statuses:
            raise ValidationException(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                field="status"
            )
        
        order.status = status
        self.db.flush()
        
        self.log_activity("order_status_updated", user_id, {
            "order_id": order_id,
            "status": status,
            "notes": notes
        })
        
        return self._format_order_response(order)
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _format_product_response(self, product: Product) -> Dict[str, Any]:
        """Format product object as API response dictionary."""
        return {
            "id": product.id,
            "supplier_id": product.supplier_id,
            "name": product.name,
            "description": product.description,
            "category": product.category,
            "price": float(product.price),
            "unit": product.unit,
            "stock_quantity": product.stock_quantity,
            "min_order_quantity": product.min_order_quantity,
            "is_organic": product.is_organic,
            "certification_number": product.certification_number,
            "image_url": product.image_url,
            "is_active": product.is_active,
            "average_rating": float(product.average_rating),
            "total_reviews": product.total_reviews,
            "total_sales": product.total_sales,
            "created_at": product.created_at.isoformat()
        }
    
    def _format_supplier_response(self, supplier: Supplier) -> Dict[str, Any]:
        """Format supplier object as API response dictionary."""
        return {
            "id": supplier.id,
            "owner_id": supplier.owner_id,
            "business_name": supplier.business_name,
            "description": supplier.description,
            "phone": supplier.phone,
            "email": supplier.email,
            "county": supplier.county,
            "physical_address": supplier.physical_address,
            "business_registration_number": supplier.business_registration_number,
            "is_verified": supplier.is_verified,
            "verified_at": supplier.verified_at.isoformat() if supplier.verified_at else None,
            "total_sales": supplier.total_sales,
            "average_rating": float(supplier.average_rating),
            "created_at": supplier.created_at.isoformat()
        }
    
    def _format_order_response(self, order: Order) -> Dict[str, Any]:
        """Format order object as API response dictionary."""
        # Get order items
        items = self.db.query(OrderItem).filter(
            OrderItem.order_id == order.id
        ).all()
        
        return {
            "id": order.id,
            "order_reference": order.order_reference,
            "user_id": order.user_id,
            "total_amount": float(order.total_amount),
            "delivery_address": order.delivery_address,
            "delivery_county": order.delivery_county,
            "delivery_phone": order.delivery_phone,
            "status": order.status,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "total_price": float(item.total_price)
                }
                for item in items
            ],
            "created_at": order.created_at.isoformat()
        }
