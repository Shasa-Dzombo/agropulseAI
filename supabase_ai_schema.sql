-- ============================================================================
-- 🌾 AgroPulse AI System - Supabase Schema
-- ============================================================================
-- This SQL schema creates all tables for the 4-tier AI system in Supabase.
-- Run this in Supabase SQL Editor: https://app.supabase.com/project/_/sql
--
-- Date: October 31, 2025
-- ============================================================================

-- ============================================================================
-- TIER 1: EDGE AI TABLES
-- ============================================================================

-- Sentry Stakes (ESP32-CAM devices)
CREATE TABLE IF NOT EXISTS sentry_stakes (
    id BIGSERIAL PRIMARY KEY,
    sentry_id VARCHAR(50) UNIQUE NOT NULL,
    farm_id BIGINT,
    zone_name VARCHAR(100),
    gps_latitude DECIMAL(10, 8),
    gps_longitude DECIMAL(11, 8),
    crop_type VARCHAR(50),
    growth_stage VARCHAR(50),
    installation_date TIMESTAMPTZ,
    last_reading_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'active',
    firmware_version VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE sentry_stakes ENABLE ROW LEVEL SECURITY;

-- Sentry Alerts (crop health anomalies)
CREATE TABLE IF NOT EXISTS sentry_alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_id VARCHAR(50) UNIQUE NOT NULL,
    sentry_id VARCHAR(50) REFERENCES sentry_stakes(sentry_id),
    timestamp TIMESTAMPTZ NOT NULL,
    ndvi_proxy DECIMAL(5, 3),
    deviation_score DECIMAL(5, 3),
    status VARCHAR(30),
    priority VARCHAR(20),
    rgb_values JSONB,
    preliminary_diagnosis TEXT,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE sentry_alerts ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_sentry_alerts_timestamp ON sentry_alerts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sentry_alerts_priority ON sentry_alerts(priority);
CREATE INDEX IF NOT EXISTS idx_sentry_alerts_status ON sentry_alerts(status);

-- Digital Manifests (grading belt output)
CREATE TABLE IF NOT EXISTS digital_manifests (
    id BIGSERIAL PRIMARY KEY,
    manifest_id VARCHAR(50) UNIQUE NOT NULL,
    harvest_bundle_id BIGINT,
    farmer_id BIGINT,
    produce_type VARCHAR(50),
    total_count INTEGER,
    grade_a_count INTEGER DEFAULT 0,
    grade_b_count INTEGER DEFAULT 0,
    reject_count INTEGER DEFAULT 0,
    quality_score DECIMAL(5, 3),
    individual_results JSONB,
    manifest_hash VARCHAR(64),
    blockchain_tx_hash VARCHAR(66),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE digital_manifests ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_manifests_farmer ON digital_manifests(farmer_id);
CREATE INDEX IF NOT EXISTS idx_manifests_hash ON digital_manifests(manifest_hash);
CREATE INDEX IF NOT EXISTS idx_manifests_bundle ON digital_manifests(harvest_bundle_id);

-- ============================================================================
-- TIER 2: MOBILE AI TABLES
-- ============================================================================

-- Diagnostic Packets (from mobile app scans)
CREATE TABLE IF NOT EXISTS diagnostic_packets (
    id BIGSERIAL PRIMARY KEY,
    packet_id VARCHAR(100) UNIQUE NOT NULL,
    farmer_id BIGINT,
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
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE diagnostic_packets ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_diagnostics_farmer ON diagnostic_packets(farmer_id);
CREATE INDEX IF NOT EXISTS idx_diagnostics_status ON diagnostic_packets(status);
CREATE INDEX IF NOT EXISTS idx_diagnostics_created ON diagnostic_packets(created_at DESC);

-- Image Analysis Results
CREATE TABLE IF NOT EXISTS image_analysis_results (
    id BIGSERIAL PRIMARY KEY,
    diagnostic_packet_id BIGINT REFERENCES diagnostic_packets(id) ON DELETE CASCADE,
    analysis_type VARCHAR(50),
    burst_frames_count INTEGER,
    aligned_frames_count INTEGER,
    alignment_success_rate DECIMAL(5, 3),
    detected_features JSONB,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE image_analysis_results ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_image_analysis_packet ON image_analysis_results(diagnostic_packet_id);

-- ============================================================================
-- TIER 3: CLOUD AI TABLES
-- ============================================================================

-- Chatbot Conversations
CREATE TABLE IF NOT EXISTS chatbot_conversations (
    id BIGSERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) UNIQUE NOT NULL,
    farmer_id BIGINT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    message_count INTEGER DEFAULT 0,
    intents JSONB,
    status VARCHAR(20) DEFAULT 'active'
);

ALTER TABLE chatbot_conversations ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_conversations_farmer ON chatbot_conversations(farmer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON chatbot_conversations(status);

-- Chatbot Messages
CREATE TABLE IF NOT EXISTS chatbot_messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) REFERENCES chatbot_conversations(conversation_id),
    role VARCHAR(20),
    content TEXT,
    intent VARCHAR(50),
    rag_context JSONB,
    actions JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE chatbot_messages ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_chatbot_messages_conversation ON chatbot_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_messages_timestamp ON chatbot_messages(timestamp DESC);

-- Quantum Optimization Jobs
CREATE TABLE IF NOT EXISTS quantum_optimization_jobs (
    id BIGSERIAL PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    job_type VARCHAR(50),
    farmer_id BIGINT,
    chama_id BIGINT,
    qubo_matrix JSONB,
    solution_vector JSONB,
    optimization_metrics JSONB,
    status VARCHAR(30) DEFAULT 'pending',
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    processing_time_seconds DECIMAL(10, 3)
);

ALTER TABLE quantum_optimization_jobs ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_quantum_jobs_status ON quantum_optimization_jobs(status);
CREATE INDEX IF NOT EXISTS idx_quantum_jobs_farmer ON quantum_optimization_jobs(farmer_id);
CREATE INDEX IF NOT EXISTS idx_quantum_jobs_chama ON quantum_optimization_jobs(chama_id);

-- Scouting Plans
CREATE TABLE IF NOT EXISTS scouting_plans (
    id BIGSERIAL PRIMARY KEY,
    plan_id VARCHAR(100) UNIQUE NOT NULL,
    farmer_id BIGINT,
    optimization_job_id BIGINT REFERENCES quantum_optimization_jobs(id),
    alerts_to_visit INTEGER,
    total_distance_km DECIMAL(10, 2),
    estimated_cost_ksh DECIMAL(10, 2),
    estimated_time_hours DECIMAL(5, 2),
    roi DECIMAL(10, 2),
    route JSONB,
    status VARCHAR(30) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    executed_at TIMESTAMPTZ
);

ALTER TABLE scouting_plans ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_scouting_plans_farmer ON scouting_plans(farmer_id);
CREATE INDEX IF NOT EXISTS idx_scouting_plans_status ON scouting_plans(status);

-- ============================================================================
-- TIER 4: COMMUNITY & FINANCIAL AI TABLES
-- ============================================================================

-- Risk Assessments (for loan applications)
CREATE TABLE IF NOT EXISTS risk_assessments (
    id BIGSERIAL PRIMARY KEY,
    assessment_id VARCHAR(100) UNIQUE NOT NULL,
    member_id BIGINT,
    chama_id BIGINT,
    risk_score DECIMAL(5, 2),
    risk_category VARCHAR(20),
    component_scores JSONB,
    loan_recommendation JSONB,
    behavioral_nudges JSONB,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE risk_assessments ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_risk_assessments_member ON risk_assessments(member_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_chama ON risk_assessments(chama_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_valid ON risk_assessments(valid_until);

-- Input Demand Forecasts
CREATE TABLE IF NOT EXISTS input_demand_forecasts (
    id BIGSERIAL PRIMARY KEY,
    forecast_id VARCHAR(100) UNIQUE NOT NULL,
    chama_id BIGINT,
    forecast_period_days INTEGER DEFAULT 30,
    upcoming_plantings JSONB,
    input_demand JSONB,
    group_buy_opportunities JSONB,
    recommendations JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE input_demand_forecasts ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_demand_forecasts_chama ON input_demand_forecasts(chama_id);
CREATE INDEX IF NOT EXISTS idx_demand_forecasts_created ON input_demand_forecasts(created_at DESC);

-- Market Price Predictions
CREATE TABLE IF NOT EXISTS market_price_predictions (
    id BIGSERIAL PRIMARY KEY,
    prediction_id VARCHAR(100) UNIQUE NOT NULL,
    crop_type VARCHAR(50),
    quality_grade VARCHAR(20),
    harvest_date DATE,
    predicted_price_per_kg DECIMAL(10, 2),
    price_range_min DECIMAL(10, 2),
    price_range_max DECIMAL(10, 2),
    confidence DECIMAL(5, 3),
    market_intelligence JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE market_price_predictions ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_price_predictions_crop ON market_price_predictions(crop_type);
CREATE INDEX IF NOT EXISTS idx_price_predictions_date ON market_price_predictions(harvest_date);
CREATE INDEX IF NOT EXISTS idx_price_predictions_created ON market_price_predictions(created_at DESC);

-- AI Dispute Cases
CREATE TABLE IF NOT EXISTS ai_dispute_cases (
    id BIGSERIAL PRIMARY KEY,
    dispute_id VARCHAR(100) UNIQUE NOT NULL,
    contract_hash VARCHAR(64),
    farmer_id BIGINT,
    buyer_id BIGINT,
    harvest_bundle_id BIGINT,
    manifest_id VARCHAR(50) REFERENCES digital_manifests(manifest_id),
    buyer_evidence JSONB,
    ai_decision VARCHAR(50),
    confidence DECIMAL(5, 3),
    reasoning TEXT,
    visual_similarity_score DECIMAL(5, 3),
    quality_discrepancy_percent DECIMAL(5, 2),
    recommended_resolution TEXT,
    status VARCHAR(30) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

ALTER TABLE ai_dispute_cases ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_disputes_farmer ON ai_dispute_cases(farmer_id);
CREATE INDEX IF NOT EXISTS idx_disputes_buyer ON ai_dispute_cases(buyer_id);
CREATE INDEX IF NOT EXISTS idx_disputes_status ON ai_dispute_cases(status);
CREATE INDEX IF NOT EXISTS idx_disputes_manifest ON ai_dispute_cases(manifest_id);

-- ============================================================================
-- TRAINING DATA TABLES (for continuous ML improvement)
-- ============================================================================

-- Diagnosis Feedback
CREATE TABLE IF NOT EXISTS diagnosis_feedback (
    id BIGSERIAL PRIMARY KEY,
    diagnostic_packet_id BIGINT REFERENCES diagnostic_packets(id),
    farmer_satisfaction INTEGER CHECK (farmer_satisfaction BETWEEN 1 AND 5),
    treatment_effective BOOLEAN,
    actual_diagnosis VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE diagnosis_feedback ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_feedback_packet ON diagnosis_feedback(diagnostic_packet_id);

-- Model Performance Metrics
CREATE TABLE IF NOT EXISTS model_performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    model_name VARCHAR(100),
    model_version VARCHAR(20),
    metric_type VARCHAR(50),
    metric_value DECIMAL(5, 4),
    evaluation_date DATE,
    sample_size INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE model_performance_metrics ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_model_metrics_name ON model_performance_metrics(model_name);
CREATE INDEX IF NOT EXISTS idx_model_metrics_date ON model_performance_metrics(evaluation_date DESC);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for sentry_stakes
DROP TRIGGER IF EXISTS update_sentry_stakes_updated_at ON sentry_stakes;
CREATE TRIGGER update_sentry_stakes_updated_at 
    BEFORE UPDATE ON sentry_stakes
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Function to update conversation last_message_at
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chatbot_conversations 
    SET last_message_at = NEW.timestamp,
        message_count = message_count + 1
    WHERE conversation_id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for chatbot_messages
DROP TRIGGER IF EXISTS update_conversation_on_message ON chatbot_messages;
CREATE TRIGGER update_conversation_on_message
    AFTER INSERT ON chatbot_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_timestamp();

-- ============================================================================
-- ROW LEVEL SECURITY POLICIES (Basic policies - customize per requirements)
-- ============================================================================

-- Allow authenticated users to read their own data
CREATE POLICY "Users can view own data" ON sentry_stakes
    FOR SELECT USING (auth.uid()::text = farm_id::text);

CREATE POLICY "Users can view own alerts" ON sentry_alerts
    FOR SELECT USING (true);  -- Customize based on farm ownership

CREATE POLICY "Users can view own diagnostics" ON diagnostic_packets
    FOR SELECT USING (auth.uid()::text = farmer_id::text);

CREATE POLICY "Users can view own conversations" ON chatbot_conversations
    FOR SELECT USING (auth.uid()::text = farmer_id::text);

CREATE POLICY "Users can view own risk assessments" ON risk_assessments
    FOR SELECT USING (auth.uid()::text = member_id::text);

-- Allow service role full access (for backend operations)
CREATE POLICY "Service role has full access" ON sentry_stakes
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Repeat for other tables as needed...

-- ============================================================================
-- STORAGE BUCKETS (for images and files)
-- ============================================================================

-- Create storage bucket for diagnostic images
INSERT INTO storage.buckets (id, name, public)
VALUES ('diagnostic-images', 'diagnostic-images', false)
ON CONFLICT (id) DO NOTHING;

-- Create storage bucket for manifest images
INSERT INTO storage.buckets (id, name, public)
VALUES ('manifest-images', 'manifest-images', false)
ON CONFLICT (id) DO NOTHING;

-- Storage policies
CREATE POLICY "Authenticated users can upload diagnostic images"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'diagnostic-images');

CREATE POLICY "Users can view their diagnostic images"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'diagnostic-images');

-- ============================================================================
-- SUMMARY
-- ============================================================================
-- This schema creates 18 tables for the AgroPulse AI system:
--
-- TIER 1 (Edge AI): 3 tables
--   - sentry_stakes
--   - sentry_alerts  
--   - digital_manifests
--
-- TIER 2 (Mobile AI): 2 tables
--   - diagnostic_packets
--   - image_analysis_results
--
-- TIER 3 (Cloud AI): 4 tables
--   - chatbot_conversations
--   - chatbot_messages
--   - quantum_optimization_jobs
--   - scouting_plans
--
-- TIER 4 (Community & Financial AI): 4 tables
--   - risk_assessments
--   - input_demand_forecasts
--   - market_price_predictions
--   - ai_dispute_cases
--
-- TRAINING DATA: 2 tables
--   - diagnosis_feedback
--   - model_performance_metrics
--
-- Plus: Triggers, RLS policies, and storage buckets
-- ============================================================================
