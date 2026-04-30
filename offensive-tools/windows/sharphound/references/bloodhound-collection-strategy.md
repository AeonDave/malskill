# SharpHound Collection Strategy & Integration

## Collection Options & When to Use

### 1. **DCOnly Collection (Fastest, Stealth)**

```powershell
# Collect only from Domain Controller (no queries to member computers)
Invoke-SharpHound -CollectionMethod DCOnly

# What it gets:
# - Domain structure (users, groups, computers, OUs)
# - Group memberships
# - ACLs on domain objects
# - Trust relationships
# - Default group policies
```

**When to use:**
- ✅ Stealthy (minimal lateral movement)
- ✅ Fast (single DC query)
- ✅ No alerting on member computers
- ❌ Misses local admin groups on machines
- ❌ Misses session information
- ❌ Misses RBCD/delegation details on computers

---

### 2. **All Collection (Most Data, Noisy)**

```powershell
# Full collection: everything
Invoke-SharpHound -CollectionMethod All

# What it gets:
# - Domain structure (users, groups, computers, OUs)
# - Group memberships (global + local)
# - ACLs (domain + local)
# - Sessions (who is logged in where)
# - Privileges (local admin groups)
# - Logon policies (password policy, lockout)
# - Trusts (domain trusts, forest trusts)
# - Delegation (constrained, unconstrained, RBCD)
# - GPOs and GPO application
```

**When to use:**
- ✅ Complete picture of domain + machines
- ✅ Session info (lateral movement paths)
- ✅ Local admin enumeration
- ❌ Very noisy (queries every machine)
- ❌ Slow (can take hours on large domains)
- ❌ High detection risk

---

### 3. **User Focused (Users + Computers)**

```powershell
# Only user-related data
Invoke-SharpHound -CollectionMethod "User,Computer"

# Skips: Sessions, LocalAdmin, LoggedIn
```

---

### 4. **Session Collection (Who's logged in where?)**

```powershell
# Only sessions = WHERE ARE DOMAIN ADMINS LOGGED IN?
Invoke-SharpHound -CollectionMethod Session

# Fastest way to find domain admin workstations for lateral movement
```

---

## Output Structure (JSON Files in ZIP)

SharpHound creates ZIP with multiple JSON files:

```
collection_timestamp_BloodHound.zip
├── computers.json          # Computer objects, local groups, sessions
├── domains.json            # Domain info, trusts
├── gpos.json              # Group Policy Objects
├── groups.json            # Domain groups + memberships
├── ous.json               # Organizational Units
├── users.json             # Domain users + group memberships
└── containers.json        # AD containers
```

### Size Estimation

| Collection Type | Domain Size | File Size | Time |
|---|---|---|---|
| **DCOnly** | 1000 users | 2-5 MB | < 1 min |
| **User+Computer** | 1000 users | 10-20 MB | 5-10 min |
| **All** | 1000 users | 50-100 MB | 20-60 min |
| **All** | 5000+ users | 200+ MB | 1-4 hours |

---

## Exfiltration Strategies

### Option 1: Direct Exfiltration (Fastest)

```powershell
# Generate and immediately exfil:
Invoke-SharpHound -CollectionMethod DCOnly -OutputDirectory C:\temp\

# Compress:
Compress-Archive -Path C:\temp\collection_*_BloodHound.zip -DestinationPath C:\temp\collection.zip

# Exfil via SMB/HTTP/DNS/etc:
# Use your favorite C2 exfil method
```

### Option 2: Staged Collection (Avoid Detection)

```powershell
# Collect gradually:
for ($i = 1; $i -le 10; $i++) {
    Invoke-SharpHound -CollectionMethod DCOnly -OutputDirectory C:\temp\
    Start-Sleep -Seconds 3600  # Wait 1 hour between collections
}

# Evade detection by spreading queries over time
```

### Option 3: Split Collection (Distribute Load)

