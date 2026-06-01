-- ============================================================
-- BRAHMO Governance Engine — SEED DATA
-- Run this SECOND in Supabase SQL Editor (after schema.sql)
-- Loads: 1 org, 8 hierarchy levels, 5 users,
--        20 knowledge nodes, DERIVED_FROM cascade tree
-- ============================================================

-- ----- ORGANIZATION (with cascade depth + health weights config) -----
INSERT INTO organizations (id, name, config) VALUES
('supra', 'Supra Multi-Specialty Hospital',
 '{"cascade_max_depth": 3, "health_score_weights": {"coverage": 0.25, "freshness": 0.30, "balance": 0.20, "consistency": 0.25}}');

-- ----- HIERARCHY LEVELS (8 levels — used for Coverage dimension) -----
INSERT INTO hierarchy_levels (id, org_id, level_number, level_name, department) VALUES
('HL-01',        'supra', 1,  'Hospital',          NULL),
('HL-03',        'supra', 3,  'Clinical Division', NULL),
('HL-05-MED',    'supra', 5,  'Gen Medicine Dept', 'medicine'),
('HL-05-ORTHO',  'supra', 5,  'Orthopaedics Dept', 'ortho'),
('HL-08-MED',    'supra', 8,  'Medicine General',  'medicine'),
('HL-08-ORTHO',  'supra', 8,  'Ortho General',     'ortho'),
('HL-10-MED',    'supra', 10, 'Medicine Ward',     'medicine'),
('HL-10-ORTHO',  'supra', 10, 'Ortho Ward',        'ortho');

-- ----- USERS (5 staff — drives notification routing) -----
INSERT INTO users (id, org_id, name, role, department) VALUES
('U-MEERA',  'supra', 'Dr. Meera (HOD Medicine)', 'HOD',    'medicine'),
('U-ANANYA', 'supra', 'Dr. Ananya (Junior)',      'EDITOR', 'medicine'),
('U-VIKRAM', 'supra', 'Dr. Vikram (HOD Ortho)',   'HOD',    'ortho'),
('U-PRIYA',  'supra', 'Nurse Priya',              'VIEWER', 'ortho'),
('U-SURESH', 'supra', 'Admin Suresh',             'ADMIN',  'admin');

-- ============================================================
-- 20 KNOWLEDGE NODES
-- ============================================================

-- ----- THE NODE TO SUPERSEDE (Sepsis v2 → triggers cascade) -----
INSERT INTO knowledge_nodes (id, org_id, hierarchy_level_id, type, title, content, importance, status, department, created_by, created_at) VALUES
('N-M08', 'supra', 'HL-05-MED', 'DECISION', 'Sepsis Protocol v2 (2024)',
 'Supra Sepsis Bundle v2 (2024): blood cultures before antibiotics, lactate within 3 HOURS, 30mL/kg crystalloid for hypotension.',
 0.95, 'ACTIVE', 'medicine', 'U-MEERA', '2024-03-01 10:00:00+05:30');

-- NOTE: Sepsis v3 is NOT pre-loaded. The demo CREATES it via SUPERSEDE action.

-- ----- 6 DEPTH-1 DERIVED_FROM CHILDREN -----
INSERT INTO knowledge_nodes (id, org_id, hierarchy_level_id, type, title, content, importance, status, department, created_by, created_at) VALUES
('N-DRV-01', 'supra', 'HL-08-MED', 'DECISION', 'Lactate Monitoring Schedule',
 'Lactate levels monitored per Sepsis v2 protocol: every 3 hours for suspected sepsis patients. ICU escalation if lactate > 4 mmol/L.',
 0.78, 'ACTIVE', 'medicine', 'U-ANANYA', '2024-05-10 11:00:00+05:30'),

('N-DRV-02', 'supra', 'HL-08-MED', 'DECISION', 'Night Shift Sepsis Screening',
 'Night shift nurses screen for sepsis using qSOFA (based on Sepsis v2 parameters): altered mentation, RR >= 22, SBP <= 100.',
 0.75, 'ACTIVE', 'medicine', 'U-MEERA', '2024-06-20 08:00:00+05:30'),

