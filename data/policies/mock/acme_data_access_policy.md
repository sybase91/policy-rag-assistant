# Acme Corp Data Access Policy

Policy Owner: Information Security and Legal  
Effective Date: 2026-01-01  
Version: 2.0  
Applies To: All Acme Corp employees, contractors, and approved third parties  
Related Policies: Approval Matrix, Remote Work Policy  
Systems of Record: Access Management Portal, Vendor Risk Register

## DA-001 Purpose

This policy defines how Acme Corp classifies, accesses, shares, and protects company and customer data using need-to-know and least-privilege principles inspired by common enterprise security practice.

## DA-002 Scope

This policy applies to all systems, files, databases, analytics environments, vendor transfers, and AI tools handling Acme data.

## DA-003 Customer Data

Customer data includes personal data, account data, usage data, and support records relating to Acme customers. Internal access requires business need and appropriate role. External sharing requires business owner, Legal, and Information Security approval, a data processing agreement, and vendor security review.

## DA-004 HR Data

Employee HR data is Restricted. Access is limited to HR and authorized managers for legitimate employment purposes. External sharing with vendors requires HR data owner, Legal, and Information Security approval.

## DA-005 Finance Data

Finance reports, payroll interfaces, and accounting records are Confidential or Restricted. Access requires finance data owner approval and documented business purpose.

## DA-006 Data Classification Overview

Acme uses four classifications: Public, Internal, Confidential, and Restricted. Higher classifications require stronger controls and approvals.

## DA-007 External Sharing Controls

External sharing of Confidential or Restricted data requires business justification, data owner approval, classification review, data processing agreement, vendor security review, approved transfer method, minimum necessary data, and retention or deletion terms.

## DA-008 Security Escalation

Suspected unauthorized access, wrong recipient, public link exposure, vendor oversharing, or upload to unapproved AI tools must be reported immediately to Information Security.

## DA-009 Prohibited Actions

Employees must not use personal email, personal cloud storage, USB drives, public links, unapproved AI tools, or personal chat apps for Confidential, Restricted, customer, HR, or finance data.

## DA-010 Escalation

High-risk data incidents escalate to Information Security, Legal, Compliance, and the business executive sponsor.

## DA-011 Core Principles

Need to know, least privilege, data minimization, approved systems only, and logging with periodic review.

## DA-012 Public and Internal Data

Public data may be shared externally without restriction. Internal data may be shared internally by role and externally only with owner approval.

## DA-013 Confidential Data

Confidential data requires data owner and manager approval for access and stronger handling controls.

## DA-014 Restricted Data

Restricted data requires data owner and Information Security approval. Transfer outside Acme requires enhanced review.

## DA-015 Access Request Process

Access requests must include business justification, manager approval, data owner approval, duration, and system role.

## DA-016 Privileged Access

Privileged access must be time-bound, use MFA, be logged, and be reviewed quarterly.

## DA-017 Customer Data External Vendors

Sharing customer data with an external vendor for analysis requires business owner approval, Legal review, Information Security review, DPA, vendor security assessment, approved transfer method, and minimum necessary extract.

## DA-018 HR Data External Vendors

Sending employee HR data to an external analytics vendor requires HR data owner, Legal, and Information Security approval. HR data must not be uploaded to public AI tools.

## DA-019 Finance Data Access by Non-Finance Employees

Non-finance employees may access finance reports only with finance data owner approval and documented project need.

## DA-020 Approved Transfer Methods

Approved methods include secure file transfer, approved cloud folders with access controls, and encrypted email only where explicitly approved.

## DA-021 Vendor Production Access

Vendor access to production systems requires system owner and Information Security approval, least privilege, logging, and time limits.

## DA-022 Break-Glass Access

Break-glass access may be granted for emergencies by Information Security and the system owner with post-review within 1 business day.

## DA-023 AI Tools and Data Handling

Public or Internal data may be used only in approved AI tools. Confidential, Restricted, customer, HR, and finance data may not be uploaded to public AI tools.

## DA-024 Access Reviews

Privileged and Restricted access is reviewed quarterly. Confidential access is reviewed semiannually.

## DA-025 Termination and Role Change

Access must be removed or adjusted promptly when employment ends or role changes.

## DA-026 Incident Reporting

Employees must report suspected unauthorized access, wrong recipient, public links, vendor oversharing, or AI tool uploads immediately to Information Security.

## DA-027 Data Minimization for Vendors

Only the minimum necessary fields should be shared with vendors, with defined retention and deletion.

## DA-028 Contracts and DPAs

External sharing requires appropriate contract terms and data processing agreements where personal or customer data is involved.

## DA-029 Logging and Monitoring

Access to sensitive systems is logged and monitored for anomalous behavior.

## DA-030 Need-to-Know Examples

Examples of need-to-know include project team access to customer analytics, HR access to employee records, and finance access to budget reports.

## DA-031 Prohibited Transfer Scenarios

Do not send customer lists to personal email, upload HR spreadsheets to public AI, or share production credentials with vendors without approval.

## DA-032 Exceptions

Exceptions require Information Security and data owner approval with time limits.

## DA-033 Audit and Monitoring

Internal Audit and Information Security perform periodic access reviews and control testing.

## DA-034 Definitions

Data owner means the business or functional owner accountable for a dataset. External vendor means a third party outside Acme Corp.

## DA-035 Policy Summary

In summary: classify data, use least privilege, obtain required approvals before external sharing, use approved transfer methods, and report incidents immediately.

### Example: Customer data to external analytics vendor

Scenario: Team wants to share customer data with an analytics vendor.  
Policy outcome: Needs approval.  
Required approvals: Business owner, Legal, Information Security.  
Why: Customer data external sharing requires security and legal review.  
Relevant sections: DA-003, DA-017, AM-012.

### Example: HR data to external vendor

Scenario: Employee wants to send HR data to an analytics vendor.  
Policy outcome: Escalate / Needs approval.  
Required approvals: HR data owner, Legal, Information Security.  
Why: HR external sharing is high risk.  
Relevant sections: DA-004, DA-018, AM-012.

### Example: Finance report access by non-finance employee

Scenario: Project manager requests finance reports outside their team.  
Policy outcome: Needs approval.  
Required approvals: Finance data owner.  
Why: Need-to-know and finance owner approval required.  
Relevant sections: DA-005, DA-019.

### Example: Customer data already sent before approval

Scenario: Employee already sent customer data to a vendor without Security approval.  
Policy outcome: Escalate immediately.  
Required actions: Report to Information Security; contain and assess exposure.  
Relevant sections: DA-008, DA-026, DA-010.

### Example: Uploading spreadsheet to public AI tool

Scenario: Employee uploads Internal customer data to a public AI tool.  
Policy outcome: Escalate / Not allowed.  
Why: Customer data may not be uploaded to public AI tools.  
Relevant sections: DA-023, DA-009.

### Example: Vendor production access

Scenario: Vendor requests production database access.  
Policy outcome: Needs approval.  
Required approvals: System owner, Information Security.  
Relevant sections: DA-021, AM-012.

### Example: Break-glass access

Scenario: On-call engineer needs emergency privileged access.  
Policy outcome: Allowed with controls.  
Required approvals: Information Security + system owner; post-review within 1 business day.  
Relevant sections: DA-022, AM-012.

### Example: Internal dashboard access

Scenario: Employee requests access to an internal analytics dashboard.  
Policy outcome: Needs approval based on classification.  
Required approvals: Data owner and manager.  
Relevant sections: DA-015, DA-011.
