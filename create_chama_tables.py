"""
Manual Database Migration Script for Digital Chama Models

Run this script to create the Digital Chama tables in your PostgreSQL database.

Usage:
    python create_chama_tables.py

Prerequisites:
    - PostgreSQL server running
    - Database 'agropulse' created
    - psycopg2 installed: pip install psycopg2-binary
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database connection string (update if needed)
DATABASE_URL = "postgresql://postgres:password@localhost/agropulse"

# SQL statements to create Digital Chama tables
CREATE_TABLES_SQL = """
-- ============================================================================
-- DIGITAL CHAMA TABLES
-- ============================================================================

-- Chama (Farmer Cooperative Groups)
CREATE TABLE IF NOT EXISTS chamas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    registration_number VARCHAR(100) UNIQUE,
    county VARCHAR(100) NOT NULL,
    sub_county VARCHAR(100),
    village VARCHAR(100),
    gps_latitude FLOAT,
    gps_longitude FLOAT,
    status VARCHAR(50) DEFAULT 'forming',
    founded_date TIMESTAMP DEFAULT NOW(),
    contribution_amount_ksh FLOAT DEFAULT 500.0,
    contribution_day_of_month INTEGER DEFAULT 5,
    late_payment_fine_percent FLOAT DEFAULT 10.0,
    loan_interest_rate_percent FLOAT DEFAULT 5.0,
    reputation_score FLOAT DEFAULT 0.0,
    verified_by_agropulse BOOLEAN DEFAULT FALSE,
    blockchain_identity_hash VARCHAR(66),
    total_members INTEGER DEFAULT 0,
    total_sacco_balance_ksh FLOAT DEFAULT 0.0,
    total_harvest_sales_ksh FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Chama Members