('N-DRV-03', 'supra', 'HL-08-MED', 'DECISION', 'Empiric Antibiotic Selection',
 'Based on Sepsis v2 bundle: Piperacillin-Tazobactam 4.5g IV within 3-hour window. Culture-guided de-escalation at 72 hours.',
 0.82, 'ACTIVE', 'medicine', 'U-MEERA', '2024-07-05 15:00:00+05:30'),

('N-DRV-04', 'supra', 'HL-05-MED', 'DECISION', 'ICU Admission from Sepsis Screening',
 'Patients meeting 2/3 qSOFA criteria with lactate > 2 mmol/L: assess for ICU admission within 1 hour.',
 0.80, 'ACTIVE', 'medicine', 'U-ANANYA', '2024-08-12 10:00:00+05:30'),

('N-DRV-05', 'supra', 'HL-05-MED', 'FACT', 'Sepsis Mortality Tracking',
 'Supra sepsis mortality Q3 2024: 18% (national average 22%). Improvement attributed to v2 bundle compliance reaching 78%.',
 0.60, 'ACTIVE', 'medicine', 'U-MEERA', '2024-10-01 09:00:00+05:30'),

('N-DRV-06', 'supra', 'HL-10-MED', 'DECISION', 'Pharmacy Pre-Auth for IV Antibiotics',
 'Per Sepsis v2 timing: pharmacy pre-authorizes Pip-Tazo for suspected sepsis. No approval delay within 3-hour window.',
 0.72, 'ACTIVE', 'medicine', 'U-ANANYA', '2024-11-15 14:00:00+05:30');

-- ----- 3 DEPTH-2 GRANDCHILDREN (derived from DRV-04 and DRV-02) -----
INSERT INTO knowledge_nodes (id, org_id, hierarchy_level_id, type, title, content, importance, status, department, created_by, created_at) VALUES
('N-DRV-04-A', 'supra', 'HL-08-MED', 'DECISION', 'ICU Bed Reservation Protocol',
 'Based on ICU admission criteria (N-DRV-04): reserve 2 ICU beds per shift for suspected sepsis admissions.',
 0.65, 'ACTIVE', 'medicine', 'U-ANANYA', '2025-01-20 10:00:00+05:30'),

('N-DRV-04-B', 'supra', 'HL-10-MED', 'FACT', 'ICU Occupancy from Sepsis Admissions',
 'ICU sepsis admissions average 3 per week (2024). Peak: 7 in monsoon season (water-borne infections).',
 0.55, 'ACTIVE', 'medicine', 'U-MEERA', '2025-02-15 09:00:00+05:30'),

('N-DRV-02-A', 'supra', 'HL-10-MED', 'DECISION', 'Night Shift Escalation Timing',
 'Night shift sepsis screening positive: call duty doctor within 15 minutes. If no response: escalate to HOD within 30 minutes.',
 0.70, 'ACTIVE', 'medicine', 'U-ANANYA', '2025-03-01 08:00:00+05:30');

-- ----- LEGAL_HOLD NODE (in cascade path — must be SKIPPED) -----
INSERT INTO knowledge_nodes (id, org_id, hierarchy_level_id, type, title, content, importance, status, department, created_by, created_at) VALUES
('N-HELD', 'supra', 'HL-08-MED', 'DECISION', 'Sepsis Bundle Compliance Audit Data',
 'Compliance data under medico-legal review: v2 bundle adherence was 78% in Q3 2024. Two adverse outcomes under investigation.',
 0.75, 'LEGAL_HOLD', 'medicine', 'U-MEERA', '2024-09-01 10:00:00+05:30');

-- ----- UNRELATED MEDICINE NODES (NOT affected by cascade) -----
INSERT INTO knowledge_nodes (id, org_id, hierarchy_level_id, type, title, content, importance, status, department, created_by, created_at) VALUES
('N-M01', 'supra', 'HL-05-MED', 'CONSTRAINT', 'Diabetic Fasting Protocol',
 'Fasting diabetic patients: adjust insulin timing not dose. Skip Glimepiride on fast days.',
 0.90, 'ACTIVE', 'medicine', 'U-MEERA', '2025-06-01 09:00:00+05:30'),

('N-M03', 'supra', 'HL-05-MED', 'ANTI_PATTERN', 'Insulin Sliding Scale Alone',
 'Do NOT use sliding scale as sole glycemic management. Always include basal insulin.',
 0.87, 'ACTIVE', 'medicine', 'U-ANANYA', '2025-07-15 14:00:00+05:30');

