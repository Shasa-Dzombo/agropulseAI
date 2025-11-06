"""
AI-Powered Dispute Resolution System
====================================

Automated dispute resolution for marketplace transactions using:
- Computer vision comparison
- Immutable evidence locker
- AI adjudicator
- Decentralized arbitration

Author: AgroPulse Team
Version: 1.0.0
"""

from .disputes import (
    ImmutableEvidenceLocker,
    AIAdjudicator,
    DecentralizedArbitration,
    DisputeAnalytics,
    DisputeCase,
    EvidencePackage
)

__all__ = [
    'ImmutableEvidenceLocker',
    'AIAdjudicator',
    'DecentralizedArbitration',
    'DisputeAnalytics',
    'DisputeCase',
    'EvidencePackage'
]

__version__ = '1.0.0'
