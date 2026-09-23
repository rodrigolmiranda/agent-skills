# Agent message templates

Use the applicable block. Replace placeholders; records hold details. Every message is correlated and has one next owner/action. These are communication forms, not executable commands or additional authority.

## Dispatch — Planner → worker

```text
DISPATCH project=<id> job=<id> revision=<n> attempt=<id>
From=<planner ID/generation> To=<worker ID>
Read <assignment path/revision>, then its required sources.
Record understanding, baseline and proof plan in <handover>.
Questions go in <questions file> before dependent work; notify with IDs and link.
Startup=<proceed when clear | explicit named gate>. Ownership/holds are in the packet.
Return <deliverable> through <verified route>. Next owner: you.
```

## Startup — worker → Planner

```text
RECEIPT project=<id> job=<id> revision=<n> attempt=<id>
From=<worker ID> To=<planner ID/generation>
Understanding and baseline recorded: <handover/revision>.
Questions=<none | IDs in file>. State=<proceeding | held on named gate>.
Next=<authorized action | precise decision needed from Planner>.
```

## Question — worker → Planner

```text
QUESTION project=<id> job=<id> revision=<n> attempt=<id>
From=<worker ID> To=<planner ID/generation>
<IDs> written at <question file/revision>; event artifact=<immutable snapshot>.
Decision=<short sentence>; recommendation=<option/reason>.
Blocked=<dependent work>; continuing=<independent work or none>.
Next owner=<Planner/owner>; process/resources=<retained or released>.
```

## Answer / resume — Planner → worker

```text
RESUME project=<id> job=<id> revision=<n> attempt=<new invocation ID>
From=<planner ID/generation> To=<worker ID>; previous attempt=<id>
Answers recorded: <Q IDs and file/revision>. Packet=<updated revision>.
Authorized next action=<exact action>; remaining holds=<IDs or none>.
Read and record incorporation before dependent work. Ask in the same file if still unclear.
Return via <route>. Next owner: you.
```

## Return — worker → Planner

```text
RETURN project=<id> job=<id> revision=<n> attempt=<id>
From=<worker ID> To=<planner ID/generation>
Result=<worker-complete | partial | blocked>; artifact=<PR/head or file/hash>.
Handover=<path/revision>; changed acceptance IDs=<IDs>; open gaps=<IDs or none>.
Questions=<file + open IDs or none>; resources=<state>.
Next owner=Planner for <review | named decision>. No independent acceptance claimed.
```

## Correction — Planner → worker

```text
CORRECT project=<id> job=<id> revision=<n> attempt=<id>
From=<planner ID/generation> To=<worker ID>
Review=<path/revision and reviewed head>; findings=<IDs>.
Correct only <scope>; preserve <accepted areas/holds>.
Return finding-to-evidence mapping at the new head via <route>.
Unclear requirement: write the question in <file> before dependent work.
```
