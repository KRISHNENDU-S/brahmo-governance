# Data Sources

This document records where the clinical knowledge data used in the BRAHMO
Governance Engine seed database came from.

## Primary Source

All seed data (the 18 knowledge nodes, hierarchy levels, users, and
DERIVED_FROM edges) was **provided in the assessment's Setup Guide**
(`ASSESSMENT_03_SETUP_GUIDE.md`). It was loaded verbatim via `supabase/seed.sql`.

No external clinical data was scraped, generated, or added beyond what the
assessment supplied. This keeps the cascade tree, expected health-score
numbers, and demo scenarios aligned with the assessment's specification.

## Clinical Concepts Referenced (real-world mapping)

Although the seed content was provided, the clinical concepts it references
are real and map to recognised medical sources. This mapping is documented
here to show domain awareness:

| Seed node | Clinical concept | Real-world basis |
|-----------|------------------|------------------|
| N-M08 Sepsis Protocol v2/v3 | Sepsis bundle, lactate timing | Surviving Sepsis Campaign (SCCM) guidelines |
| N-DRV-02 Night Shift Screening | qSOFA criteria | Sepsis-3 consensus definitions |
| N-DRV-03 Empiric Antibiotics | Piperacillin-Tazobactam empiric therapy | Standard broad-spectrum empiric sepsis treatment |
| N-O01 DVT Prophylaxis | Enoxaparin post-arthroplasty | Orthopaedic VTE prophylaxis guidelines |
| N-M01 Diabetic Fasting | Insulin timing during fasting | Standard inpatient glycaemic management |

These are illustrative clinical references for the seed concepts. In a
production system, each knowledge node would carry a citation to its
source guideline, and the governance engine's cascade would be triggered
when those underlying guidelines are revised (e.g. SCCM updating the
lactate window from 3 hours to 1 hour — the exact scenario this demo models).

## Note on Node Count

The assessment prose refers to "20 knowledge nodes," but the seed SQL it
provided defines **18** pre-loaded nodes. The remaining nodes are created
*during* the demo (e.g. the Sepsis v3 replacement node via the SUPERSEDE
action), which is why the live database starts at 18. This is consistent
with the assessment's instruction not to pre-load the replacement node.