# Information Security Policy

**Document ID:** POL-004  
**Version:** 4.0  
**Last Updated:** January 2025  
**Owner:** Information Security Department

## 1. Purpose

This policy establishes the requirements for protecting company information assets, systems, and data from unauthorized access, disclosure, modification, or destruction.

## 2. Scope

This policy applies to all employees, contractors, vendors, and third parties with access to company information systems, networks, or data.

## 3. Information Classification

### 3.1 Classification Levels

**Public:** Information approved for public disclosure
- Marketing materials
- Press releases
- Public website content

**Internal:** Information for internal use only
- Company announcements
- General policies and procedures
- Internal directories

**Confidential:** Sensitive business information
- Financial data
- Customer lists
- Employee records
- Business strategies and plans
- Source code

**Restricted:** Highly sensitive information requiring strict protection
- Social Security numbers
- Payment card information (PCI data)
- Health information (PHI)
- Trade secrets
- M&A information
- Security credentials

### 3.2 Handling Requirements

- **Public:** No special handling required
- **Internal:** Share only with employees; do not forward to personal email
- **Confidential:** Share only with authorized personnel; encrypt when emailing
- **Restricted:** Access logged and monitored; encryption required; print only when necessary

## 4. Access Control

### 4.1 User Accounts

- Every user must have a unique account (no shared accounts)
- User accounts created only after manager approval via IT ticket
- Access provisioned based on role and principle of least privilege
- Accounts disabled immediately upon termination
- Temporary accounts for contractors expire after 90 days

### 4.2 Password Requirements

**Minimum Standards:**
- At least 12 characters long
- Include uppercase, lowercase, numbers, and special characters
- Cannot contain username or common dictionary words
- Cannot reuse last 10 passwords
- Must be changed every 90 days
- Different passwords for different systems

**Multi-Factor Authentication (MFA):**
- Required for all accounts accessing company systems
- Approved MFA methods: authenticator apps (Duo, Microsoft Authenticator), hardware tokens
- SMS-based MFA discouraged but acceptable for low-risk systems
- Backup codes stored securely

### 4.3 Access Reviews

- Managers review team access quarterly
- Privileged access (admin rights) reviewed monthly
- Unused accounts disabled after 60 days of inactivity
- Access violations reported to Security immediately

## 5. Device Security

### 5.1 Company Devices

**Required Security Controls:**
- Full disk encryption enabled
- Automatic screen lock after 5 minutes
- Antivirus/EDR software installed and updated
- Operating system patches applied within 14 days
- Company MDM (Mobile Device Management) enrolled

**Prohibited Activities:**
- Installing unauthorized software
- Disabling security tools
- Sharing devices with others
- Storing company data on external drives without encryption

### 5.2 Personal Devices (BYOD)

If approved for company use:
- Must install company MDM profile
- Separate work and personal data containers
- Company retains right to remotely wipe work data
- Must meet minimum security standards (OS version, encryption, passcode)
- Not permitted for Restricted data access

### 5.3 Mobile Devices

- Screen lock required (6-digit PIN minimum, biometric preferred)
- Report lost/stolen devices within 4 hours
- Remote wipe will be initiated for lost devices
- No rooted/jailbroken devices permitted

## 6. Network Security

### 6.1 Wireless Networks

- Use company Wi-Fi with credentials
- Public Wi-Fi only with VPN enabled
- Do not connect to suspicious or unsecured networks
- Home Wi-Fi must use WPA2 or WPA3 encryption

### 6.2 VPN Usage

- Required when accessing internal systems remotely
- Required on all public Wi-Fi connections
- Auto-disconnect after 12 hours of inactivity
- Split tunneling disabled for security

### 6.3 Firewall and Network Monitoring

- All network traffic monitored for threats
- Firewall blocks unauthorized inbound connections
- Intrusion detection alerts investigated within 4 hours

## 7. Email and Communication Security

### 7.1 Email Usage

**Prohibited:**
- Sending Confidential or Restricted data without encryption
- Opening attachments from unknown senders
- Clicking links in suspicious emails
- Using company email for personal business
- Auto-forwarding to external email addresses

**Required:**
- Use email encryption for sensitive data (Outlook encryption button)
- Verify sender before opening attachments
- Report phishing attempts to security@company.com
- Use "Reply All" carefully to avoid data leaks

### 7.2 Phishing Prevention

- Annual security awareness training required
- Simulated phishing tests conducted quarterly
- Hover over links before clicking
- Verify requests for sensitive info via phone
- Report suspicious emails immediately