```powershell
# Collect from multiple machines to appear as normal domain queries:
# Machine1: Collect users
# Machine2: Collect computers
# Machine3: Collect sessions

# Then combine JSON files for analysis
```

---

## BloodHound GUI Integration

### Import & Analyze

1. **Upload ZIP to BloodHound:**
   ```
   BloodHound GUI → Upload Data → Select ZIP
   ```

2. **View Domain Structure:**
   - Domain Stats (users, computers, groups)
   - Relationship graphs

3. **Run Queries (Built-in):**
   - "Shortest Path to Domain Admin"
   - "Shortest Path to High-Value Targets"
   - "Users with Admin Privileges"
   - "Sessions with Kerberoastable Users"
   - "Unconstrained Delegation"
   - "Resource-Based Constrained Delegation"

4. **Custom Queries (Cypher):**
   ```cypher
   # Find all paths to Domain Admins:
   MATCH p = (n) -[*1..] -> (g:Group {name:"DOMAIN ADMINS@DOMAIN.COM"})
   WHERE NOT n.isDeleted
   RETURN p

   # Find users with GenericAll:
   MATCH p = (u:User) -[r:GenericAll] -> (t)
   RETURN u, r, t
   ```

---

## PowerView + SharpHound Workflow

Combine for full coverage:

```powershell
# 1. SharpHound collects raw data
Invoke-SharpHound -CollectionMethod DCOnly

# 2. PowerView queries live domain
# (Helpful for missing data or alternative paths)
Get-DomainUser -AdminCount  # Users with admin privileges
Get-DomainUser -TrustedToAuth  # Constrained delegation users
Get-DomainComputer -Unconstrained  # Unconstrained delegation

# 3. Import SharpHound ZIP into BloodHound GUI
# 4. Manually cross-check with PowerView output
```

---

## Post-Collection Analysis

### Key Questions SharpHound Answers

1. **Who can become Domain Admin?**
   - Run: "Shortest Path to Domain Admin"

2. **Who has local admin on sensitive machines?**
   - Query: `MATCH (u:User) -[r:AdminTo] -> (c:Computer)` in BloodHound

3. **Which users are Kerberoastable?**
   - Query: Find users with SPNs

4. **Are there unconstrained delegation paths?**
   - Query: `MATCH p = (c:Computer {unconstrainedDelegation: true})`

5. **Can we escalate via group membership?**
   - Show group membership chains

---

## OPSEC Considerations

⚠️ **SharpHound is LOUD:**
- Every DC query logged (Event ID 4624 / 4625)
- Computer enumeration creates SMB connections (likely detected)
- Session collection = WMI calls to every machine

✅ **Stealth options:**
- **DCOnly** is quietest (just DC queries)
- Avoid "Session" collection unless necessary
- Run during maintenance windows
- Use low-privilege account (less suspicious)
- Stagger collection over days/weeks

❌ **Don't use if:**
- EDR is actively hunting
- BlueTeam is live-hunting for recon

---

## Real-World Integration Flow

```
Step 1: Gain initial access to domain-joined machine
        ↓
Step 2: Verify domain context (whoami /all)
        ↓
Step 3: Run SharpHound DCOnly (minimal noise)
        ↓
Step 4: Download ZIP from machine
        ↓
Step 5: Import to BloodHound on attacker machine
        ↓
Step 6: Run "Shortest Path to Domain Admin" query
        ↓
Step 7: Identify attack chain (e.g., User → Group → Privesc → Admin)
        ↓
Step 8: Execute chain with PowerView / other tools
        ↓
Step 9: Domain compromise achieved
```

---

## References

- **SharpHound GitHub**: https://github.com/BloodHoundAD/SharpHound3
- **BloodHound Community**: https://github.com/BloodHoundAD/BloodHound
- **BloodHound Queries**: https://github.com/BloodHoundAD/BloodHound/wiki/The-BloodHound-Power-User-Interface
- **Cypher Query Language**: https://neo4j.com/docs/cypher-manual/current/
- **PowerView + BloodHound Integration**: https://bloodhound.readthedocs.io/