-- ----- ORTHO NODES (different dept — for surprise test) -----
INSERT INTO knowledge_nodes (id, org_id, hierarchy_level_id, type, title, content, importance, status, department, created_by, created_at) VALUES
('N-O01', 'supra', 'HL-05-ORTHO', 'CONSTRAINT', 'DVT Prophylaxis Protocol',
 'ALL ortho surgical patients: Enoxaparin 40mg SC daily. TKR 14d, THR 28d.',
 0.93, 'ACTIVE', 'ortho', 'U-VIKRAM', '2025-04-01 10:00:00+05:30'),

('N-O02', 'supra', 'HL-08-ORTHO', 'DECISION', 'Paracetamol First-Line Post-TKR',
 'Paracetamol 650mg QDS first-line. Tramadol if VAS > 6. No NSAIDs.',
 0.88, 'ACTIVE', 'ortho', 'U-VIKRAM', '2025-01-20 11:00:00+05:30'),

('N-O03', 'supra', 'HL-08-ORTHO', 'DECISION', 'PT Within 24 Hours Post-TKR',
 'Physiotherapy must begin within 24 hours of TKR. Day 1: ankle pumps.',
 0.90, 'ACTIVE', 'ortho', 'U-VIKRAM', '2025-03-10 08:00:00+05:30'),

('N-O04', 'supra', 'HL-10-ORTHO', 'FACT', 'Ortho Ward Capacity',
 'Ortho Ward: 45 beds. 85-90% occupancy. Overflow to Medicine in winter.',
 0.50, 'ACTIVE', 'ortho', 'U-VIKRAM', '2025-05-01 09:00:00+05:30');

-- ----- EXPIRED NODE (for Freshness dimension) -----
INSERT INTO knowledge_nodes (id, org_id, hierarchy_level_id, type, title, content, importance, status, department, created_by, created_at) VALUES
('N-EXP', 'supra', 'HL-05-MED', 'FACT', 'Antibiotic Sensitivity Report Q2 2024',
 'E. coli sensitivity to Pip-Tazo: 89%. K. pneumoniae: 72%. Based on 2024 Q2 data.',
 0.55, 'EXPIRED', 'medicine', 'U-MEERA', '2024-07-01 09:00:00+05:30');

UPDATE knowledge_nodes SET valid_until = '2025-01-01 00:00:00+05:30' WHERE id = 'N-EXP';

-- ============================================================
-- DERIVED_FROM EDGES (the cascade tree) + non-cascade edges
-- ============================================================
INSERT INTO edges (source_id, target_id, edge_type) VALUES
-- Depth 1: 6 direct children of Sepsis v2
('N-DRV-01', 'N-M08', 'DERIVED_FROM'),
('N-DRV-02', 'N-M08', 'DERIVED_FROM'),
('N-DRV-03', 'N-M08', 'DERIVED_FROM'),
('N-DRV-04', 'N-M08', 'DERIVED_FROM'),
('N-DRV-05', 'N-M08', 'DERIVED_FROM'),
('N-DRV-06', 'N-M08', 'DERIVED_FROM'),

-- Depth 2: grandchildren
('N-DRV-04-A', 'N-DRV-04', 'DERIVED_FROM'),
('N-DRV-04-B', 'N-DRV-04', 'DERIVED_FROM'),
('N-DRV-02-A', 'N-DRV-02', 'DERIVED_FROM'),

-- LEGAL_HOLD node also derived from Sepsis v2 (will be skipped)
('N-HELD', 'N-M08', 'DERIVED_FROM'),

-- SUPPORTS edges (must NOT trigger cascade)
('N-M01', 'N-DRV-01', 'SUPPORTS'),
('N-O01', 'N-O02', 'SUPPORTS'),

-- Ortho cascade tree (for surprise test): O02 & O03 derived from O01
('N-O02', 'N-O01', 'DERIVED_FROM'),
('N-O03', 'N-O01', 'DERIVED_FROM');

-- ============================================================
-- VERIFY (run these after):
--   SELECT COUNT(*) FROM knowledge_nodes;                          -- expect 20
--   SELECT COUNT(*) FROM edges WHERE edge_type = 'DERIVED_FROM';   -- expect 12
--   SELECT COUNT(*) FROM users;                                    -- expect 5
-- ============================================================
