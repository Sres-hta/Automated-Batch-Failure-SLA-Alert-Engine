from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

for section in doc.sections:
    section.top_margin = Inches(0.45)
    section.bottom_margin = Inches(0.45)
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)

style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(10)

def add_header(name, title, contact):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(3)
    
    r_name = p.add_run(name + "\n")
    r_name.bold = True
    r_name.font.size = Pt(15.5)
    
    r_title = p.add_run(title + "\n")
    r_title.bold = True
    r_title.font.size = Pt(10.5)
    r_title.font.color.rgb = RGBColor(50, 50, 50)
    
    r_contact = p.add_run(contact)
    r_contact.font.size = Pt(9.5)

def add_section_heading(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(11)

def add_bullet(lead_in, text):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(1.5)
    if lead_in:
        r_lead = p.add_run(lead_in + ": ")
        r_lead.bold = True
    p.add_run(text)

add_header(
    "SRESHTA SARKAR",
    "IT OPERATIONS ANALYST | INFRASTRUCTURE & BATCH MONITORING SPECIALIST",
    "Bengaluru, Karnataka | +91 7596838818 | sreshtasarkar16@gmail.com | LinkedIn: [Insert URL] | GitHub: [Insert URL]"
)

add_section_heading("Professional Summary")
p_sum = doc.add_paragraph(
    "Detail-oriented IT Operations Analyst with 2 years of experience monitoring and supporting enterprise IT infrastructure, "
    "mission-critical applications, and batch processing workflows in high-availability environments. Proven expertise in L1 computer "
    "operations support, batch scheduling (Control-M, JP1), Unix/Windows system administration, and AS400/Mainframe operations. "
    "Adept at assessing and escalating real-time alerts, executing system housekeeping and start/shutdown procedures, and managing "
    "end-to-end incident lifecycles via ServiceNow within strict SLAs. Strong communicator capable of liaising with L2/L3 technical SMEs, "
    "third-party vendors, and business users under high pressure across 24x365 rotational shifts."
)
p_sum.paragraph_format.space_after = Pt(3)

add_section_heading("Core Technical Skills")
add_bullet("Batch & Operations Monitoring", "Control-M, JP1, Batch Failure Triage & Reruns, DAG Job Scheduling, System Housekeeping, Server Start/Shutdown Procedures, Daily Check-Sheet Reporting")
add_bullet("OS & Mainframe Platforms", "Unix / Linux (L1 Support, Shell Scripting, Telemetry & Log Analysis), Windows Server Administration, AS400 / IBM iSeries & Mainframe Operations, VDI Environments")
add_bullet("ITSM & Governance", "ServiceNow (Incident, Problem, Change & Request Management, REST API Payloads), ITIL v4 Practices, SLA Compliance, Alert & Event Escalation, SOP / Runbook Documentation")
add_bullet("Cloud, Access & Reporting", "Microsoft Azure, Active Directory (AD), MFA/SSO, SQL (SQLite, MySQL, SQL Developer), Python (Automation), Advanced Excel, Power BI")

add_section_heading("Work Experience")
p_job = doc.add_paragraph()
p_job.paragraph_format.space_after = Pt(1.5)
r_role = p_job.add_run("IT Operations & Service Desk Analyst | LTIMindtree Limited")
r_role.bold = True
p_job.add_run(" — Bengaluru, Karnataka | [Oct 2024] – Present")

p_sub1 = doc.add_paragraph()
p_sub1.paragraph_format.space_before = Pt(3)
p_sub1.paragraph_format.space_after = Pt(1.5)
p_sub1.add_run("Batch Monitoring & Infrastructure Operations").bold = True

add_bullet("Batch Job Management", "Monitor, identify, and troubleshoot scheduled batch jobs using Control-M and JP1; immediately assess batch failures, perform root-cause checks, execute approved job reruns, or escalate to application SMEs within strict SLA windows.")
add_bullet("Platform & OS Support", "Provide first-line (L1) operational support across Unix, Windows, and AS400/Mainframe environments, monitoring system performance, disk utilization, and service availability across 24x365 rotational shifts.")
add_bullet("System Housekeeping & Maintenance", "Execute scheduled system housekeeping, server startups, shutdowns, and health verifications in strict accordance with standard operating procedures (SOPs) and change windows.")
add_bullet("Daily Check-Sheets & Shift Handovers", "Complete comprehensive daily operational check-sheets, shift handover logs, and real-time status reports, ensuring zero gaps in workload continuity across rotational shifts.")

p_sub2 = doc.add_paragraph()
p_sub2.paragraph_format.space_before = Pt(3)
p_sub2.paragraph_format.space_after = Pt(1.5)
p_sub2.add_run("Incident Management, Escalation & SLA Governance").bold = True

add_bullet("End-to-End Incident Lifecycle", "Assess real-time infrastructure alerts and events, logging and managing 40+ daily incidents and service requests via ServiceNow while consistently achieving 99% SLA compliance.")
add_bullet("Stakeholder & Vendor Liaison", "Act as the primary bridge during high-priority (P1/P2) outages—coordinating between internal L2/L3 technical experts, third-party vendors, and end-users to drive rapid incident resolution and timely status updates.")
add_bullet("Operational Reporting & Analytics", "Extract and analyze operational ticket volumes, batch failure trends, and SLA breach risks using SQL and Advanced Excel, delivering actionable weekly dashboards to operations leadership.")
add_bullet("SME Guidance & Process Standardization", "Author 20+ Knowledge Base articles and runbooks for recurring batch/system alerts, and provide SME guidance and ITIL process training (Incident, Change, Problem Management) to junior shift analysts.")
add_bullet("Identity & Cloud Support", "Manage secure user provisioning/deprovisioning via Active Directory, MFA, and SSO, and support day-to-day operational tasks across Microsoft Azure and VDI infrastructure.")

add_section_heading("Key Operations Automation Project")
p_proj = doc.add_paragraph()
p_proj.paragraph_format.space_after = Pt(1.5)
r_proj = p_proj.add_run("FinOps-BatchGuard: Automated Batch Failure, ServiceNow Escalation & SLA Alert Engine")
r_proj.bold = True
p_proj.add_run(" | Python, Unix Bash, SQLite, ServiceNow REST API, HTML/CSV")

add_bullet("DAG Batch Orchestration & Auto-Retry", "Engineered a Control-M/JP1-modeled financial batch scheduler (SWIFT ingestion, GL reconciliation, EOD settlement) with topological dependency resolution, automated retry backoff for transient locks, and upstream failure blocking.")
add_bullet("ITIL ServiceNow Auto-Ticketing & Deduplication", "Built an automated incident triage engine that generates ServiceNow Table API payloads (P1/P2/P3), maps failures to L2/L3 SME escalation matrices and KB runbooks, and links downstream blocked jobs as child incidents to prevent alert storms.")
add_bullet("Unix Housekeeping & Daily Shift Check-Sheet", "Developed a Bash/Python telemetry utility to audit disk/memory/CPU usage, purge stale spool files, verify core banking daemons (controlm-agent, as400-tn5250-bridge), and auto-export CSV Daily Check-Sheets and HTML Shift Handover Dashboards.")

add_section_heading("Education & Certifications")
p_edu = doc.add_paragraph()
p_edu.paragraph_format.space_after = Pt(1.5)
p_edu.add_run("Bachelor of Computer Applications (BCA)").bold = True
p_edu.add_run(" | Institute of Engineering and Management, Salt Lake, West Bengal (2022 – 2025)")

add_bullet("Certifications & Training", "ITIL Foundation (Incident, Problem & Change Management) | Microsoft Azure Fundamentals (AZ-900) | Enterprise Operations & Access Management (Active Directory, MFA/SSO, ServiceNow, SQL, Power BI)")
add_bullet("Operational Readiness", "Fully flexible for 24x365 rotational shifts & onsite deployment at MUFG BCIT Bengaluru | Availability: Immediate / [30 Days] | Languages: English, Hindi, Bengali")

doc.save("Sreshta_Sarkar_MUFG_Resume.docx")
print("✅ Saved Final Resume: Sreshta_Sarkar_MUFG_Resume.docx")
