-- KaushalVani Database Schema for PostgreSQL
-- Compliant with PM-AJAY Livelihood Framework & NSQF Qualification Standards

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users (Beneficiaries & Officials)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'beneficiary', -- 'beneficiary', 'official', 'admin'
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Beneficiaries
CREATE TABLE IF NOT EXISTS beneficiaries (
    id VARCHAR(100) PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    age INT CHECK (age >= 15 AND age <= 80),
    gender VARCHAR(50),
    location VARCHAR(255),
    district VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL DEFAULT 'Maharashtra',
    pincode VARCHAR(10),
    language VARCHAR(50) DEFAULT 'Marathi',
    education VARCHAR(100),
    current_occupation VARCHAR(255),
    previous_occupation VARCHAR(255),
    family_occupation VARCHAR(255),
    existing_skills TEXT[],
    experience_years INT DEFAULT 0,
    desired_occupation VARCHAR(255),
    interests TEXT[],
    employment_preference VARCHAR(50) DEFAULT 'wage', -- 'wage', 'self_employment', 'either'
    mobility_km INT DEFAULT 15,
    physical_constraints TEXT,
    digital_literacy VARCHAR(50) DEFAULT 'basic',
    income_category VARCHAR(100),
    status VARCHAR(50) DEFAULT 'profiled', -- 'draft', 'profiled', 'analyzed', 'enrolled', 'placed', 'self_employed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Qualifications (National Qualification Register - NQR)
CREATE TABLE IF NOT EXISTS qualifications (
    id VARCHAR(100) PRIMARY KEY,
    qp_code VARCHAR(100) UNIQUE NOT NULL,
    job_role VARCHAR(255) NOT NULL,
    sector VARCHAR(100) NOT NULL,
    nsqf_level INT NOT NULL CHECK (nsqf_level BETWEEN 1 AND 10),
    eligibility TEXT NOT NULL,
    education_req VARCHAR(255),
    experience_req TEXT,
    duration_hours INT NOT NULL,
    skills TEXT[] NOT NULL,
    nos_modules TEXT[],
    progression TEXT,
    awarding_body VARCHAR(255) NOT NULL,
    source_url TEXT NOT NULL,
    source_name VARCHAR(255) DEFAULT 'National Qualification Register (NQR)',
    last_verified_at DATE DEFAULT CURRENT_DATE
);

-- Training Providers & Centres (Skill India Digital)
CREATE TABLE IF NOT EXISTS training_centres (
    id VARCHAR(100) PRIMARY KEY,
    provider_name VARCHAR(255) NOT NULL,
    centre_name VARCHAR(255) NOT NULL,
    district VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    lat NUMERIC(9,6) NOT NULL,
    lng NUMERIC(9,6) NOT NULL,
    contact_phone VARCHAR(50),
    contact_email VARCHAR(100),
    courses TEXT[],
    source_url TEXT
);

-- Employment Opportunities (National Career Service)
CREATE TABLE IF NOT EXISTS employment_opportunities (
    id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    employer VARCHAR(255) NOT NULL,
    sector VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    lat NUMERIC(9,6),
    lng NUMERIC(9,6),
    salary_range VARCHAR(100),
    experience_req VARCHAR(255),
    education_req VARCHAR(255),
    vacancies INT DEFAULT 1,
    job_type VARCHAR(100) DEFAULT 'Full-Time Wage Employment',
    verified BOOLEAN DEFAULT TRUE,
    source_url TEXT
);

-- Enterprise & Self-Employment Pathways
CREATE TABLE IF NOT EXISTS enterprise_pathways (
    id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    sector VARCHAR(100) NOT NULL,
    suitable_for_skills TEXT[],
    min_education VARCHAR(100),
    equipment_required TEXT[],
    target_market TEXT,
    estimated_investment VARCHAR(100),
    potential_revenue VARCHAR(100),
    key_steps TEXT[],
    guidance_url TEXT
);

-- Recommendations
CREATE TABLE IF NOT EXISTS recommendations (
    id VARCHAR(100) PRIMARY KEY,
    beneficiary_id VARCHAR(100) REFERENCES beneficiaries(id) ON DELETE CASCADE,
    qualification_id VARCHAR(100) REFERENCES qualifications(id),
    score INT CHECK (score BETWEEN 0 AND 100),
    match_reasons JSONB,
    factors JSONB,
    skill_gap JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Livelihood Roadmaps
CREATE TABLE IF NOT EXISTS livelihood_roadmaps (
    id VARCHAR(100) PRIMARY KEY,
    beneficiary_id VARCHAR(100) REFERENCES beneficiaries(id) ON DELETE CASCADE,
    recommendation_id VARCHAR(100) REFERENCES recommendations(id),
    qualification_id VARCHAR(100) REFERENCES qualifications(id),
    pathway_type VARCHAR(50) DEFAULT 'wage',
    title VARCHAR(255) NOT NULL,
    steps JSONB NOT NULL,
    explanation TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Outcome Tracking
CREATE TABLE IF NOT EXISTS outcomes (
    id VARCHAR(100) PRIMARY KEY,
    beneficiary_id VARCHAR(100) REFERENCES beneficiaries(id) ON DELETE CASCADE,
    training_status VARCHAR(50) DEFAULT 'Not Started',
    completion_date DATE,
    certification_status VARCHAR(50) DEFAULT 'Pending',
    employment_status VARCHAR(50) DEFAULT 'Unemployed',
    enterprise_status VARCHAR(50) DEFAULT 'None',
    placement_date DATE,
    income_band VARCHAR(100),
    feedback TEXT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Indexes for Geospatial and Search Performance
CREATE INDEX IF NOT EXISTS idx_beneficiaries_district ON beneficiaries(district);
CREATE INDEX IF NOT EXISTS idx_beneficiaries_status ON beneficiaries(status);
CREATE INDEX IF NOT EXISTS idx_qualifications_sector ON qualifications(sector);
CREATE INDEX IF NOT EXISTS idx_training_centres_district ON training_centres(district);
CREATE INDEX IF NOT EXISTS idx_employment_opportunities_district ON employment_opportunities(district);
