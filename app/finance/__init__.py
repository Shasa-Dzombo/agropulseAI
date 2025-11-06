"""
SACCO Risk & Loan Management System
===================================

Dynamic loan collateralization based on drone-verified harvests.

Author: AgroPulse Team
Version: 1.0.0
"""

from .sacco import (
    DynamicCollateralization,
    YieldBasedCreditScoring,
    AutomatedLoanAdjustment,
    RiskAssessmentEngine,
    LoanApplication,
    CollateralAsset
)

__all__ = [
    'DynamicCollateralization',
    'YieldBasedCreditScoring',
    'AutomatedLoanAdjustment',
    'RiskAssessmentEngine',
    'LoanApplication',
    'CollateralAsset'
]

__version__ = '1.0.0'
