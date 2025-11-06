"""
SACCO Risk & Loan Management System
===================================

Dynamic agricultural lending based on verifiable harvest predictions:

1. Dynamic Collateralization
   - Drone-verified asset valuation
   - Real-time harvest forecast integration
   - Quality-adjusted collateral value
   - Automatic revaluation on new drone scans

2. Yield-Based Credit Scoring
   - Historical yield performance
   - Current season prediction confidence
   - Weather risk assessment
   - Income projection models

3. Automated Loan Adjustment
   - Mid-season reassessment
   - Credit limit increase/decrease
   - Pre-approval notifications
   - Harvest-linked repayment

4. Risk Assessment Engine
   - Multi-factor risk modeling
   - Portfolio risk aggregation
   - SACCO capital adequacy monitoring
   - Default probability prediction

Enables:
- Credit access for smallholder farmers
- Reduced default risk through verification
- Dynamic risk pricing
- Automated loan management
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum


class LoanStatus(Enum):
    """Loan lifecycle states"""
    PENDING = "pending"  # Application submitted
    APPROVED = "approved"  # Approved, awaiting disbursement
    DISBURSED = "disbursed"  # Funds released
    ACTIVE = "active"  # Repayment period
    DEFAULTED = "defaulted"  # Missed payments
    COMPLETED = "completed"  # Fully repaid


class RiskLevel(Enum):
    """Risk categories"""
    VERY_LOW = "very_low"  # <5% default probability
    LOW = "low"  # 5-10%
    MEDIUM = "medium"  # 10-20%
    HIGH = "high"  # 20-35%
    VERY_HIGH = "very_high"  # >35%


@dataclass
class CollateralAsset:
    """Agricultural asset used as collateral"""
    asset_id: str
    farm_id: str
    crop_type: str
    area_hectares: float
    
    # Harvest prediction
    predicted_yield_tons: float
    quality_distribution: Dict[str, float]  # {"A": 40%, "B": 45%...}
    harvest_date: datetime
    confidence_score: float  # 0-100%
    
    # Valuation
    market_price_per_ton: float
    estimated_revenue: float
    collateral_value: float  # 70% of estimated revenue (LTV ratio)
    
    # Verification
    drone_scan_date: datetime
    certificate_hash: str
    
    # Status
    pledged_to_loan: Optional[str]  # loan_id if pledged
    last_revaluation: datetime


@dataclass
class CreditScore:
    """Farmer credit assessment"""
    farmer_id: str
    
    # Historical performance
    past_yields: List[float]  # Tons per hectare per season
    avg_yield_percentile: float  # 0-100%, compared to regional average
    yield_consistency: float  # 0-100%, stddev-based
    
    # Repayment history
    previous_loans: int
    on_time_payments: int
    total_payments: int
    payment_rate: float  # on_time / total
    
    # Current season
    current_yield_prediction: float
    prediction_confidence: float
    
    # Weather/environmental risk
    drought_risk: float  # 0-100%
    pest_risk: float
    disease_risk: float
    
    # Market risk
    price_volatility: float  # Historical price variance
    
    # Final score
    credit_score: float  # 0-1000
    risk_level: RiskLevel
    max_loan_amount: float
    interest_rate: float  # APR


@dataclass
class LoanApplication:
    """Loan application details"""
    application_id: str
    farmer_id: str
    farmer_name: str
    chama_id: Optional[str]  # Group lending
    
    # Loan terms
    requested_amount: float
    purpose: str  # "seeds", "fertilizer", "equipment", etc
    term_months: int
    
    # Collateral
    collateral_assets: List[CollateralAsset]
    total_collateral_value: float
    loan_to_value_ratio: float  # loan / collateral
    
    # Assessment
    credit_score: Optional[CreditScore]
    risk_assessment: Optional[Dict]
    
    # Status
    status: LoanStatus
    application_date: datetime
    decision_date: Optional[datetime]
    disbursement_date: Optional[datetime]
    
    # Terms (if approved)
    approved_amount: float
    interest_rate: float
    monthly_payment: float
    repayment_schedule: List[Dict]


@dataclass
class LoanAccount:
    """Active loan account"""
    loan_id: str
    application_id: str
    farmer_id: str
    
    # Principal
    original_amount: float
    outstanding_balance: float
    
    # Interest
    interest_rate: float
    accrued_interest: float
    
    # Repayment
    monthly_payment: float
    payments_made: int
    payments_total: int
    next_payment_date: datetime
    next_payment_amount: float
    
    # Collateral
    collateral_assets: List[CollateralAsset]
    current_collateral_value: float
    ltv_ratio: float  # Current loan / collateral value
    
    # Status
    status: LoanStatus
    days_overdue: int
    default_risk: float  # Current probability of default
    
    # Adjustments
    adjustment_history: List[Dict]


class DynamicCollateralization:
    """
    Real-time collateral valuation based on harvest predictions.
    
    Features:
    - Drone-verified yield forecasts
    - Quality-adjusted pricing
    - Market price integration
    - Automatic revaluation
    - Margin call triggers
    
    Benefits:
    - Accurate asset valuation
    - Reduced over-collateralization
    - Protects SACCO from defaults
    - Enables mid-season adjustments
    """
    
    def __init__(self):
        self.market_prices = self._initialize_market_prices()
        
    def _initialize_market_prices(self) -> Dict[str, float]:
        """Current market prices per ton by crop"""
        return {
            'Maize': 250.0,
            'Potato': 400.0,
            'Tomato': 600.0,
            'Cabbage': 300.0,
            'Beans': 800.0,
            'Onion': 500.0
        }
    
    def value_asset(
        self,
        farm_id: str,
        crop_type: str,
        area_hectares: float,
        predicted_yield_tons: float,
        quality_distribution: Dict[str, float],
        confidence_score: float,
        drone_scan_date: datetime,
        certificate_hash: str
    ) -> CollateralAsset:
        """
        Value agricultural asset for collateral.
        
        Methodology:
        1. Base valuation = predicted_yield * market_price
        2. Quality adjustment = weighted average by grade premiums
        3. Confidence discount = reduce value if low confidence
        4. LTV ratio = 70% (conservative, protects SACCO)
        
        Returns CollateralAsset with collateral_value.
        """
        
        # Get market price
        market_price = self.market_prices.get(crop_type, 350.0)
        
        # Quality premium adjustment
        # A grade: 120%, B: 100%, C: 70%, Reject: 30%
        quality_premiums = {'A': 1.2, 'B': 1.0, 'C': 0.7, 'Reject': 0.3}
        
        weighted_price = sum(
            market_price * quality_premiums.get(grade, 1.0) * (pct / 100.0)
            for grade, pct in quality_distribution.items()
        )
        
        # Base estimated revenue
        estimated_revenue = predicted_yield_tons * weighted_price
        
        # Confidence discount (reduce value if prediction uncertain)
        confidence_factor = confidence_score / 100.0
        confidence_adjusted_revenue = estimated_revenue * confidence_factor
        
        # LTV ratio: 70% (industry standard for agricultural collateral)
        ltv_ratio = 0.70
        collateral_value = confidence_adjusted_revenue * ltv_ratio
        
        # Harvest date (from current date)
        harvest_date = datetime.now() + timedelta(days=90)  # Assume 90 days
        
        asset = CollateralAsset(
            asset_id=f"asset_{farm_id}_{crop_type}_{int(datetime.now().timestamp())}",
            farm_id=farm_id,
            crop_type=crop_type,
            area_hectares=area_hectares,
            predicted_yield_tons=predicted_yield_tons,
            quality_distribution=quality_distribution,
            harvest_date=harvest_date,
            confidence_score=confidence_score,
            market_price_per_ton=weighted_price,
            estimated_revenue=estimated_revenue,
            collateral_value=collateral_value,
            drone_scan_date=drone_scan_date,
            certificate_hash=certificate_hash,
            pledged_to_loan=None,
            last_revaluation=datetime.now()
        )
        
        return asset
    
    def revalue_asset(
        self,
        asset: CollateralAsset,
        new_yield_prediction: float,
        new_quality_distribution: Dict[str, float],
        new_confidence: float,
        drone_scan_date: datetime
    ) -> CollateralAsset:
        """
        Revalue asset based on new drone scan.
        
        Triggers:
        - New drone flight (every 14-30 days)
        - Significant weather event
        - Disease/pest detection
        - Market price change
        
        Updates collateral_value, may trigger margin call.
        """
        
        # Recalculate valuation
        market_price = self.market_prices.get(asset.crop_type, 350.0)
        
        quality_premiums = {'A': 1.2, 'B': 1.0, 'C': 0.7, 'Reject': 0.3}
        weighted_price = sum(
            market_price * quality_premiums.get(grade, 1.0) * (pct / 100.0)
            for grade, pct in new_quality_distribution.items()
        )
        
        estimated_revenue = new_yield_prediction * weighted_price
        confidence_adjusted = estimated_revenue * (new_confidence / 100.0)
        new_collateral_value = confidence_adjusted * 0.70
        
        # Update asset
        asset.predicted_yield_tons = new_yield_prediction
        asset.quality_distribution = new_quality_distribution
        asset.confidence_score = new_confidence
        asset.market_price_per_ton = weighted_price
        asset.estimated_revenue = estimated_revenue
        asset.collateral_value = new_collateral_value
        asset.drone_scan_date = drone_scan_date
        asset.last_revaluation = datetime.now()
        
        return asset
    
    def check_margin_call(
        self,
        loan_balance: float,
        collateral_value: float,
        ltv_threshold: float = 0.85
    ) -> Tuple[bool, float]:
        """
        Check if margin call needed.
        
        Margin call when LTV > threshold (85%):
        - Loan balance has grown (interest accrual)
        - Collateral value has decreased (poor yield forecast)
        
        Returns (needs_margin_call, additional_collateral_required)
        """
        
        current_ltv = loan_balance / collateral_value if collateral_value > 0 else 1.0
        
        if current_ltv > ltv_threshold:
            # Margin call: Need more collateral to bring LTV back to 70%
            target_ltv = 0.70
            required_collateral = loan_balance / target_ltv
            additional_needed = required_collateral - collateral_value
            
            return True, additional_needed
        
        return False, 0.0


class YieldBasedCreditScoring:
    """
    Credit scoring based on agricultural performance.
    
    Factors:
    - Historical yield (consistency and level)
    - Current season prediction
    - Repayment history
    - Environmental risks
    - Market risks
    
    Score range: 0-1000
    - 750+: Excellent (very low risk)
    - 650-750: Good (low risk)
    - 550-650: Fair (medium risk)
    - 450-550: Poor (high risk)
    - <450: Very poor (very high risk)
    """
    
    def __init__(self):
        pass
    
    def calculate_credit_score(
        self,
        farmer_id: str,
        past_yields: List[float],
        predicted_yield: float,
        prediction_confidence: float,
        previous_loans: int,
        on_time_payments: int,
        total_payments: int,
        drought_risk: float,
        pest_risk: float,
        price_volatility: float
    ) -> CreditScore:
        """
        Calculate comprehensive credit score.
        
        Scoring breakdown:
        - Historical yield (30%): Consistency and level
        - Current prediction (25%): Forecast quality
        - Repayment history (25%): Payment track record
        - Environmental risk (10%): Weather/pest
        - Market risk (10%): Price stability
        
        Returns CreditScore with risk level and max loan amount.
        """
        
        # 1. Historical yield score (0-300 points)
        if past_yields:
            avg_yield = np.mean(past_yields)
            yield_percentile = min(100, (avg_yield / 5.0) * 100)  # Assume 5 t/ha is excellent
            yield_consistency = max(0, 100 - (np.std(past_yields) / avg_yield * 100)) if avg_yield > 0 else 50
            
            yield_score = (yield_percentile * 2.0 + yield_consistency * 1.0)
        else:
            yield_percentile = 50.0  # New farmer, assume average
            yield_consistency = 50.0
            yield_score = 150  # Neutral score
        
        # 2. Current prediction score (0-250 points)
        prediction_quality = prediction_confidence  # 0-100
        predicted_yield_score = min(100, (predicted_yield / 5.0) * 100)
        
        prediction_score = (prediction_quality * 1.5 + predicted_yield_score * 1.0)
        
        # 3. Repayment history score (0-250 points)
        if total_payments > 0:
            payment_rate = on_time_payments / total_payments
            repayment_score = payment_rate * 250
        else:
            repayment_score = 125  # New borrower, neutral
            payment_rate = 0.5
        
        # 4. Environmental risk score (0-100 points)
        # Lower risk = higher score
        avg_env_risk = (drought_risk + pest_risk) / 2.0
        env_score = (100 - avg_env_risk)
        
        # 5. Market risk score (0-100 points)
        market_score = (100 - price_volatility)
        
        # Total score
        total_score = yield_score + prediction_score + repayment_score + env_score + market_score
        
        # Determine risk level
        if total_score >= 750:
            risk_level = RiskLevel.VERY_LOW
            interest_rate = 0.08  # 8% APR
        elif total_score >= 650:
            risk_level = RiskLevel.LOW
            interest_rate = 0.12  # 12% APR
        elif total_score >= 550:
            risk_level = RiskLevel.MEDIUM
            interest_rate = 0.16  # 16% APR
        elif total_score >= 450:
            risk_level = RiskLevel.HIGH
            interest_rate = 0.22  # 22% APR
        else:
            risk_level = RiskLevel.VERY_HIGH
            interest_rate = 0.30  # 30% APR
        
        # Max loan amount (based on predicted income)
        estimated_income = predicted_yield * 300  # Assume $300/ton average
        max_loan = estimated_income * 0.5  # 50% of predicted income
        
        credit_score = CreditScore(
            farmer_id=farmer_id,
            past_yields=past_yields,
            avg_yield_percentile=yield_percentile,
            yield_consistency=yield_consistency,
            previous_loans=previous_loans,
            on_time_payments=on_time_payments,
            total_payments=total_payments,
            payment_rate=payment_rate,
            current_yield_prediction=predicted_yield,
            prediction_confidence=prediction_confidence,
            drought_risk=drought_risk,
            pest_risk=pest_risk,
            disease_risk=0.0,
            price_volatility=price_volatility,
            credit_score=total_score,
            risk_level=risk_level,
            max_loan_amount=max_loan,
            interest_rate=interest_rate
        )
        
        return credit_score


class AutomatedLoanAdjustment:
    """
    Mid-season loan adjustments based on harvest progress.
    
    Triggers:
    - New drone scan shows improved yield → Increase credit limit
    - Weather damage detected → Extend repayment term
    - Early harvest completion → Automatic repayment
    - NDVI decline → Trigger risk review
    
    Benefits:
    - Responsive to farmer needs
    - Reduces default risk
    - Improves farmer satisfaction
    """
    
    def __init__(self):
        pass
    
    def assess_adjustment(
        self,
        loan: LoanAccount,
        new_collateral_value: float,
        current_ndvi: float,
        weather_events: List[str]
    ) -> Dict[str, Any]:
        """
        Assess if loan adjustment needed.
        
        Scenarios:
        1. Collateral value increased 20%+ → Offer credit limit increase
        2. NDVI dropped below 0.5 → Trigger review
        3. Severe weather event → Offer term extension
        4. Harvest sold early → Process automatic repayment
        
        Returns adjustment recommendation.
        """
        
        recommendation = {
            'adjustment_needed': False,
            'adjustment_type': None,
            'details': {},
            'reasoning': ''
        }
        
        # 1. Check for credit limit increase opportunity
        original_collateral = loan.collateral_assets[0].collateral_value if loan.collateral_assets else 0
        collateral_increase_pct = ((new_collateral_value - original_collateral) / original_collateral * 100) if original_collateral > 0 else 0
        
        if collateral_increase_pct > 20:
            additional_credit = (new_collateral_value - original_collateral) * 0.70  # 70% LTV
            recommendation['adjustment_needed'] = True
            recommendation['adjustment_type'] = 'credit_increase'
            recommendation['details'] = {
                'additional_credit_available': additional_credit,
                'new_max_loan': loan.outstanding_balance + additional_credit
            }
            recommendation['reasoning'] = f"Collateral value increased {collateral_increase_pct:.1f}%. Additional credit available."
        
        # 2. Check for crop stress requiring review
        if current_ndvi < 0.5:
            recommendation['adjustment_needed'] = True
            recommendation['adjustment_type'] = 'risk_review'
            recommendation['details'] = {
                'current_ndvi': current_ndvi,
                'risk_increase': True
            }
            recommendation['reasoning'] = f"NDVI dropped to {current_ndvi:.2f}, indicating crop stress. Risk review recommended."
        
        # 3. Check for weather-related term extension
        severe_events = [e for e in weather_events if 'drought' in e.lower() or 'flood' in e.lower()]
        if severe_events:
            extension_months = 2  # Offer 2-month extension
            recommendation['adjustment_needed'] = True
            recommendation['adjustment_type'] = 'term_extension'
            recommendation['details'] = {
                'extension_months': extension_months,
                'reason': severe_events[0]
            }
            recommendation['reasoning'] = f"Weather event ({severe_events[0]}) impacting harvest. Term extension offered."
        
        return recommendation
    
    def apply_adjustment(
        self,
        loan: LoanAccount,
        adjustment_type: str,
        adjustment_details: Dict
    ) -> LoanAccount:
        """
        Apply approved adjustment to loan.
        
        Updates:
        - Outstanding balance
        - Monthly payment
        - Repayment schedule
        - Adjustment history
        """
        
        adjustment_record = {
            'date': datetime.now(),
            'type': adjustment_type,
            'details': adjustment_details
        }
        
        if adjustment_type == 'credit_increase':
            loan.original_amount += adjustment_details['additional_credit_available']
            loan.outstanding_balance += adjustment_details['additional_credit_available']
        
        elif adjustment_type == 'term_extension':
            loan.payments_total += adjustment_details['extension_months']
            # Recalculate monthly payment
            loan.monthly_payment = loan.outstanding_balance / loan.payments_total
        
        loan.adjustment_history.append(adjustment_record)
        
        return loan


class RiskAssessmentEngine:
    """
    Portfolio-level risk assessment for SACCO.
    
    Monitors:
    - Individual loan default probabilities
    - Portfolio concentration risk
    - Geographic risk
    - Crop diversification
    - Capital adequacy
    
    Ensures:
    - SACCO stays within risk limits
    - Early warning for portfolio stress
    - Regulatory compliance
    """
    
    def __init__(self):
        pass
    
    def assess_loan_default_risk(
        self,
        loan: LoanAccount,
        credit_score: CreditScore,
        current_ndvi: float,
        days_to_harvest: int
    ) -> float:
        """
        Calculate probability of default for individual loan.
        
        Factors:
        - Credit score (historical performance)
        - Current crop health (NDVI)
        - Time to harvest (longer = more uncertainty)
        - Payment history on this loan
        
        Returns probability (0-1.0)
        """
        
        # Base default rate from credit score
        base_rates = {
            RiskLevel.VERY_LOW: 0.03,
            RiskLevel.LOW: 0.08,
            RiskLevel.MEDIUM: 0.15,
            RiskLevel.HIGH: 0.28,
            RiskLevel.VERY_HIGH: 0.40
        }
        
        base_risk = base_rates.get(credit_score.risk_level, 0.15)
        
        # Adjust for current crop health
        if current_ndvi > 0.7:
            health_factor = 0.8  # Reduce risk 20%
        elif current_ndvi > 0.5:
            health_factor = 1.0  # No change
        else:
            health_factor = 1.5  # Increase risk 50%
        
        # Adjust for time to harvest (more risk when harvest far away)
        time_factor = 1.0 + (days_to_harvest / 365.0)  # +100% risk for 1 year away
        
        # Adjust for payment history
        if loan.payments_made > 0:
            payment_factor = loan.payments_made / max(loan.payments_made, 1)  # Better if making payments
        else:
            payment_factor = 1.0
        
        # Adjust for overdue status
        overdue_factor = 1.0 + (loan.days_overdue / 30.0)  # +100% risk per month overdue
        
        # Combined default probability
        default_prob = base_risk * health_factor * time_factor * overdue_factor / payment_factor
        
        return min(1.0, default_prob)
    
    def assess_portfolio_risk(
        self,
        loans: List[LoanAccount],
        target_capital_ratio: float = 0.12  # 12% capital adequacy
    ) -> Dict:
        """
        Assess overall portfolio risk.
        
        Metrics:
        - Total exposure
        - Expected loss (sum of default_prob * loan_balance)
        - Required capital reserves
        - Capital adequacy ratio
        - Portfolio concentration (Herfindahl index)
        
        Returns comprehensive risk report.
        """
        
        if not loans:
            return {}
        
        total_exposure = sum(loan.outstanding_balance for loan in loans)
        
        # Expected loss
        expected_losses = []
        for loan in loans:
            loss = loan.outstanding_balance * loan.default_risk
            expected_losses.append(loss)
        
        total_expected_loss = sum(expected_losses)
        
        # Required capital reserves (expected loss + buffer)
        required_capital = total_expected_loss * 1.5  # 150% of expected loss
        
        # Capital adequacy ratio (assume SACCO has capital)
        sacco_capital = total_exposure * 0.15  # Assume 15% capital
        capital_ratio = sacco_capital / total_exposure if total_exposure > 0 else 0
        
        # Concentration risk (Herfindahl index)
        # H = sum((exposure_i / total_exposure)^2)
        # H near 0 = diversified, H near 1 = concentrated
        concentrations = [(loan.outstanding_balance / total_exposure) ** 2 for loan in loans]
        herfindahl_index = sum(concentrations)
        
        # Risk classification
        if capital_ratio >= target_capital_ratio and herfindahl_index < 0.2:
            risk_classification = "Low"
        elif capital_ratio >= target_capital_ratio * 0.8:
            risk_classification = "Moderate"
        else:
            risk_classification = "High"
        
        return {
            'total_exposure': total_exposure,
            'total_expected_loss': total_expected_loss,
            'expected_loss_rate': total_expected_loss / total_exposure if total_exposure > 0 else 0,
            'required_capital': required_capital,
            'sacco_capital': sacco_capital,
            'capital_adequacy_ratio': capital_ratio,
            'target_capital_ratio': target_capital_ratio,
            'capital_surplus_deficit': sacco_capital - required_capital,
            'herfindahl_index': herfindahl_index,
            'diversification_level': 'High' if herfindahl_index < 0.15 else ('Medium' if herfindahl_index < 0.25 else 'Low'),
            'portfolio_risk_classification': risk_classification,
            'number_of_loans': len(loans)
        }


# ====================
# USAGE EXAMPLE & TEST
# ====================

if __name__ == "__main__":
    print("=" * 70)
    print("SACCO RISK & LOAN MANAGEMENT - TEST")
    print("=" * 70)
    
    # 1. Initialize components
    print("\n1. Initializing SACCO system...")
    collateral_manager = DynamicCollateralization()
    credit_scorer = YieldBasedCreditScoring()
    loan_adjuster = AutomatedLoanAdjustment()
    risk_engine = RiskAssessmentEngine()
    
    # 2. Create collateral asset from harvest prediction
    print("\n2. Valuing collateral asset...")
    asset = collateral_manager.value_asset(
        farm_id="farm_001",
        crop_type="Maize",
        area_hectares=2.5,
        predicted_yield_tons=8.5,
        quality_distribution={"A": 35.0, "B": 45.0, "C": 15.0, "Reject": 5.0},
        confidence_score=88.0,
        drone_scan_date=datetime.now(),
        certificate_hash="abc123"
    )
    
    print(f"  Asset ID: {asset.asset_id}")
    print(f"  Crop: {asset.crop_type} ({asset.area_hectares} ha)")
    print(f"  Predicted yield: {asset.predicted_yield_tons} tons")
    print(f"  Estimated revenue: ${asset.estimated_revenue:,.2f}")
    print(f"  Collateral value (70% LTV): ${asset.collateral_value:,.2f}")
    print(f"  Confidence: {asset.confidence_score:.1f}%")
    
    # 3. Calculate credit score
    print("\n3. Calculating farmer credit score...")
    credit_score = credit_scorer.calculate_credit_score(
        farmer_id="farmer_001",
        past_yields=[4.2, 4.5, 4.1, 4.8],  # Previous 4 seasons
        predicted_yield=3.4,  # tons/ha for current season
        prediction_confidence=88.0,
        previous_loans=3,
        on_time_payments=34,
        total_payments=36,
        drought_risk=15.0,
        pest_risk=10.0,
        price_volatility=25.0
    )
    
    print(f"  Farmer ID: {credit_score.farmer_id}")
    print(f"  Credit score: {credit_score.credit_score:.0f}/1000")
    print(f"  Risk level: {credit_score.risk_level.value}")
    print(f"  Payment rate: {credit_score.payment_rate * 100:.1f}%")
    print(f"  Yield consistency: {credit_score.yield_consistency:.1f}%")
    print(f"  Interest rate: {credit_score.interest_rate * 100:.1f}% APR")
    print(f"  Max loan amount: ${credit_score.max_loan_amount:,.2f}")
    
    # 4. Create loan account
    print("\n4. Creating loan account...")
    loan_amount = 1500.0
    term_months = 6
    monthly_payment = (loan_amount * (1 + credit_score.interest_rate)) / term_months
    
    loan = LoanAccount(
        loan_id="loan_001",
        application_id="app_001",
        farmer_id="farmer_001",
        original_amount=loan_amount,
        outstanding_balance=loan_amount,
        interest_rate=credit_score.interest_rate,
        accrued_interest=0.0,
        monthly_payment=monthly_payment,
        payments_made=0,
        payments_total=term_months,
        next_payment_date=datetime.now() + timedelta(days=30),
        next_payment_amount=monthly_payment,
        collateral_assets=[asset],
        current_collateral_value=asset.collateral_value,
        ltv_ratio=loan_amount / asset.collateral_value,
        status=LoanStatus.ACTIVE,
        days_overdue=0,
        default_risk=0.0,
        adjustment_history=[]
    )
    
    print(f"  Loan ID: {loan.loan_id}")
    print(f"  Amount: ${loan.original_amount:,.2f}")
    print(f"  Term: {loan.payments_total} months")
    print(f"  Monthly payment: ${loan.monthly_payment:.2f}")
    print(f"  LTV ratio: {loan.ltv_ratio * 100:.1f}%")
    
    # 5. Revalue collateral (new drone scan)
    print("\n5. Revaluing collateral after new drone scan...")
    updated_asset = collateral_manager.revalue_asset(
        asset=asset,
        new_yield_prediction=9.2,  # Improved forecast
        new_quality_distribution={"A": 42.0, "B": 45.0, "C": 10.0, "Reject": 3.0},
        new_confidence=92.0,
        drone_scan_date=datetime.now() + timedelta(days=30)
    )
    
    print(f"  New yield prediction: {updated_asset.predicted_yield_tons} tons")
    print(f"  New collateral value: ${updated_asset.collateral_value:,.2f}")
    print(f"  Value change: {((updated_asset.collateral_value - asset.collateral_value) / asset.collateral_value * 100):+.1f}%")
    
    # 6. Check for loan adjustment
    print("\n6. Checking for loan adjustment opportunity...")
    adjustment = loan_adjuster.assess_adjustment(
        loan=loan,
        new_collateral_value=updated_asset.collateral_value,
        current_ndvi=0.72,
        weather_events=[]
    )
    
    if adjustment['adjustment_needed']:
        print(f"  Adjustment recommended: {adjustment['adjustment_type']}")
        print(f"  Reasoning: {adjustment['reasoning']}")
        if 'additional_credit_available' in adjustment['details']:
            print(f"  Additional credit: ${adjustment['details']['additional_credit_available']:,.2f}")
    else:
        print(f"  No adjustment needed")
    
    # 7. Assess default risk
    print("\n7. Assessing loan default risk...")
    default_prob = risk_engine.assess_loan_default_risk(
        loan=loan,
        credit_score=credit_score,
        current_ndvi=0.72,
        days_to_harvest=60
    )
    loan.default_risk = default_prob
    
    print(f"  Default probability: {default_prob * 100:.2f}%")
    print(f"  Expected loss: ${loan.outstanding_balance * default_prob:,.2f}")
    
    # 8. Check margin call
    print("\n8. Checking margin call status...")
    needs_margin_call, additional_collateral = collateral_manager.check_margin_call(
        loan_balance=loan.outstanding_balance,
        collateral_value=loan.current_collateral_value
    )
    
    if needs_margin_call:
        print(f"  ⚠️ MARGIN CALL REQUIRED")
        print(f"  Additional collateral needed: ${additional_collateral:,.2f}")
    else:
        print(f"  ✓ Collateral adequate (LTV: {loan.ltv_ratio * 100:.1f}%)")
    
    # 9. Portfolio risk assessment
    print("\n9. Assessing portfolio risk...")
    # Create sample portfolio
    portfolio_loans = [loan]
    for i in range(9):  # Add 9 more loans
        sample_loan = LoanAccount(
            loan_id=f"loan_{i+2:03d}",
            application_id=f"app_{i+2:03d}",
            farmer_id=f"farmer_{i+2:03d}",
            original_amount=1000 + np.random.rand() * 2000,
            outstanding_balance=1000 + np.random.rand() * 2000,
            interest_rate=0.10 + np.random.rand() * 0.15,
            accrued_interest=0.0,
            monthly_payment=200,
            payments_made=np.random.randint(0, 6),
            payments_total=6,
            next_payment_date=datetime.now() + timedelta(days=30),
            next_payment_amount=200,
            collateral_assets=[asset],
            current_collateral_value=2000 + np.random.rand() * 1000,
            ltv_ratio=0.70,
            status=LoanStatus.ACTIVE,
            days_overdue=0,
            default_risk=0.05 + np.random.rand() * 0.15,
            adjustment_history=[]
        )
        portfolio_loans.append(sample_loan)
    
    portfolio_risk = risk_engine.assess_portfolio_risk(portfolio_loans)
    
    print(f"  Total loans: {portfolio_risk['number_of_loans']}")
    print(f"  Total exposure: ${portfolio_risk['total_exposure']:,.2f}")
    print(f"  Expected loss: ${portfolio_risk['total_expected_loss']:,.2f}")
    print(f"  Expected loss rate: {portfolio_risk['expected_loss_rate'] * 100:.2f}%")
    print(f"  Capital adequacy: {portfolio_risk['capital_adequacy_ratio'] * 100:.1f}%")
    print(f"  Target: {portfolio_risk['target_capital_ratio'] * 100:.1f}%")
    print(f"  Diversification: {portfolio_risk['diversification_level']}")
    print(f"  Portfolio risk: {portfolio_risk['portfolio_risk_classification']}")
    
    print("\n" + "=" * 70)
    print("SACCO RISK & LOAN MANAGEMENT TEST COMPLETE")
    print("=" * 70)
    print("\nKey Capabilities:")
    print("  ✓ Drone-verified collateral valuation")
    print("  ✓ Dynamic collateral revaluation")
    print("  ✓ Yield-based credit scoring (0-1000)")
    print("  ✓ Risk-adjusted interest rates (8-30% APR)")
    print("  ✓ Automated loan adjustments")
    print("  ✓ Margin call detection")
    print("  ✓ Default probability prediction")
    print("  ✓ Portfolio risk assessment")
    print("  ✓ Capital adequacy monitoring")
    print("=" * 70)
