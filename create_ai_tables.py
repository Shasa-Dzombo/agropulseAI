"""
🌾 AgroPulse - AI System Database Migration

Creates all tables needed for the 4-tier AI system:
- Tier 1: Edge AI (Sentry alerts, grading manifests)
- Tier 2: Mobile AI (Diagnostic packets, image analysis)
- Tier 3: Cloud AI (Chatbot conversations, quantum optimizations)
- Tier 4: Community AI (Risk scores, market predictions, disputes)

Author: AgroPulse AI Team
Date: October 31, 2025
"""

import psycopg2
from psycopg2 import sql
import os
from datetime import datetime

# Database connection
DATABASE_URL = "postgresql://postgres:password@localhost/agropulse"

# SQL DDL for AI system tables
CREATE_AI_TABLES_SQL = """
-- ============================================================================
-- TIER 1: EDGE AI TABLES
-- ============================================================================

-- Sentry Stakes (ESP32-CAM devices)
CREATE TABLE IF NOT EXISTS sentry_stakes (
    id SERIAL PRIMARY KEY,
    sentry_id VARCHAR(50) UNIQUE NOT NULL,
    farm_id INTEGER REFERENCES farms(id) ON DELETE CASCADE,
    zone_name VARCHAR(100),
    gps_latitude DECIMAL(10, 8),
    gps_longitude DECIMAL(11, 8),
    crop_type VARCHAR(50),
    growth_stage VARCHAR(50),
    installation_date TIMESTAMP,
    last_reading_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    firmware_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sentry Alerts (crop health anomalies)
CREATE TABLE IF NOT EXISTS sentry_alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(50) UNIQUE NOT NULL,
    sentry_id VARCHAR(50) REFERENCES sentry_stakes(sentry_id),
    timestamp TIMESTAMP NOT NULL,
    ndvi_proxy DECIMAL(5, 3),
    deviation_score DECIMAL(5, 3),
    status VARCHAR(30),
    priority VARCHAR(20),
    rgb_values JSONB,
    preliminary_diagnosis TEXT,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sentry_alerts_timestamp ON sentry_alerts(timestamp DESC);
CREATE INDEX idx_sentry_alerts_priority ON sentry_alerts(priority);

-- Digital Manifests (grading belt output)
CREATE TABLE IF NOT EXISTS digital_manifests (
    id SERIAL PRIMARY KEY,
    manifest_id VARCHAR(50) UNIQUE NOT NULL,
    harvest_bundle_id INTEGER,
    farmer_id INTEGER,
    produce_type VARCHAR(50),
    total_count INTEGER,
    grade_a_count INTEGER DEFAULT 0,
    grade_b_count INTEGER DEFAULT 0,
    reject_count INTEGER DEFAULT 0,
    quality_score DECIMAL(5, 3),
    individual_results JSONB,
    manifest_hash VARCHAR(64),  -- SHA-256 for blockchain
    blockchain_tx_hash VARCHAR(66),  -- Ethereum transaction hash
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_manifests_farmer ON digital_manifests(farmer_id);
CREATE INDEX idx_manifests_hash ON digital_manifests(manifest_hash);

-- ============================================================================
-- TIER 2: MOBILE AI TABLES
-- ============================================================================

-- Diagnostic Packets (from mobile app scans)
CREATE TABLE IF NOT EXISTS diagnostic_packets (
    id SERIAL PRIMARY KEY,
    packet_id VARCHAR(100) UNIQUE NOT NULL,
    farmer_id INTEGER,
    crop_type VARCHAR(50),
    user_symptoms TEXT,
    gps_latitude DECIMAL(10, 8),
    gps_longitude DECIMAL(11, 8),
    super_resolution_image_url TEXT,
    stress_map_url TEXT,
    on_device_diagnosis JSONB,
    cloud_diagnosis JSONB,
    confidence_on_device DECIMAL(5, 3),
    confidence_cloud DECIMAL(5, 3),
    priority VARCHAR(20),
    status VARCHAR(30) DEFAULT 'pending',
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_diagnostics_farmer ON diagnostic_packets(farmer_id);
CREATE INDEX idx_diagnostics_status ON diagnostic_packets(status);
CREATE INDEX idx_diagnostics_created ON diagnostic_packets(created_at DESC);

-- Image Analysis Results
CREATE TABLE IF NOT EXISTS image_analysis_results (
    id SERIAL PRIMARY KEY,
    diagnostic_packet_id INTEGER REFERENCES diagnostic_packets(id) ON DELETE CASCADE,
    analysis_type VARCHAR(50),  -- 'computational_photography', 'stress_map', 'defect_detection'
    burst_frames_count INTEGER,
    aligned_frames_count INTEGER,
    alignment_success_rate DECIMAL(5, 3),
    detected_features JSONB,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TIER 3: CLOUD AI TABLES
-- ============================================================================

-- Chatbot Conversations
CREATE TABLE IF NOT EXISTS chatbot_conversations (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) UNIQUE NOT NULL,
    farmer_id INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    intents JSONB,  -- Array of classified intents
    status VARCHAR(20) DEFAULT 'active'
);

-- Chatbot Messages
CREATE TABLE IF NOT EXISTS chatbot_messages (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) REFERENCES chatbot_conversations(conversation_id),
    role VARCHAR(20),  -- 'user' or 'assistant'
    content TEXT,
    intent VARCHAR(50),
    rag_context JSONB,  -- Retrieved context from database
    actions JSONB,  -- Executed actions
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chatbot_messages_conversation ON chatbot_messages(conversation_id);
CREATE INDEX idx_chatbot_messages_timestamp ON chatbot_messages(timestamp DESC);

-- Quantum Optimization Jobs
CREATE TABLE IF NOT EXISTS quantum_optimization_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    job_type VARCHAR(50),  -- 'scouting_plan', 'harvest_logistics', 'group_buying'
    farmer_id INTEGER,
    chama_id INTEGER,
    qubo_matrix JSONB,
    solution_vector JSONB,
    optimization_metrics JSONB,
    status VARCHAR(30) DEFAULT 'pending',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    processing_time_seconds DECIMAL(10, 3)
);

CREATE INDEX idx_quantum_jobs_status ON quantum_optimization_jobs(status);
CREATE INDEX idx_quantum_jobs_farmer ON quantum_optimization_jobs(farmer_id);

-- Scouting Plans
CREATE TABLE IF NOT EXISTS scouting_plans (
    id SERIAL PRIMARY KEY,
    plan_id VARCHAR(100) UNIQUE NOT NULL,
    farmer_id INTEGER,
    optimization_job_id INTEGER REFERENCES quantum_optimization_jobs(id),
    alerts_to_visit INTEGER,
    total_distance_km DECIMAL(10, 2),
    estimated_cost_ksh DECIMAL(10, 2),
    estimated_time_hours DECIMAL(5, 2),
    roi DECIMAL(10, 2),
    route JSONB,  -- Array of waypoints
    status VARCHAR(30) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP
);

-- ============================================================================
-- TIER 4: COMMUNITY & FINANCIAL AI TABLES
-- ============================================================================

-- Risk Assessments (for loan applications)
CREATE TABLE IF NOT EXISTS risk_assessments (
    id SERIAL PRIMARY KEY,
    assessment_id VARCHAR(100) UNIQUE NOT NULL,
    member_id INTEGER,
    chama_id INTEGER,
    risk_score DECIMAL(5, 2),
    risk_category VARCHAR(20),
    component_scores JSONB,  -- savings, assets, yield, repayment
    loan_recommendation JSONB,
    behavioral_nudges JSONB,
    valid_until TIMESTAMP,  -- Risk scores expire after 30 days
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_risk_assessments_member ON risk_assessments(member_id);
CREATE INDEX idx_risk_assessments_chama ON risk_assessments(chama_id);
CREATE INDEX idx_risk_assessments_valid ON risk_assessments(valid_until);

-- Input Demand Forecasts
CREATE TABLE IF NOT EXISTS input_demand_forecasts (
    id SERIAL PRIMARY KEY,
    forecast_id VARCHAR(100) UNIQUE NOT NULL,
    chama_id INTEGER,
    forecast_period_days INTEGER DEFAULT 30,
    upcoming_plantings JSONB,
    input_demand JSONB,  -- DAP, CAN, seeds, pesticides
    group_buy_opportunities JSONB,
    recommendations JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_demand_forecasts_chama ON input_demand_forecasts(chama_id);

-- Market Price Predictions
CREATE TABLE IF NOT EXISTS market_price_predictions (
    id SERIAL PRIMARY KEY,
    prediction_id VARCHAR(100) UNIQUE NOT NULL,
    crop_type VARCHAR(50),
    quality_grade VARCHAR(20),
    harvest_date DATE,
    predicted_price_per_kg DECIMAL(10, 2),
    price_range_min DECIMAL(10, 2),
    price_range_max DECIMAL(10, 2),
    confidence DECIMAL(5, 3),
    market_intelligence JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_price_predictions_crop ON market_price_predictions(crop_type);
CREATE INDEX idx_price_predictions_date ON market_price_predictions(harvest_date);

-- Dispute Cases
CREATE TABLE IF NOT EXISTS ai_dispute_cases (
    id SERIAL PRIMARY KEY,
    dispute_id VARCHAR(100) UNIQUE NOT NULL,
    contract_hash VARCHAR(64),
    farmer_id INTEGER,
    buyer_id INTEGER,
    harvest_bundle_id INTEGER,
    manifest_id VARCHAR(50) REFERENCES digital_manifests(manifest_id),
    buyer_evidence JSONB,
    ai_decision VARCHAR(50),  -- 'favor_farmer', 'favor_buyer', 'partial', 'escalate'
    confidence DECIMAL(5, 3),
    reasoning TEXT,
    visual_similarity_score DECIMAL(5, 3),
    quality_discrepancy_percent DECIMAL(5, 2),
    recommended_resolution TEXT,
    status VARCHAR(30) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX idx_disputes_farmer ON ai_dispute_cases(farmer_id);
CREATE INDEX idx_disputes_status ON ai_dispute_cases(status);

-- ============================================================================
-- TRAINING DATA TABLES (for continuous ML improvement)
-- ============================================================================

-- Diagnosis Feedback (for model improvement)
CREATE TABLE IF NOT EXISTS diagnosis_feedback (
    id SERIAL PRIMARY KEY,
    diagnostic_packet_id INTEGER REFERENCES diagnostic_packets(id),
    farmer_satisfaction INTEGER CHECK (farmer_satisfaction BETWEEN 1 AND 5),
    treatment_effective BOOLEAN,
    actual_diagnosis VARCHAR(100),  -- If different from AI prediction
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Model Performance Metrics
CREATE TABLE IF NOT EXISTS model_performance_metrics (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100),
    model_version VARCHAR(20),
    metric_type VARCHAR(50),  -- 'accuracy', 'precision', 'recall', 'f1'
    metric_value DECIMAL(5, 4),
    evaluation_date DATE,
    sample_size INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_metrics_name ON model_performance_metrics(model_name);
CREATE INDEX idx_model_metrics_date ON model_performance_metrics(evaluation_date DESC);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sentry_stakes_updated_at BEFORE UPDATE ON sentry_stakes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""

def create_ai_tables():
    """Create all AI system tables."""
    try:
        print("🌾 Creating AgroPulse AI System tables...")
        print(f"Connecting to: {DATABASE_URL.split('@')[1]}")  # Hide password
        
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Execute SQL
        cursor.execute(CREATE_AI_TABLES_SQL)
        conn.commit()
        
        # Verify tables created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%sentry%' 
            OR table_name LIKE '%diagnostic%'
            OR table_name LIKE '%chatbot%'
            OR table_name LIKE '%quantum%'
            OR table_name LIKE '%risk%'
            OR table_name LIKE '%dispute%'
            OR table_name LIKE '%manifest%'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        
        print(f"\n✅ AI System tables created successfully!\n")
        print("AI System tables:")
        
        # Group tables by tier
        tier1 = [t[0] for t in tables if 'sentry' in t[0] or 'manifest' in t[0]]
        tier2 = [t[0] for t in tables if 'diagnostic' in t[0] or 'image_analysis' in t[0]]
        tier3 = [t[0] for t in tables if 'chatbot' in t[0] or 'quantum' in t[0] or 'scouting' in t[0]]
        tier4 = [t[0] for t in tables if 'risk' in t[0] or 'dispute' in t[0] or 'market' in t[0] or 'demand' in t[0]]
        training = [t[0] for t in tables if 'feedback' in t[0] or 'performance' in t[0]]
        
        if tier1:
            print("\n  📡 TIER 1: Edge AI")
            for table in tier1:
                print(f"    - {table}")
        
        if tier2:
            print("\n  📱 TIER 2: Mobile AI")
            for table in tier2:
                print(f"    - {table}")
        
        if tier3:
            print("\n  ☁️ TIER 3: Cloud AI")
            for table in tier3:
                print(f"    - {table}")
        
        if tier4:
            print("\n  👥 TIER 4: Community & Financial AI")
            for table in tier4:
                print(f"    - {table}")
        
        if training:
            print("\n  🎓 Training Data")
            for table in training:
                print(f"    - {table}")
        
        print(f"\nTotal: {len(tables)} AI tables")
        
        cursor.close()
        conn.close()
        
        print("\n🎯 Next steps:")
        print("  1. Start FastAPI server: uvicorn app.main:app --reload")
        print("  2. Test AI endpoints at: http://localhost:8000/docs")
        print("  3. Deploy edge devices (Sentry Stakes, Grading Belts)")
        print("  4. Configure mobile app AI features")
        print("  5. Train models with real data")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating AI tables: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Check PostgreSQL is running")
        print(f"  2. Verify database 'agropulse' exists")
        print(f"  3. Update DATABASE_URL in this script with correct password")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🌾 AgroPulse AI System Database Migration")
    print("=" * 60)
    
    success = create_ai_tables()
    
    if success:
        print("\n✅ AI system database migration complete!")
    else:
        print("\n❌ Migration failed. Please fix errors and try again.")
