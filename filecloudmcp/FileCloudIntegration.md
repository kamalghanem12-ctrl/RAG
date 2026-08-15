# FileCloud and Enterprise RAG Integration Model

## 1. Capability and Access Matrix

| Capability / Access Path | Primary Purpose | AI Integration | Typical Use | Query-Time | Ingestion / Sync |
|---|---|---|---|---|---|
| **FileCloud Desktop** | User access to FileCloud content from the workstation through Desktop / Drive / Sync | **FileCloud MCP** can expose content that the authenticated user is able to access through the desktop integration | Personal working files, locally synchronized content, direct file operations | ✅ | ❌ |
| **FileCloud Web** | Browser-based access to the user's authorized FileCloud repository | **FileCloud MCP** can use FileCloud APIs to search/retrieve content available to the authenticated user | Department repositories, remote access, files not locally synchronized | ✅ | ❌ |
| **FileCloud as RAG Source** | Authoritative enterprise document repository | RAG ingestion reads document content and relevant permission metadata from FileCloud and builds/updates the knowledge index | Initial ingestion and continuous synchronization | ❌ | ✅ |
| **FileCloud MCP** | Live repository interaction | Provides Claude with controlled access to FileCloud operations | Exact file access, browse, current-version retrieval, repository search | ✅ | ❌ |
| **PostgreSQL + pgvector RAG Index** | Search-optimized, permission-aware knowledge layer | **RAG MCP** retrieves authorized chunks | Semantic enterprise questions and cross-document reasoning | ✅ | ✅ Populated/updated from FileCloud |
| **RAG MCP** | Permission-aware semantic retrieval and RAG orchestration | Connects Claude to the RAG service/index | Policy questions, semantic search, cross-document questions | ✅ | ❌ |

> **Validation note:** FileCloud's Web Portal supports file/folder access and search, including filename, content, and metadata search when configured. FileCloud Sync/Desktop capabilities also support search and access to content available through the client. Exact capabilities depend on the deployed FileCloud version, configuration, user type, and permissions. citeturn386984search2turn386984search3turn386984search11

---

## 2. Live FileCloud Access

### Flow

```text
User
  ↓
Claude
  ↓
FileCloud MCP
  ↓
FileCloud Desktop / Web / API
  ↓
User-authorized FileCloud Content
```

### Purpose

Use this path when the user needs to work with the **live repository itself**, rather than asking a semantic question over the indexed knowledge base.

Typical use cases:

- Find an exact filename.
- Retrieve a specific document.
- Retrieve the latest/current version available to the user.
- Browse folders.
- Open or download a document.
- Search current FileCloud content.
- Access a document that has not yet been indexed by the RAG pipeline.

FileCloud supports browser-based repository access and search; content search availability depends on the FileCloud configuration. citeturn386984search2turn386984search11

---

## 3. FileCloud as the RAG Ingestion Source

For the Enterprise RAG platform, FileCloud remains the **authoritative document repository**.

```text
FileCloud
    ↓
Ingestion / Synchronization
    ↓
Content Extraction
    ↓
Metadata Extraction
    ↓
ACL / Permission Extraction
    ↓
Chunking
    ↓
Embedding
    ↓
PostgreSQL + pgvector
```

The RAG index is a **derived, search-optimized representation** of the FileCloud knowledge.

### Important

FileCloud must not be treated as a one-time import source.

The ingestion/synchronization lifecycle must continue to detect and process:

- New documents
- Modified documents
- Deleted documents
- ACL / permission changes
- Document moves
- Version changes
- Classification/security changes

This ensures that the RAG index remains aligned with the authoritative repository.

---

## 4. Runtime Enterprise RAG Access

Once documents are indexed:

```text
User
  ↓
Claude
  ↓
RAG MCP
  ↓
Identity / Authorization Context
  ↓
Permission-Aware PostgreSQL + pgvector Retrieval
  ↓
Authorized Chunks
  ↓
Reranker
  ↓
Context Builder
  ↓
Claude
  ↓
Answer
```

The RAG runtime is optimized for:

- Semantic search
- Metadata filtering
- Permission-aware retrieval
- Hybrid search
- Reranking
- Cross-document reasoning
- Source/citation handling

A normal semantic RAG query does **not** need to call FileCloud for every request.

---

## 5. FileCloud MCP vs RAG MCP

These are separate capabilities with different purposes.

### FileCloud MCP

**Question it answers:**

> "Can you find, open, retrieve, or interact with the actual FileCloud document?"

Examples:

- "Find `Investment_Policy_2026.pdf`."
- "Open the latest version."
- "Show me the files in this folder."
- "Download the source document."

### RAG MCP

**Question it answers:**

> "What does the enterprise knowledge say about this topic?"

Examples:

- "What is our privileged access policy?"
- "Summarize the HR onboarding process."
- "Compare the requirements across these policies."

---

## 6. Combined Pattern

The two capabilities can work together.

Example:

> "Explain the 2026 Investment Policy and provide the original source document."

Flow:

```text
User
  ↓
Claude
  ├───────────────→ RAG MCP
  │                    ↓
  │              Semantic Retrieval
  │                    ↓
  │              Authorized Chunks
  │
  └───────────────→ FileCloud MCP
                       ↓
                 Original Source
                       ↓
                    Claude
                       ↓
                    Answer
```

In this model:

- **RAG MCP** identifies and explains relevant knowledge.
- **FileCloud MCP** provides the authoritative repository artifact.

---

## 7. Simplified Architectural Principle

> **FileCloud Desktop / Web + FileCloud MCP = Live document and repository access.**

> **FileCloud as the RAG source = Authoritative content and permission source used to build and continuously synchronize the Enterprise RAG index.**

> **PostgreSQL + pgvector = Search-optimized, permission-aware knowledge index used at runtime.**

> **RAG MCP = Runtime semantic knowledge retrieval and RAG orchestration.**

---

## 8. Final Conceptual Model

```text
                              FileCloud
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
             FileCloud MCP              RAG Ingestion
                    │                         │
                    ▼                         ▼
             Live Repository          PostgreSQL + pgvector
             Access / Files                    │
                                                ▼
                                            RAG MCP
                                                │
                         ┌──────────────────────┘
                         ▼
                       Claude
```

## 9. Key Design Rule

> **FileCloud remains the authoritative source for document content and document permissions. FileCloud MCP provides controlled live repository access, while PostgreSQL + pgvector provides the search-optimized permission-aware knowledge layer used by the RAG runtime.**

The RAG index is therefore a **derived representation**, not a replacement for FileCloud.

---

## 10. Validation and Scope Note

The exact FileCloud MCP behavior is dependent on the MCP implementation used by the organization. FileCloud's documented platform capabilities include browser-based access, desktop client capabilities, search, sharing/permissions, and programmatic APIs; the organization-specific MCP layer must preserve those authorization boundaries rather than bypass them. citeturn386984search2turn386984search10turn386984search1
