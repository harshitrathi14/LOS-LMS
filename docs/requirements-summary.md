# LOS/LMS Requirements Summary (Draft)

This repository currently contains requirements PDFs for a unified Loan Origination System (LOS)
plus Loan Management System (LMS). The notes below are a short, working summary to guide
initial architecture and scaffolding decisions.

## Core goals
- Unified LOS and LMS on one platform, API-first, modular, and configuration-driven.
- Support retail, SME/corporate, co-lending, supply chain finance, and securitization.
- Deployable on-prem or cloud (containerized), multi-tenant ready.
- Strong security, compliance, auditability, and RBAC.

## LOS (origination) highlights
- Multi-channel intake (web, mobile, branch, partner platforms).
- KYC/AML and verification workflows with document management and e-sign.
- Automated credit decisioning with policy rules and manual review queues.
- Product configurability (dynamic application forms per product).
- Co-lending origination with partner allocations and consolidated decisions.
- Workflow tasks, notifications, and applicant status tracking.

## LMS (servicing) highlights
- Loan onboarding and account setup post-approval.
- Amortization schedules with multiple repayment structures and frequencies.
- Interest accrual with multiple day-count conventions and posting rules.
- Payments, allocations, partials, prepayments, rescheduling and restructuring.
- Delinquency tracking (DPD, buckets), collections workflows, penalties, and fees.
- Support for revolving facilities and invoice-linked loans (SCF).

## Cross-cutting needs
- Multi-lender cash flow splits and partner ledgers for co-lending.
- Securitization pools, cash flow routing, and investor reporting.
- Integration points for credit bureaus, KYC services, payment gateways, and ERPs.
- Complete audit trail with timestamps and user IDs.

## Early architecture direction
- Backend: Python FastAPI (API-first) with SQLAlchemy and PostgreSQL.
- Modular domains: borrowers, products, applications, loans, payments, collections.
- Event hooks for workflow notifications and integrations.
- Config tables for rules (fees, interest, schedules, penalties) rather than hardcoded logic.
