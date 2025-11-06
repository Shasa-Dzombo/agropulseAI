"""
Chama Service Module

This service handles all business logic for digital cooperatives (Chamas), including:
- Chama creation and management
- Member management and roles
- Loan application and approval workflow
- Guarantor system
- Loan repayment tracking
- Interest calculations
- Penalty handling
- Financial reporting
- Member analytics
- Transaction management

A Chama is a digital cooperative that enables members to pool resources,
provide microfinance services, and support each other financially.
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
import enum

from app.services.base import (
    BaseService,
    ValidationException,
    BusinessRuleException,
    ResourceNotFoundException,
    InsufficientPermissionsException
)
from app.repositories.base import BaseRepository
from app.repositories.user import UserRepository
from app.models.database import (
    Chama, ChamaMember, Loan, LoanRepayment, Guarantor,
    Transaction, LoanStatus, ChamaMemberRole, TransactionType
)


class ChamaService(BaseService):
    """
    Service class for Chama (digital cooperative) business logic.
    
    This service provides comprehensive microfinance operations,
    implementing banking-like business rules and workflows.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the chama service.
        
        Args:
            db: SQLAlchemy database session
        """
        super().__init__(db)
        self.chama_repo = BaseRepository(Chama, db)
        self.member_repo = BaseRepository(ChamaMember, db)
        self.loan_repo = BaseRepository(Loan, db)
        self.repayment_repo = BaseRepository(LoanRepayment, db)
        self.guarantor_repo = BaseRepository(Guarantor, db)
        self.transaction_repo = BaseRepository(Transaction, db)
        self.user_repo = UserRepository(db)
    
    # ========================================================================
    # Chama Creation and Management
    # ========================================================================
    
    def create_chama(
        self,
        founder_id: int,
        name: str,
        description: Optional[str] = None,
        registration_fee: Decimal = Decimal("0"),
        monthly_contribution: Decimal = Decimal("0"),
        max_members: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new Chama (digital cooperative).
        
        Business Rules:
        - Founder must be an active user
        - Name must be unique
        - Fees must be non-negative
        - Founder automatically becomes admin
        - Initial balance is 0
        
        Args:
            founder_id: ID of founding user
            name: Chama name
            description: Chama description (optional)
            registration_fee: One-time registration fee (default: 0)
            monthly_contribution: Required monthly contribution (default: 0)
            max_members: Maximum members allowed (optional)
            
        Returns:
            Dictionary with chama information
            
        Raises:
            ValidationException: If validation fails
            ResourceNotFoundException: If founder not found
        """
        with self.transaction():
            # Validate founder exists
            founder = self.check_resource_exists(
                self.user_repo.get_by_id(founder_id),
                "User",
                founder_id
            )
            
            if not founder.is_active:
                raise BusinessRuleException(
                    "Cannot create chama with inactive user",
                    rule="active_user_required"
                )
            
            # Validate inputs
            self.validate_string_length(name, 3, 100, "name")
            
            if registration_fee < 0:
                raise ValidationException("Registration fee cannot be negative", field="registration_fee")
            
            if monthly_contribution < 0:
                raise ValidationException("Monthly contribution cannot be negative", field="monthly_contribution")
            
            if max_members is not None and max_members < 2:
                raise ValidationException("Chama must allow at least 2 members", field="max_members")
            
            # Check name uniqueness
            existing = self.db.query(Chama).filter(Chama.name == name).first()
            if existing:
                raise ValidationException("Chama name already exists", field="name")
            
            # Create chama
            chama = Chama(
                name=name,
                description=description,
                registration_fee=registration_fee,
                monthly_contribution=monthly_contribution,
                total_balance=Decimal("0"),
                max_members=max_members,
                is_active=True
            )
            self.db.add(chama)
            self.db.flush()
            
            # Add founder as admin member
            member = ChamaMember(
                chama_id=chama.id,
                user_id=founder_id,
                role=ChamaMemberRole.ADMIN,
                joined_at=datetime.utcnow(),
                is_active=True
            )
            self.db.add(member)
            
            self.log_activity("chama_created", founder_id, {
                "chama_id": chama.id,
                "name": name
            })
            
            return self._format_chama_response(chama)
    
    def update_chama(
        self,
        chama_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        monthly_contribution: Optional[Decimal] = None,
        max_members: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update chama details (admin only).
        
        Args:
            chama_id: ID of chama
            user_id: ID of user performing update
            name: New name (optional)
            description: New description (optional)
            monthly_contribution: New contribution amount (optional)
            max_members: New max members (optional)
            
        Returns:
            Updated chama information
            
        Raises:
            ResourceNotFoundException: If chama not found
            InsufficientPermissionsException: If user is not admin
        """
        chama = self.check_resource_exists(
            self.chama_repo.get_by_id(chama_id),
            "Chama",
            chama_id
        )
        
        self._check_chama_admin(chama_id, user_id)
        
        if name is not None:
            self.validate_string_length(name, 3, 100, "name")
            chama.name = name
        
        if description is not None:
            chama.description = description
        
        if monthly_contribution is not None:
            if monthly_contribution < 0:
                raise ValidationException("Monthly contribution cannot be negative")
            chama.monthly_contribution = monthly_contribution
        
        if max_members is not None:
            current_members = len(self._get_active_members(chama_id))
            if max_members < current_members:
                raise BusinessRuleException(
                    f"Cannot set max members below current member count ({current_members})",
                    rule="max_members_constraint"
                )
            chama.max_members = max_members
        
        self.db.flush()
        
        self.log_activity("chama_updated", user_id, {"chama_id": chama_id})
        
        return self._format_chama_response(chama)
    
    # ========================================================================
    # Member Management
    # ========================================================================
    
    def add_member(
        self,
        chama_id: int,
        admin_id: int,
        new_member_id: int
    ) -> Dict[str, Any]:
        """
        Add a new member to chama (admin only).
        
        Business Rules:
        - Only admins can add members
        - User must exist and be active
        - User cannot already be a member
        - Chama must not be at max capacity
        - Registration fee must be recorded
        
        Args:
            chama_id: ID of chama
            admin_id: ID of admin adding member
            new_member_id: ID of user to add
            
        Returns:
            Member information
            
        Raises:
            ResourceNotFoundException: If chama or user not found
            InsufficientPermissionsException: If user is not admin
            BusinessRuleException: If business rules violated
        """
        with self.transaction():
            chama = self.check_resource_exists(
                self.chama_repo.get_by_id(chama_id),
                "Chama",
                chama_id
            )
            
            self._check_chama_admin(chama_id, admin_id)
            
            # Validate new member
            new_user = self.check_resource_exists(
                self.user_repo.get_by_id(new_member_id),
                "User",
                new_member_id
            )
            
            if not new_user.is_active:
                raise BusinessRuleException(
                    "Cannot add inactive user to chama",
                    rule="active_user_required"
                )
            
            # Check if already a member
            existing = self.db.query(ChamaMember).filter(
                ChamaMember.chama_id == chama_id,
                ChamaMember.user_id == new_member_id
            ).first()
            
            if existing:
                raise BusinessRuleException(
                    "User is already a member of this chama",
                    rule="unique_membership"
                )
            
            # Check max capacity
            if chama.max_members:
                current_count = len(self._get_active_members(chama_id))
                if current_count >= chama.max_members:
                    raise BusinessRuleException(
                        f"Chama is at maximum capacity ({chama.max_members} members)",
                        rule="max_members_reached"
                    )
            
            # Create membership
            member = ChamaMember(
                chama_id=chama_id,
                user_id=new_member_id,
                role=ChamaMemberRole.MEMBER,
                joined_at=datetime.utcnow(),
                is_active=True
            )
            self.db.add(member)
            
            # Record registration fee transaction if applicable
            if chama.registration_fee > 0:
                transaction = Transaction(
                    chama_id=chama_id,
                    member_id=new_member_id,
                    amount=chama.registration_fee,
                    transaction_type=TransactionType.REGISTRATION_FEE,
                    description=f"Registration fee for {new_user.username}",
                    transaction_date=datetime.utcnow()
                )
                self.db.add(transaction)
                chama.total_balance += chama.registration_fee
            
            self.log_activity("member_added", admin_id, {
                "chama_id": chama_id,
                "new_member_id": new_member_id
            })
            
            return {
                "id": member.id,
                "chama_id": member.chama_id,
                "user_id": member.user_id,
                "username": new_user.username,
                "role": member.role.value,
                "joined_at": member.joined_at.isoformat(),
                "registration_fee_paid": float(chama.registration_fee)
            }
    
    def remove_member(
        self,
        chama_id: int,
        admin_id: int,
        member_id: int,
        reason: str
    ) -> Dict[str, str]:
        """
        Remove a member from chama (admin only).
        
        Business Rules:
        - Only admins can remove members
        - Cannot remove the last admin
        - Member must not have active loans
        - Member must not be a guarantor for active loans
        
        Args:
            chama_id: ID of chama
            admin_id: ID of admin removing member
            member_id: ID of member to remove
            reason: Reason for removal
            
        Returns:
            Success message
            
        Raises:
            ResourceNotFoundException: If chama or member not found
            InsufficientPermissionsException: If user is not admin
            BusinessRuleException: If business rules violated
        """
        self._check_chama_admin(chama_id, admin_id)
        
        member = self.db.query(ChamaMember).filter(
            ChamaMember.chama_id == chama_id,
            ChamaMember.user_id == member_id
        ).first()
        
        if not member:
            raise ResourceNotFoundException("ChamaMember", member_id)
        
        # Check if last admin
        if member.role == ChamaMemberRole.ADMIN:
            admin_count = self.db.query(ChamaMember).filter(
                ChamaMember.chama_id == chama_id,
                ChamaMember.role == ChamaMemberRole.ADMIN,
                ChamaMember.is_active == True
            ).count()
            
            if admin_count <= 1:
                raise BusinessRuleException(
                    "Cannot remove the last admin. Promote another member first.",
                    rule="minimum_one_admin"
                )
        
        # Check for active loans
        active_loans = self.db.query(Loan).filter(
            Loan.chama_id == chama_id,
            Loan.borrower_id == member_id,
            Loan.status.in_([LoanStatus.PENDING, LoanStatus.APPROVED, LoanStatus.ACTIVE])
        ).count()
        
        if active_loans > 0:
            raise BusinessRuleException(
                f"Member has {active_loans} active loan(s). Cannot remove until loans are closed.",
                rule="no_active_loans_for_removal"
            )
        
        # Check if guarantor for active loans
        active_guarantees = self.db.query(Guarantor).join(Loan).filter(
            Guarantor.guarantor_id == member_id,
            Loan.chama_id == chama_id,
            Loan.status.in_([LoanStatus.APPROVED, LoanStatus.ACTIVE])
        ).count()
        
        if active_guarantees > 0:
            raise BusinessRuleException(
                f"Member is guarantor for {active_guarantees} active loan(s). Cannot remove.",
                rule="no_active_guarantees_for_removal"
            )
        
        # Deactivate member
        member.is_active = False
        self.db.flush()
        
        self.log_activity("member_removed", admin_id, {
            "chama_id": chama_id,
            "member_id": member_id,
            "reason": reason
        })
        
        return {"message": "Member removed successfully"}
    
    def update_member_role(
        self,
        chama_id: int,
        admin_id: int,
        member_id: int,
        new_role: str
    ) -> Dict[str, Any]:
        """
        Update a member's role (admin only).
        
        Args:
            chama_id: ID of chama
            admin_id: ID of admin performing update
            member_id: ID of member to update
            new_role: New role (admin, treasurer, member)
            
        Returns:
            Updated member information
            
        Raises:
            ResourceNotFoundException: If member not found
            InsufficientPermissionsException: If user is not admin
            ValidationException: If role is invalid
        """
        self._check_chama_admin(chama_id, admin_id)
        
        member = self.db.query(ChamaMember).filter(
            ChamaMember.chama_id == chama_id,
            ChamaMember.user_id == member_id
        ).first()
        
        if not member:
            raise ResourceNotFoundException("ChamaMember", member_id)
        
        # Validate role
        try:
            new_role_enum = ChamaMemberRole(new_role)
        except ValueError:
            valid_roles = [role.value for role in ChamaMemberRole]
            raise ValidationException(
                f"Invalid role. Must be one of: {', '.join(valid_roles)}",
                field="new_role"
            )
        
        old_role = member.role
        member.role = new_role_enum
        self.db.flush()
        
        self.log_activity("member_role_updated", admin_id, {
            "chama_id": chama_id,
            "member_id": member_id,
            "from_role": old_role.value,
            "to_role": new_role
        })
        
        return {
            "member_id": member_id,
            "chama_id": chama_id,
            "role": member.role.value,
            "message": f"Role updated to {new_role}"
        }
    
    # ========================================================================
    # Loan Application and Approval
    # ========================================================================
    
    def apply_for_loan(
        self,
        chama_id: int,
        borrower_id: int,
        amount: Decimal,
        purpose: str,
        duration_months: int,
        guarantor_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Apply for a loan from chama.
        
        Business Rules:
        - Borrower must be an active member
        - Amount must not exceed chama balance
        - Must have required number of guarantors (min 2)
        - Guarantors must be active members
        - Borrower cannot have another active loan
        - Duration must be reasonable (1-24 months)
        
        Args:
            chama_id: ID of chama
            borrower_id: ID of borrowing member
            amount: Loan amount
            purpose: Loan purpose
            duration_months: Loan duration in months
            guarantor_ids: List of guarantor user IDs
            
        Returns:
            Loan application information
            
        Raises:
            ValidationException: If validation fails
            BusinessRuleException: If business rules violated
        """
        with self.transaction():
            chama = self.check_resource_exists(
                self.chama_repo.get_by_id(chama_id),
                "Chama",
                chama_id
            )
            
            # Validate borrower is active member
            borrower_member = self._get_member(chama_id, borrower_id)
            if not borrower_member.is_active:
                raise BusinessRuleException(
                    "Borrower must be an active member",
                    rule="active_member_required"
                )
            
            # Validate amount
            self.validate_positive(float(amount), "amount")
            
            if amount > chama.total_balance:
                raise BusinessRuleException(
                    f"Loan amount ({amount}) exceeds chama balance ({chama.total_balance})",
                    rule="insufficient_chama_funds",
                    details={
                        "requested": float(amount),
                        "available": float(chama.total_balance)
                    }
                )
            
            # Validate duration
            if not (1 <= duration_months <= 24):
                raise ValidationException(
                    "Loan duration must be between 1 and 24 months",
                    field="duration_months"
                )
            
            # Check for existing active loans
            existing_loans = self.db.query(Loan).filter(
                Loan.chama_id == chama_id,
                Loan.borrower_id == borrower_id,
                Loan.status.in_([LoanStatus.PENDING, LoanStatus.APPROVED, LoanStatus.ACTIVE])
            ).count()
            
            if existing_loans > 0:
                raise BusinessRuleException(
                    "Borrower already has an active loan. Clear existing loan first.",
                    rule="one_active_loan_per_member"
                )
            
            # Validate guarantors
            if len(guarantor_ids) < 2:
                raise ValidationException(
                    "Minimum 2 guarantors required",
                    field="guarantor_ids"
                )
            
            if borrower_id in guarantor_ids:
                raise ValidationException(
                    "Borrower cannot be their own guarantor",
                    field="guarantor_ids"
                )
            
            # Validate each guarantor
            for guarantor_id in guarantor_ids:
                guarantor_member = self._get_member(chama_id, guarantor_id)
                if not guarantor_member.is_active:
                    raise BusinessRuleException(
                        f"Guarantor {guarantor_id} is not an active member",
                        rule="active_guarantor_required"
                    )
            
            # Calculate interest (12% annual rate for this example)
            interest_rate = Decimal("0.12")
            interest_amount = amount * interest_rate * Decimal(duration_months) / Decimal(12)
            total_amount = amount + interest_amount
            
            # Create loan application
            loan = Loan(
                chama_id=chama_id,
                borrower_id=borrower_id,
                amount=amount,
                interest_rate=interest_rate,
                interest_amount=interest_amount,
                total_amount=total_amount,
                duration_months=duration_months,
                purpose=purpose,
                status=LoanStatus.PENDING,
                application_date=datetime.utcnow()
            )
            self.db.add(loan)
            self.db.flush()
            
            # Add guarantors
            for guarantor_id in guarantor_ids:
                guarantor = Guarantor(
                    loan_id=loan.id,
                    guarantor_id=guarantor_id,
                    guaranteed_at=datetime.utcnow()
                )
                self.db.add(guarantor)
            
            self.log_activity("loan_applied", borrower_id, {
                "chama_id": chama_id,
                "loan_id": loan.id,
                "amount": float(amount)
            })
            
            return self._format_loan_response(loan)
    
    def approve_loan(
        self,
        loan_id: int,
        admin_id: int,
        approval_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve a loan application (admin/treasurer only).
        
        Business Rules:
        - Only admin or treasurer can approve
        - Loan must be in PENDING status
        - Chama must have sufficient balance
        - Approval triggers fund disbursement
        - Due date is calculated from approval date
        
        Args:
            loan_id: ID of loan
            admin_id: ID of admin approving
            approval_notes: Optional approval notes
            
        Returns:
            Approved loan information
            
        Raises:
            ResourceNotFoundException: If loan not found
            InsufficientPermissionsException: If user lacks permission
            BusinessRuleException: If business rules violated
        """
        with self.transaction():
            loan = self.check_resource_exists(
                self.loan_repo.get_by_id(loan_id),
                "Loan",
                loan_id
            )
            
            # Check admin permission
            admin_member = self._get_member(loan.chama_id, admin_id)
            if admin_member.role not in [ChamaMemberRole.ADMIN, ChamaMemberRole.TREASURER]:
                raise InsufficientPermissionsException(
                    "Only admins and treasurers can approve loans"
                )
            
            # Validate loan status
            if loan.status != LoanStatus.PENDING:
                raise BusinessRuleException(
                    f"Cannot approve loan in {loan.status.value} status",
                    rule="pending_status_required"
                )
            
            # Check chama balance
            chama = self.chama_repo.get_by_id(loan.chama_id)
            if loan.amount > chama.total_balance:
                raise BusinessRuleException(
                    "Insufficient chama funds for loan disbursement",
                    rule="insufficient_funds"
                )
            
            # Approve loan
            loan.status = LoanStatus.APPROVED
            loan.approved_date = datetime.utcnow()
            loan.disbursement_date = datetime.utcnow()
            loan.due_date = self.add_days_to_date(datetime.utcnow(), loan.duration_months * 30)
            
            # Deduct from chama balance
            chama.total_balance -= loan.amount
            
            # Record disbursement transaction
            transaction = Transaction(
                chama_id=loan.chama_id,
                member_id=loan.borrower_id,
                loan_id=loan.id,
                amount=-loan.amount,  # Negative for disbursement
                transaction_type=TransactionType.LOAN_DISBURSEMENT,
                description=f"Loan disbursement: {loan.purpose}",
                transaction_date=datetime.utcnow()
            )
            self.db.add(transaction)
            
            self.log_activity("loan_approved", admin_id, {
                "loan_id": loan_id,
                "amount": float(loan.amount)
            })
            
            return self._format_loan_response(loan)
    
    def reject_loan(
        self,
        loan_id: int,
        admin_id: int,
        rejection_reason: str
    ) -> Dict[str, str]:
        """
        Reject a loan application (admin/treasurer only).
        
        Args:
            loan_id: ID of loan
            admin_id: ID of admin rejecting
            rejection_reason: Reason for rejection
            
        Returns:
            Success message
            
        Raises:
            ResourceNotFoundException: If loan not found
            InsufficientPermissionsException: If user lacks permission
        """
        loan = self.check_resource_exists(
            self.loan_repo.get_by_id(loan_id),
            "Loan",
            loan_id
        )
        
        # Check admin permission
        admin_member = self._get_member(loan.chama_id, admin_id)
        if admin_member.role not in [ChamaMemberRole.ADMIN, ChamaMemberRole.TREASURER]:
            raise InsufficientPermissionsException(
                "Only admins and treasurers can reject loans"
            )
        
        if loan.status != LoanStatus.PENDING:
            raise BusinessRuleException(
                f"Cannot reject loan in {loan.status.value} status",
                rule="pending_status_required"
            )
        
        loan.status = LoanStatus.REJECTED
        self.db.flush()
        
        self.log_activity("loan_rejected", admin_id, {
            "loan_id": loan_id,
            "reason": rejection_reason
        })
        
        return {"message": f"Loan rejected: {rejection_reason}"}
    
    # ========================================================================
    # Loan Repayment
    # ========================================================================
    
    def make_repayment(
        self,
        loan_id: int,
        payer_id: int,
        amount: Decimal,
        payment_reference: str,
        payment_method: str = "cash"
    ) -> Dict[str, Any]:
        """
        Make a loan repayment.
        
        Business Rules:
        - Loan must be in APPROVED or ACTIVE status
        - Amount must be positive
        - Overpayment is allowed
        - Loan is marked PAID when fully repaid
        - Chama balance is increased
        - Late payment penalty applied if overdue
        
        Args:
            loan_id: ID of loan
            payer_id: ID of member making payment
            amount: Repayment amount
            payment_reference: Payment reference/receipt number
            payment_method: Payment method (cash, mpesa, bank)
            
        Returns:
            Repayment information with loan status
            
        Raises:
            ResourceNotFoundException: If loan not found
            ValidationException: If validation fails
            BusinessRuleException: If business rules violated
        """
        with self.transaction():
            loan = self.check_resource_exists(
                self.loan_repo.get_by_id(loan_id),
                "Loan",
                loan_id
            )
            
            # Validate loan status
            if loan.status not in [LoanStatus.APPROVED, LoanStatus.ACTIVE]:
                raise BusinessRuleException(
                    f"Cannot make repayment for loan in {loan.status.value} status",
                    rule="active_loan_required"
                )
            
            # Validate amount
            self.validate_positive(float(amount), "amount")
            
            # Calculate penalty if overdue
            penalty_amount = Decimal("0")
            if loan.due_date and datetime.utcnow() > loan.due_date:
                days_overdue = self.calculate_days_between(loan.due_date, datetime.utcnow())
                # Penalty: 1% of remaining balance per month overdue
                months_overdue = Decimal(days_overdue) / Decimal(30)
                remaining_balance = loan.total_amount - (loan.amount_paid or Decimal("0"))
                penalty_amount = remaining_balance * Decimal("0.01") * months_overdue
            
            # Create repayment record
            repayment = LoanRepayment(
                loan_id=loan_id,
                amount=amount,
                payment_date=datetime.utcnow(),
                payment_method=payment_method,
                payment_reference=payment_reference,
                penalty_amount=penalty_amount
            )
            self.db.add(repayment)
            
            # Update loan
            loan.amount_paid = (loan.amount_paid or Decimal("0")) + amount
            loan.status = LoanStatus.ACTIVE
            
            # Check if fully paid
            if loan.amount_paid >= (loan.total_amount + penalty_amount):
                loan.status = LoanStatus.PAID
            
            # Update chama balance
            chama = self.chama_repo.get_by_id(loan.chama_id)
            chama.total_balance += amount
            
            # Record transaction
            transaction = Transaction(
                chama_id=loan.chama_id,
                member_id=payer_id,
                loan_id=loan_id,
                amount=amount,
                transaction_type=TransactionType.LOAN_REPAYMENT,
                description=f"Loan repayment - Ref: {payment_reference}",
                transaction_date=datetime.utcnow()
            )
            self.db.add(transaction)
            
            self.log_activity("repayment_made", payer_id, {
                "loan_id": loan_id,
                "amount": float(amount),
                "penalty": float(penalty_amount)
            })
            
            remaining_balance = loan.total_amount - loan.amount_paid
            
            return {
                "repayment_id": repayment.id,
                "loan_id": loan_id,
                "amount": float(amount),
                "penalty_amount": float(penalty_amount),
                "total_paid": float(loan.amount_paid),
                "remaining_balance": float(remaining_balance),
                "loan_status": loan.status.value,
                "payment_date": repayment.payment_date.isoformat(),
                "message": "Repayment recorded successfully"
            }
    
    def get_loan_repayment_schedule(self, loan_id: int) -> Dict[str, Any]:
        """
        Get repayment schedule for a loan.
        
        Args:
            loan_id: ID of loan
            
        Returns:
            Repayment schedule with monthly breakdown
            
        Raises:
            ResourceNotFoundException: If loan not found
        """
        loan = self.check_resource_exists(
            self.loan_repo.get_by_id(loan_id),
            "Loan",
            loan_id
        )
        
        if not loan.disbursement_date:
            return {
                "loan_id": loan_id,
                "message": "Loan not yet disbursed"
            }
        
        # Calculate monthly payment
        monthly_payment = loan.total_amount / Decimal(loan.duration_months)
        
        # Generate schedule
        schedule = []
        current_date = loan.disbursement_date
        
        for month in range(1, loan.duration_months + 1):
            payment_date = self.add_days_to_date(current_date, 30)
            schedule.append({
                "month": month,
                "due_date": payment_date.isoformat(),
                "amount_due": float(monthly_payment),
                "cumulative_amount": float(monthly_payment * month)
            })
            current_date = payment_date
        
        # Get actual repayments
        repayments = self.db.query(LoanRepayment).filter(
            LoanRepayment.loan_id == loan_id
        ).all()
        
        return {
            "loan_id": loan_id,
            "total_amount": float(loan.total_amount),
            "monthly_payment": float(monthly_payment),
            "duration_months": loan.duration_months,
            "amount_paid": float(loan.amount_paid or 0),
            "remaining_balance": float(loan.total_amount - (loan.amount_paid or 0)),
            "schedule": schedule,
            "actual_repayments": [
                {
                    "payment_date": r.payment_date.isoformat(),
                    "amount": float(r.amount),
                    "penalty": float(r.penalty_amount or 0),
                    "payment_method": r.payment_method,
                    "reference": r.payment_reference
                }
                for r in repayments
            ]
        }
    
    # ========================================================================
    # Financial Reporting
    # ========================================================================
    
    def get_chama_financial_summary(self, chama_id: int) -> Dict[str, Any]:
        """
        Get comprehensive financial summary for a chama.
        
        Args:
            chama_id: ID of chama
            
        Returns:
            Financial summary with all key metrics
            
        Raises:
            ResourceNotFoundException: If chama not found
        """
        chama = self.check_resource_exists(
            self.chama_repo.get_by_id(chama_id),
            "Chama",
            chama_id
        )
        
        # Get all loans
        all_loans = self.db.query(Loan).filter(Loan.chama_id == chama_id).all()
        
        # Calculate loan statistics
        total_loans_issued = len(all_loans)
        total_amount_disbursed = sum(loan.amount for loan in all_loans if loan.status != LoanStatus.REJECTED)
        active_loans = [loan for loan in all_loans if loan.status in [LoanStatus.APPROVED, LoanStatus.ACTIVE]]
        total_active_loan_amount = sum(loan.amount for loan in active_loans)
        total_amount_repaid = sum(loan.amount_paid or Decimal("0") for loan in all_loans)
        
        # Get all transactions
        transactions = self.db.query(Transaction).filter(
            Transaction.chama_id == chama_id
        ).all()
        
        total_contributions = sum(
            t.amount for t in transactions
            if t.transaction_type in [TransactionType.CONTRIBUTION, TransactionType.REGISTRATION_FEE]
        )
        
        total_interest_earned = sum(
            loan.interest_amount for loan in all_loans
            if loan.status == LoanStatus.PAID
        )
        
        # Calculate default rate
        defaulted_loans = [
            loan for loan in all_loans
            if loan.due_date and datetime.utcnow() > loan.due_date
            and loan.status == LoanStatus.ACTIVE
        ]
        default_rate = self.calculate_percentage(len(defaulted_loans), total_loans_issued)
        
        return {
            "chama_id": chama_id,
            "chama_name": chama.name,
            "current_balance": float(chama.total_balance),
            "total_members": len(self._get_active_members(chama_id)),
            "loans": {
                "total_issued": total_loans_issued,
                "active_loans": len(active_loans),
                "paid_loans": len([l for l in all_loans if l.status == LoanStatus.PAID]),
                "defaulted_loans": len(defaulted_loans),
                "default_rate": default_rate
            },
            "financial_metrics": {
                "total_disbursed": float(total_amount_disbursed),
                "total_repaid": float(total_amount_repaid),
                "active_loan_amount": float(total_active_loan_amount),
                "total_contributions": float(total_contributions),
                "interest_earned": float(total_interest_earned),
                "net_profit": float(total_interest_earned)
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def get_member_financial_summary(
        self,
        chama_id: int,
        member_id: int
    ) -> Dict[str, Any]:
        """
        Get financial summary for a specific member.
        
        Args:
            chama_id: ID of chama
            member_id: ID of member
            
        Returns:
            Member's financial summary
            
        Raises:
            ResourceNotFoundException: If member not found
        """
        member = self._get_member(chama_id, member_id)
        
        # Get member's loans
        loans = self.db.query(Loan).filter(
            Loan.chama_id == chama_id,
            Loan.borrower_id == member_id
        ).all()
        
        active_loans = [l for l in loans if l.status in [LoanStatus.APPROVED, LoanStatus.ACTIVE]]
        
        total_borrowed = sum(l.amount for l in loans if l.status != LoanStatus.REJECTED)
        total_repaid = sum(l.amount_paid or Decimal("0") for l in loans)
        outstanding_balance = sum(
            l.total_amount - (l.amount_paid or Decimal("0"))
            for l in active_loans
        )
        
        # Get member's contributions
        contributions = self.db.query(Transaction).filter(
            Transaction.chama_id == chama_id,
            Transaction.member_id == member_id,
            Transaction.transaction_type.in_([
                TransactionType.CONTRIBUTION,
                TransactionType.REGISTRATION_FEE
            ])
        ).all()
        
        total_contributions = sum(t.amount for t in contributions)
        
        # Count guarantees
        guarantees = self.db.query(Guarantor).filter(
            Guarantor.guarantor_id == member_id
        ).count()
        
        return {
            "chama_id": chama_id,
            "member_id": member_id,
            "member_role": member.role.value,
            "joined_at": member.joined_at.isoformat(),
            "loans": {
                "total_loans": len(loans),
                "active_loans": len(active_loans),
                "total_borrowed": float(total_borrowed),
                "total_repaid": float(total_repaid),
                "outstanding_balance": float(outstanding_balance)
            },
            "contributions": {
                "total_contributed": float(total_contributions),
                "number_of_contributions": len(contributions)
            },
            "guarantees": {
                "total_guarantees": guarantees
            }
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _get_member(self, chama_id: int, user_id: int) -> ChamaMember:
        """Get a chama member or raise exception."""
        member = self.db.query(ChamaMember).filter(
            ChamaMember.chama_id == chama_id,
            ChamaMember.user_id == user_id
        ).first()
        
        if not member:
            raise ResourceNotFoundException("ChamaMember", user_id)
        
        return member
    
    def _get_active_members(self, chama_id: int) -> List[ChamaMember]:
        """Get all active members of a chama."""
        return self.db.query(ChamaMember).filter(
            ChamaMember.chama_id == chama_id,
            ChamaMember.is_active == True
        ).all()
    
    def _check_chama_admin(self, chama_id: int, user_id: int):
        """Check if user is chama admin, raise exception if not."""
        member = self._get_member(chama_id, user_id)
        if member.role != ChamaMemberRole.ADMIN:
            raise InsufficientPermissionsException(
                "Only chama admins can perform this action"
            )
    
    def _format_chama_response(self, chama: Chama) -> Dict[str, Any]:
        """Format chama object as API response dictionary."""
        return {
            "id": chama.id,
            "name": chama.name,
            "description": chama.description,
            "registration_fee": float(chama.registration_fee),
            "monthly_contribution": float(chama.monthly_contribution),
            "total_balance": float(chama.total_balance),
            "max_members": chama.max_members,
            "is_active": chama.is_active,
            "created_at": chama.created_at.isoformat()
        }
    
    def _format_loan_response(self, loan: Loan) -> Dict[str, Any]:
        """Format loan object as API response dictionary."""
        return {
            "id": loan.id,
            "chama_id": loan.chama_id,
            "borrower_id": loan.borrower_id,
            "amount": float(loan.amount),
            "interest_rate": float(loan.interest_rate),
            "interest_amount": float(loan.interest_amount),
            "total_amount": float(loan.total_amount),
            "amount_paid": float(loan.amount_paid or 0),
            "duration_months": loan.duration_months,
            "purpose": loan.purpose,
            "status": loan.status.value,
            "application_date": loan.application_date.isoformat(),
            "approved_date": loan.approved_date.isoformat() if loan.approved_date else None,
            "disbursement_date": loan.disbursement_date.isoformat() if loan.disbursement_date else None,
            "due_date": loan.due_date.isoformat() if loan.due_date else None
        }