### 7.3 Sensitive Data Transmission

- Use encrypted file sharing (SharePoint, OneDrive with encryption)
- For external sharing: use secure file transfer (Sharefile, Accellion)
- Never email SSNs, credit card numbers, or passwords
- Password-protect sensitive documents

## 8. Data Protection

### 8.1 Data Storage

**Approved Storage Locations:**
- Company file servers
- SharePoint/OneDrive for Business
- Approved cloud services (AWS, Azure with company account)

**Prohibited Storage:**
- Personal email accounts
- Personal cloud storage (Dropbox, Google Drive personal)
- USB drives without encryption
- Personal computers

### 8.2 Data Backup

- Company data backed up automatically daily
- Backups encrypted and stored off-site
- Test restores performed quarterly
- Employee responsibility to store files in approved locations

### 8.3 Data Retention and Disposal

- Follow records retention schedule (see Records Management Policy)
- Delete data when no longer needed
- Use secure deletion tools (don't just delete files)
- Physical documents: shred with cross-cut shredder
- Devices: wiped by IT before disposal/reuse

## 9. Incident Response

### 9.1 Security Incidents

Report immediately to security@company.com or ext. 5911:
- Suspected malware infection
- Lost or stolen devices
- Unauthorized access attempts
- Data breaches or leaks
- Phishing emails with opened attachments
- Suspicious system behavior

### 9.2 Response Process

1. Report incident immediately
2. Do not turn off device (may destroy evidence)
3. Disconnect from network if malware suspected
4. Security team investigates within 1 hour
5. Communications team handles external notifications if needed

### 9.3 Incident Severity

- **Critical:** Active breach, ransomware, stolen Restricted data
- **High:** Compromised credentials, malware infection
- **Medium:** Phishing attempt, suspicious login
- **Low:** Policy violation, lost non-sensitive device

## 10. Third-Party Security

### 10.1 Vendor Requirements

- Security assessment required before engagement
- Sign Business Associate Agreement or Data Processing Agreement
- Annual security questionnaire
- Compliance with company security standards
- Access reviewed quarterly

### 10.2 Vendor Access

- Minimum necessary access only
- Separate vendor accounts (no shared credentials)
- MFA required
- Access automatically expires after contract end
- Activity monitored and logged

## 11. Physical Security

### 11.1 Office Security

- Wear badge at all times in office
- Do not tailgate or allow tailgating
- Secure laptops when away from desk (lock or take with you)
- Clean desk policy: no Confidential documents left unattended
- Visitor badges required; escort visitors in secure areas

### 11.2 Remote Work Security

- Lock doors/windows when handling Restricted data
- Shred confidential documents at home
- No screen sharing with unauthorized viewers
- Professional background for video calls (no sensitive info visible)

## 12. Compliance and Monitoring

### 12.1 Acceptable Use

- Company systems for business purposes primarily
- Limited personal use acceptable (lunch breaks, brief personal email)
- No illegal activity, harassment, or offensive content
- No copyright infringement (unauthorized software, media)

### 12.2 Monitoring and Auditing

- Company reserves right to monitor all system activity
- No expectation of privacy on company systems
- Security logs retained for 1 year
- Random audits conducted quarterly
- Privileged user activity audited monthly

### 12.3 Training Requirements

- Security awareness training: annually for all employees
- Role-specific training: for developers, finance, HR
- New hire security orientation: within first week
- Phishing simulations: quarterly

## 13. Violations and Enforcement

### 13.1 Policy Violations

Minor violations (first offense):
- Security awareness counseling
- Documented in employee file

Moderate violations:
- Written warning
- Mandatory retraining
- Loss of privileges

Severe violations:
- Suspension
- Termination
- Legal action for criminal activity

### 13.2 Examples of Violations

- Sharing passwords
- Disabling security controls
- Unauthorized data access
- Failure to report incidents
- Storing company data on personal accounts

## 14. Exceptions

- Exception requests submitted to security@company.com
- Business justification required
- CISO approval needed
- Exceptions documented and reviewed quarterly
- Compensating controls may be required

## 15. Related Policies

- Acceptable Use Policy (POL-008)
- Data Privacy Policy (POL-009)
- Records Retention Policy (POL-010)
- Remote Work Policy (POL-002)

## 16. Contact Information

**Security Team:**
- Email: security@company.com
- Phone: Extension 5911 (24/7 for emergencies)
- Security Portal: https://security.company.com

**For Questions:**
- Policy interpretation: security-policy@company.com
- Security training: training@company.com
- Incident reporting: security-incident@company.com