CREATE TABLE IF NOT EXISTS chama_members (
    id SERIAL PRIMARY KEY,
    chama_id INTEGER NOT NULL REFERENCES chamas(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    joined_date TIMESTAMP DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE,
    farm_name VARCHAR(200),
    farm_size_acres FLOAT,
    primary_crops JSONB,
    farm_gps_latitude FLOAT,
    farm_gps_longitude FLOAT,
    reputation_score FLOAT DEFAULT 50.0,
    total_contributions_ksh FLOAT DEFAULT 0.0,
    total_loans_taken_ksh FLOAT DEFAULT 0.0,
    total_loans_repaid_ksh FLOAT DEFAULT 0.0,
    total_fines_ksh FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chama_members_chama_id ON chama_members(chama_id);
CREATE INDEX IF NOT EXISTS idx_chama_members_user_id ON chama_members(user_id);

-- SACCO Accounts
CREATE TABLE IF NOT EXISTS sacco_accounts (
    id SERIAL PRIMARY KEY,
    chama_id INTEGER NOT NULL REFERENCES chamas(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL UNIQUE REFERENCES chama_members(id) ON DELETE CASCADE,
    account_number VARCHAR(50) UNIQUE NOT NULL,
    savings_balance_ksh FLOAT DEFAULT 0.0,
    loan_balance_ksh FLOAT DEFAULT 0.0,
    available_credit_ksh FLOAT DEFAULT 0.0,
    risk_score FLOAT DEFAULT 50.0,
    savings_consistency_score FLOAT DEFAULT 0.0,
    loan_repayment_score FLOAT DEFAULT 100.0,
    farm_asset_value_ksh FLOAT DEFAULT 0.0,
    predicted_annual_income_ksh FLOAT DEFAULT 0.0,
    account_status VARCHAR(50) DEFAULT 'active',
    last_contribution_date TIMESTAMP,
    consecutive_contributions INTEGER DEFAULT 0,
    missed_contributions INTEGER DEFAULT 0,
    active_loan BOOLEAN DEFAULT FALSE,
    loan_amount_ksh FLOAT DEFAULT 0.0,
    loan_disbursed_date TIMESTAMP,
    loan_due_date TIMESTAMP,
    loan_interest_rate_percent FLOAT DEFAULT 5.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sacco_accounts_chama_id ON sacco_accounts(chama_id);
CREATE INDEX IF NOT EXISTS idx_sacco_accounts_member_id ON sacco_accounts(member_id);

-- SACCO Transactions (Immutable Ledger)
CREATE TABLE IF NOT EXISTS sacco_transactions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES sacco_accounts(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES chama_members(id) ON DELETE CASCADE,
    transaction_type VARCHAR(50) NOT NULL,
    amount_ksh FLOAT NOT NULL,
    description TEXT,
    reference_number VARCHAR(100) UNIQUE NOT NULL,
    balance_after_ksh FLOAT NOT NULL,
    transaction_hash VARCHAR(66),
    blockchain_tx_hash VARCHAR(66),
    approved_by_member_id INTEGER,
    digital_signature TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sacco_transactions_account_id ON sacco_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_sacco_transactions_member_id ON sacco_transactions(member_id);
CREATE INDEX IF NOT EXISTS idx_sacco_transactions_timestamp ON sacco_transactions(timestamp);

-- Group Buys (Bulk Purchases)
CREATE TABLE IF NOT EXISTS group_buys (
    id SERIAL PRIMARY KEY,
    chama_id INTEGER NOT NULL REFERENCES chamas(id) ON DELETE CASCADE,
    product_name VARCHAR(200) NOT NULL,
    product_category VARCHAR(100) NOT NULL,
    product_unit VARCHAR(50) DEFAULT 'bag',
    unit_price_ksh FLOAT NOT NULL,
    bulk_discount_percent FLOAT DEFAULT 0.0,
    final_unit_price_ksh FLOAT NOT NULL,
    target_quantity INTEGER NOT NULL,
    current_quantity INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'open',
    deadline TIMESTAMP,
    vendor_name VARCHAR(200),
    vendor_contact VARCHAR(100),
    vendor_rating FLOAT,
    total_committed_ksh FLOAT DEFAULT 0.0,
    escrow_address VARCHAR(200),
    funds_released BOOLEAN DEFAULT FALSE,
    goods_confirmed BOOLEAN DEFAULT FALSE,
    confirmation_count INTEGER DEFAULT 0,
    ai_recommended BOOLEAN DEFAULT FALSE,
    predicted_demand INTEGER,
    created_by_member_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_group_buys_chama_id ON group_buys(chama_id);

-- Harvest Bundles (Marketplace)
CREATE TABLE IF NOT EXISTS harvest_bundles (
    id SERIAL PRIMARY KEY,
    chama_id INTEGER NOT NULL REFERENCES chamas(id) ON DELETE CASCADE,
    crop_type VARCHAR(100) NOT NULL,
    crop_variety VARCHAR(100),
    total_quantity_kg FLOAT DEFAULT 0.0,
    grade_a_quantity_kg FLOAT DEFAULT 0.0,
    grade_b_quantity_kg FLOAT DEFAULT 0.0,
    data_source VARCHAR(50) DEFAULT 'predicted',
    drone_scan_id INTEGER,
    confidence_score FLOAT DEFAULT 0.0,
    predicted_harvest_date TIMESTAMP,
    actual_harvest_date TIMESTAMP,
    asking_price_ksh_per_kg FLOAT,
    minimum_price_ksh_per_kg FLOAT,
    market_price_ksh_per_kg FLOAT,
    status VARCHAR(50) DEFAULT 'forecasted',
    listed_date TIMESTAMP,
    buyer_id INTEGER,
    buyer_name VARCHAR(200),
    sale_price_ksh_per_kg FLOAT,
    total_revenue_ksh FLOAT DEFAULT 0.0,
    smart_contract_address VARCHAR(200),
    escrow_amount_ksh FLOAT DEFAULT 0.0,
    funds_locked BOOLEAN DEFAULT FALSE,
    manifest_id INTEGER,
    manifest_hash VARCHAR(66),
    blockchain_verified BOOLEAN DEFAULT FALSE,
    quantum_matched BOOLEAN DEFAULT FALSE,
    optimization_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_harvest_bundles_chama_id ON harvest_bundles(chama_id);
CREATE INDEX IF NOT EXISTS idx_harvest_bundles_crop_type ON harvest_bundles(crop_type);

-- Equipment Bookings
CREATE TABLE IF NOT EXISTS equipment_bookings (
    id SERIAL PRIMARY KEY,
    chama_id INTEGER NOT NULL REFERENCES chamas(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES chama_members(id) ON DELETE CASCADE,
    equipment_type VARCHAR(100) NOT NULL,
    equipment_id VARCHAR(100),
    booking_date TIMESTAMP NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    duration_hours FLOAT NOT NULL,
    farm_gps_latitude FLOAT,
    farm_gps_longitude FLOAT,
    status VARCHAR(50) DEFAULT 'requested',
    ai_scheduled BOOLEAN DEFAULT FALSE,
    route_optimization_id VARCHAR(100),
    estimated_fuel_cost_ksh FLOAT,
    booking_fee_ksh FLOAT DEFAULT 0.0,
    payment_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_equipment_bookings_chama_id ON equipment_bookings(chama_id);
CREATE INDEX IF NOT EXISTS idx_equipment_bookings_booking_date ON equipment_bookings(booking_date);

-- Chat Messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    chama_id INTEGER NOT NULL REFERENCES chamas(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES chama_members(id) ON DELETE CASCADE,
    channel VARCHAR(100) DEFAULT 'general',
    message_text TEXT NOT NULL,
    image_url VARCHAR(500),
    ai_category VARCHAR(50),
    ai_confidence FLOAT,
    ai_tagged_officer BOOLEAN DEFAULT FALSE,
    ai_response TEXT,
    redirected_to VARCHAR(100),
    thread_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT NOW(),
    edited BOOLEAN DEFAULT FALSE,
    deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_chama_id ON chat_messages(chama_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp);

-- Reputation Scores
CREATE TABLE IF NOT EXISTS reputation_scores (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES chama_members(id) ON DELETE CASCADE,
    total_score FLOAT DEFAULT 50.0,
    financial_score FLOAT DEFAULT 50.0,
    agronomic_score FLOAT DEFAULT 50.0,
    quality_score FLOAT DEFAULT 50.0,
    commercial_score FLOAT DEFAULT 50.0,
    sacco_repayment_rate_percent FLOAT DEFAULT 100.0,
    consecutive_on_time_payments INTEGER DEFAULT 0,
    average_crop_grade VARCHAR(10),
    total_group_buys_participated INTEGER DEFAULT 0,
    total_harvests_delivered INTEGER DEFAULT 0,
    years_of_membership FLOAT DEFAULT 0.0,
    certification_level VARCHAR(50) DEFAULT 'Bronze',
    blockchain_reputation_hash VARCHAR(66),
    calculated_at TIMESTAMP DEFAULT NOW(),
    next_calculation_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reputation_scores_member_id ON reputation_scores(member_id);

-- Dispute Cases
CREATE TABLE IF NOT EXISTS dispute_cases (
    id SERIAL PRIMARY KEY,
    buyer_id INTEGER NOT NULL,
    chama_id INTEGER NOT NULL REFERENCES chamas(id) ON DELETE CASCADE,
    harvest_bundle_id INTEGER REFERENCES harvest_bundles(id) ON DELETE CASCADE,
    dispute_type VARCHAR(100) NOT NULL,
    claimed_issue TEXT NOT NULL,
    claimed_loss_ksh FLOAT DEFAULT 0.0,
    smart_contract_address VARCHAR(200),
    manifest_hash VARCHAR(66),
    grading_belt_images JSONB,
    buyer_submitted_images JSONB,
    blockchain_evidence_hash VARCHAR(66),
    status VARCHAR(50) DEFAULT 'pending',
    ai_reviewed BOOLEAN DEFAULT FALSE,
    ai_decision VARCHAR(100),
    ai_confidence FLOAT,
    ai_analysis JSONB,
    escalated BOOLEAN DEFAULT FALSE,
    arbitration_panel_ids JSONB,
    arbitration_votes JSONB,
    arbitration_decision VARCHAR(100),
    resolved BOOLEAN DEFAULT FALSE,
    resolution_summary TEXT,
    payout_buyer_percent FLOAT DEFAULT 0.0,
    payout_chama_percent FLOAT DEFAULT 100.0,
    filed_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dispute_cases_chama_id ON dispute_cases(chama_id);
CREATE INDEX IF NOT EXISTS idx_dispute_cases_harvest_bundle_id ON dispute_cases(harvest_bundle_id);

-- Create trigger for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_chamas_updated_at BEFORE UPDATE ON chamas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_chama_members_updated_at BEFORE UPDATE ON chama_members FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sacco_accounts_updated_at BEFORE UPDATE ON sacco_accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_group_buys_updated_at BEFORE UPDATE ON group_buys FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_harvest_bundles_updated_at BEFORE UPDATE ON harvest_bundles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_equipment_bookings_updated_at BEFORE UPDATE ON equipment_bookings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""

def main():
    """Create Digital Chama tables in PostgreSQL"""
    print("🌾 Creating Digital Chama tables...")
    print(f"Connecting to: {DATABASE_URL.replace('password', '***')}")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Execute SQL
        cursor.execute(CREATE_TABLES_SQL)
        
        # Verify tables created
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename LIKE '%chama%' OR tablename LIKE '%sacco%'
            ORDER BY tablename
        """)
        
        tables = cursor.fetchall()
        
        print("\n✅ Tables created successfully!")
        print("\nDigital Chama tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        print(f"\nTotal: {len(tables)} tables")
        
        cursor.close()
        conn.close()
        
        print("\n🎯 Next steps:")
        print("  1. Register Digital Chama API in main.py")
        print("  2. Start FastAPI server: uvicorn app.main:app --reload")
        print("  3. Test endpoints at: http://localhost:8000/docs")
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Database connection failed: {e}")
        print("\nPlease ensure:")
        print("  1. PostgreSQL server is running")
        print("  2. Database 'agropulse' exists")
        print("  3. Connection details in DATABASE_URL are correct")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
