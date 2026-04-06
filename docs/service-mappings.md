# Service Comparison: opencode Built-in Tools vs CRANE MCP Tools

**Document Purpose**: Enable seamless integration of opencode tool execution framework with CRANE's 90+ research tools by comparing capabilities, parameter mappings, and integration strategies.

**Status**: Documentation for thesis Phase 3 (Integration Design)
**Last Updated**: 2024-04-04

---

## 1. System Overview

### 1.1 opencode Architecture
- **14 built-in tools**: Hardcoded file system, shell, and agent interaction primitives
- **MCP-ready design**: `Tool.McpTool` bool field enables future MCP exposure
- **Session-based execution**: Tool calls tracked per session with message context
- **Permission system**: Pub/sub pattern for tool approval (auto-approval bypass)
- **Provider-agnostic**: Router supports Copilot, Anthropic, OpenAI, Gemini, Groq, OpenRouter, AWS, Azure, VertexAI

### 1.2 CRANE Architecture
- **90+ MCP tools**: All tools exposed as MCP server via `mcp_tool_orchestration.py`
- **12 research categories**: Papers, Tasks, Citations, Evaluation, Pipeline, Agents, etc.
- **YAML-based storage**: References stored as `references/papers/{key}.yaml`
- **GitHub issue integration**: Research tasks managed via GitHub Issues
- **Evidence-first design**: All claims backed by citations to reference library

### 1.3 Key Integration Insight
> **opencode is the execution engine; CRANE is the domain layer.**
> - opencode provides universal file/shell/agent primitives
> - CRANE provides research-domain operations (paper search, citation analysis, evaluation)
> - Integration strategy: Use opencode's tool execution infrastructure to run CRANE's MCP tools

---

## 2. Side-by-Side Comparison Matrix

| Category | opencode Built-in Tool | CRANE MCP Tool(s) | Purpose Match | Capability Gap |
|----------|----------------------|-------------------|---------------|----------------|
| **File Reading** | `view.go` | `read_paper.py`, `get_reference.py` | Partial - CRANE specialized for PDFs/YAML | opencode reads any file; CRANE reads research artifacts |
| **File Writing** | `write.go` | `add_reference.py`, `annotate_reference.py` | Partial - CRANE domain-specific | opencode writes any file; CRANE writes research artifacts |
| **Search (text)** | `grep.go` | `search_references.py`, `list_references.py` | Different domains | opencode: text in files; CRANE: semantic keyword search |
| **Search (vector)** | None | `semantic_search.py`, `semantic_search_by_paper.py` | **CRANE exclusive** | opencode lacks vector search capability |
| **File Discovery** | `glob.go` | None | **opencode exclusive** | CRANE doesn't need glob - uses structured paths |
| **Shell Execution** | `bash.go` | None | **opencode exclusive** | CRANE uses Python subprocess internally, not exposed |
| **Agent Delegation** | `agent-tool.go` | `list_agents.py`, `add_agent_memory.py` | Partial - different models | opencode: multi-AI agent spawning; CRANE: single-agent memory |
| **Code Navigation** | `lsp_goto_definition.py` | None | **opencode exclusive** | CRANE doesn't need LSP - research workflow only |
| **Code Search** | `sourcegraph-tool.py` | None | **opencode exclusive** | Research workflow doesn't need cross-repo search |
| **Diagnostics** | `diagnostics.go` | `verify_reference.py` | Different domains | opencode: type errors; CRANE: metadata validation |
| **Diff/Edits** | `diff.go` | None | **opencode exclusive** | CRANE uses direct write; no diff needed |
| **HTTP Fetch** | `fetch.go` | `search_papers.py` (indirect) | Different domains | opencode: raw HTTP; CRANE: academic API wrappers |
| **Permission** | `permission.go` (internal) | `add_permission_rule.py`, `evaluate_permission_action.py` | **CRANE exclusive** | opencode permission is system-level; CRANE is research-governance |
| **MCP Server** | `Tool.McpTool` field | All 90 tools | **CRANE implements it** | opencode designed for MCP but has no MCP tools yet |

---

## 3. Detailed Parameter Mappings

### 3.1 File Reading Operations

#### opencode `view.go`
```go
type ViewToolCall struct {
    Path   string `json:"path"`   // Absolute file path
    Format string `json:"format,omitempty"` // raw/markdown/html (default: raw)
    Lines  string `json:"lines,omitempty"` // Line range "1:50" or "1:" for head 50
}
```
**Returns**: File content with line prefixes (`1: foo\n`), truncation at 2000 lines

#### CRANE `read_paper.py`
```python
def read_papers(paper_id: str,
                save_dir: Optional[str] = None,
                project_dir: Optional[str] = None):
    """Download and extract text from PDF in references/pdfs/"""
```
**Returns**: Plain text content from PDF

**Mapping Notes**:
- opencode `view` is **general file reader**; CRANE `read_paper` is **PDF extractor**
- opencode uses `Path` param; CRANE uses `paper_id` (bibTeX key)
- CRANE auto-downloads PDF if not present; opencode requires file to exist
- **Integration**: opencode can read CRANE's YAML outputs (`references/papers/{key}.yaml`)

---

### 3.2 File Writing Operations

#### opencode `write.go`
```go
type WriteToolCall struct {
    FilePath string `json:"filePath"`   // Absolute path
    Content  string `json:"content"`    // Full file content
}
```
**Constraints**:
- Must read file first (prevents accidental overwrites)
- Overwrites existing files
- Truncates lines >2000 chars

#### CRANE `add_reference.py`
```python
def add_reference(key: str,
                  title: str,
                  authors: List[str],
                  year: int,
                  doi: Optional[str] = None,
                  venue: Optional[str] = None,
                  url: Optional[str] = None,
                  abstract: Optional[str] = None,
                  categories: Optional[List[str]] = None,
                  keywords: Optional[List[str]] = None):
    """Write YAML to references/papers/{key}.yaml + append to bibliography.bib"""
```
**Returns**: `{key, path, status}`

**Mapping Notes**:
- opencode `write` is **low-level file creation**; CRANE `add_reference` is **structured artifact creation**
- CRANE writes **two files** simultaneously (YAML + BibTeX); opencode writes one file
- CRANE validates required fields (`key`, `title`, `authors`, `year`); opencode has no validation
- **Integration**: opencode can write CRANE YAML files directly if CRANE tool unavailable

---

### 3.3 Search Operations

#### opencode `grep.go`
```go
type GrepToolCall struct {
    Pattern    string `json:"pattern"`      // Regex pattern
    Include    string `json:"include,omitempty"` // File glob "src/**/*.ts"
    Path       string `json:"path,omitempty"` // Directory to search
    OutputMode string `json:"output_mode,omitempty"` // content/files_with_matches/count
    HeadLimit  int    `json:"head_limit,omitempty"` // Limit results
}
```
**Returns**: Matching lines with file paths (regex search on file content)

#### CRANE `semantic_search.py`
```python
def semantic_search(query: str,
                    k: int = 5,
                    refs_dir: Optional[str] = None,
                    project_dir: Optional[str] = None):
    """Vector search across reference library embeddings"""
```
**Returns**: `{"query": "...", "matches": [{"key": "...", "similarity": 0.85, ...}]}`

**Mapping Notes**:
- opencode `grep` = **text-based regex search** on any files
- CRANE `semantic_search` = **vector-based** on pre-built embeddings
- Different use cases: grepping code vs searching academic literature
- **Integration**: opencode `glob` + `grep` can search CRANE's YAML files for text patterns

---

### 3.4 Agent Operations

#### opencode `agent-tool.go`
```go
type AgentToolCall struct {
    Name             string  `json:"name"`           // Agent name
    Description      string  `json:"description"`    // 3-5 words
    Prompt           string  `json:"prompt"`         // Full task description
    RunInBackground  bool    `json:"run_in_background"`
    LoadSkills       []string `json:"load_skills"`   // Skill names to inject
    Category         string  `json:"category,omitempty"` // Deep/quick/etc.
    SubAgentType     string  `json:"subagent_type,omitempty"` // explore/oracle/expert
}
```
**Returns**: `task_id` or immediate result

#### CRANE `add_agent_memory.py`
```python
def add_agent_memory(agent_name: str,
                     content: str,
                     source: Optional[str] = None,
                     project_dir: Optional[str] = None):
    """Append memory entry to .crane/agents/{agent_name}.jsonl"""
```
**Returns**: `{"agent", "content", "source", "timestamp"}`

**Mapping Notes**:
- opencode `agent` = **spawn LLM agent** to execute task (orchestration)
- CRANE `add_agent_memory` = **store knowledge** for single persistent agent (memory)
- CRANE has `list_agents` (get agent list); opencode has no agent registry
- **Integration**: opencode can spawn agents that call CRANE tools as MCP server

---

### 3.5 Permission Systems

#### opencode `permission.go` (Internal Service)
```go
type PermissionRequest struct {
    SessionID   string
    ToolName    string
    Action      string  // "read" | "write"
    Params      map[string]interface{}
    Path        string
    Description string
}
```
**Behavior**:
- Pub/sub pattern: tool calls published → LLM decides approve/modify/reject
- Auto-approval sessions bypass permission checks
- Session-scoped with persistent approval list

#### CRANE `add_permission_rule.py`
```python
def add_permission_rule(category: str,
                        rule: str,
                        project_dir: Optional[str] = None):
    """Write research governance rule to .crane/permission_rules.yaml"""

def evaluate_permission_action(action: str,
                                context: Optional[dict] = None):
    """Check if action is allowed by current rules"""
```
**Returns**: `{"allowed": true, "reason": "Rule X permits..."}`

**Mapping Notes**:
- opencode permission = **tool execution approval** (security)
- CRANE permission = **research workflow governance** (e.g., "don't submit before Phase 5")
- Different layers: opencode protects file system; CRANE protects research process
- **Integration**: CRANE rules could be fetched by opencode permission service

---

## 4. Integration Strategy Recommendations

### 4.1 Exposure Strategy: MCP vs. Built-in

| Tool Category | Keep as opencode Built-in | Expose as CRANE MCP Tool | Migration Effort |
|---------------|------------------------|------------------------|-----------------|
| File I/O (`view`, `write`, `edit`, `read`) | ✅ Keep | ❌ Don't expose | N/A - fundamental primitives |
| Search (`glob`, `grep`) | ✅ Keep | ❌ Don't expose | N/A - file system native |
| Shell (`bash`) | ✅ Keep | ❌ Don't expose | N/A - needs shell access |
| Agent Orchestration (`agent-tool`) | ✅ Keep | ❌ Don't expose | N/A - opencode internal |
| LSP Tools (`diagnostics`, `lsp_*`) | ✅ Keep | ⚠️ Optional | Medium - niche use case |
| Sourcegraph Search | ❌ Remove if unused | ✅ Expose as CRANE MCP | High - external API |
| HTTP Fetch (`fetch.go`) | ⚠️ Deprecate | ✅ Replace with CRANE MCP | Medium - redirect to domain tools |

**Rationale**:
- Keep **file system primitives** as built-in: opencode needs these to run ANY tool
- Expose **domain-specific tools** as MCP: CRANE provides research operations
- opencode becomes **tool execution engine**; CRANE becomes **plugin ecosystem**

---

### 4.2 Implementation Patterns

#### Pattern A: MCP Server Bridge (Recommended)
```
[User Request]
     ↓
[opencode session manager]
     ↓
[MCP Server Transport: stdio/sse]
     ↓
[CRANE MCP Server] ←─── All 90 tools
     ↓
[Result streamed back to opencode]
```

**Advantages**:
- Clean separation: opencode doesn't need to know CRANE internals
- Modular: swap CRANE for other MCP servers
- Already implemented in CRANE (`mcp_tool_orchestration.py`)

**Implementation Steps**:
1. Configure opencode `config.go` with CRANE MCP server
   ```go
   MCPServers: []MCPServer{
       {
           Name:    "crane",
           Type:    "stdio",
           Command: "uv",
           Args:    []string{"run", "python", "-m", "crane.mcp_server"},
           Env:     map[string]string{"PROJECT_DIR": "/home/augchao/opencode-crane"},
       },
   }
   ```
2. Add MCP tool routing in `tools.go`:
   ```go
   if tool.McpTool {
       return executeMCPCall(sessionID, tool.Name, params)
   }
   ```
3. Implement `executeMCPCall()` to forward to MCP transport

---

#### Pattern B: Direct Go Bindings (No MCP)
```
[User Request]
     ↓
[opencode session manager]
     ↓
[Go wrapper calls CRANE Python via subprocess]
     ↓
[JSON-RPC over stdio]
```

**Advantages**:
- Zero dependency on MCP spec
- Simpler debugging (direct Go → Python call)

**Disadvantages**:
- Must implement JSON-RPC transport from scratch
- Duplicates work already in CRANE's MCP server
- Not extensible to third-party tools

**Verdict**: ❌ Don't implement - use Pattern A (MCP already exists)

---

#### Pattern C: Hybrid (Critical Tools as Built-in)
```
[User Request]
     ↓
[if opencode built-in: use directly]
[if CRANE domain tool: route to MCP]
```

**Critical Tools to Keep as Built-in**:
- `view`, `write`, `edit` (file I/O)
- `bash` (shell execution)
- `agent-tool` (orchestration)
- `glob`, `grep` (search)

**Tools to Route to MCP**:
- All 90 CRANE tools
- Sourcegraph (if kept)
- LSP tools (optional)

**Verdict**: ✅ **RECOMMENDED** - Best of both worlds

---

### 4.3 Parameter Translation Layer

**Problem**: opencode params ↔ CRANE params don't match

**Solution**: Add translation map in `config.go`:
```go
var MCPCallTranslation = map[string]map[string]string{
    "read_paper": {
        "paperId":      "paper_id",      // camelCase → snake_case
        "saveDir":      "save_dir",
        "projectDir":   "project_dir",
    },
    "add_reference": {
        "key":      "key",
        "title":    "title",
        "authors":  "authors",
        "year":     "year",
        // ... map all fields
    },
}
```

**Translation Function**:
```go
func translateToMCPParams(toolName string, params map[string]interface{}) (map[string]interface{}, error) {
    if mapping, ok := MCPCallTranslation[toolName]; ok {
        translated := make(map[string]interface{})
        for key, value := range params {
            if mappedKey, ok := mapping[key]; ok {
                translated[mappedKey] = value
            } else {
                translated[key] = value  // passthrough
            }
        }
        return translated, nil
    }
    return params, nil
}
```

---

## 5. API Design: Unified Tool Interface

### 5.1 Proposed Tool Registry Schema

```go
type ToolRegistry struct {
    Name          string      `json:"name"`
    Description   string      `json:"description"`
    Category      string      `json:"category"`          // "file", "search", "agent", "research"
    IsMCP         bool        `json:"mcp"`
    MCPServerName string      `json:"mcp_server,omitempty"` // "crane", "sourcegraph"
    Parameters    []Parameter `json:"parameters"`
    RequiresRead  bool        `json:"requires_read,omitempty"` // For write safety
}

type Parameter struct {
    Name        string  `json:"name"`
    Type        string  `json:"type"`          // "string", "int", "array", "object"
    Required    bool    `json:"required"`
    Description string  `json:"description"`
    Default     string  `json:"default,omitempty"`
}
```

### 5.2 Tool Lookup API

```go
// Get tool schema by name (built-in or MCP)
func GetToolSchema(toolName string) (*ToolRegistry, error) {
    // Check built-in tools first
    if builtIn := getBuiltInTool(toolName); builtIn != nil {
        return builtIn, nil
    }
    
    // Check MCP servers
    for _, server := range config.MCPServers {
        if mcpTool := getMCPTool(server, toolName); mcpTool != nil {
            return mcpTool, nil
        }
    }
    
    return nil, fmt.Errorf("tool not found: %s", toolName)
}

// Execute tool call (unified entry point)
func ExecuteToolCall(sessionID string, toolName string, params map[string]interface{}) (map[string]interface{}, error) {
    schema, err := GetToolSchema(toolName)
    if err != nil {
        return nil, err
    }
    
    // Permission check (opencode permission.go)
    if !shouldApproveToolCall(sessionID, toolName, params) {
        return nil, fmt.Errorf("tool call not approved")
    }
    
    // Route to appropriate handler
    if schema.IsMCP {
        return executeMCPCall(sessionID, schema.MCPServerName, toolName, params)
    } else {
        return executeBuiltInTool(sessionID, toolName, params)
    }
}
```

---

## 6. Use Cases: How Users Will Interact

### 6.1 Research Paper Search (End-to-End)

**User Prompt**: "Find papers on attention mechanisms and add the top 3 to my library"

**Tool Execution Flow**:
```
1. [opencode session] receives prompt
2. [opencode agent-tool] spawns task agent with prompt
3. [task agent] calls CRANE MCP tool:
   crane.search_papers(query="attention mechanisms", max_results=3)
4. [CRANE] returns: [{"title": "...", "doi": "...", ...}]
5. [task agent] iterates results:
   crane.add_reference(key="...", title="...", ...)  # 3x calls
6. [CRANE] writes YAML files to references/papers/
7. [opencode view] reads created YAML files to show user
8. [opencode write] creates summary.md in refs/
```

**Key Insight**: opencode orchestrates, CRANE does the work

---

### 6.2 Citation Analysis (Multi-Tool Workflow)

**User Prompt**: "Analyze citations for my paper and generate a visualization"

**Tool Execution Flow**:
```
1. [opencode agent] calls: crane.build_citation_graph(source="semantic_scholar")
2. [CRANE] fetches citations from API, updates YAML files
3. [opencode agent] calls: crane.visualize_citation_graph(output_path="figs/citations.pdf")
4. [CRANE] generates PDF via Graphviz
5. [opencode view] reads PDF metadata (file size, dimensions)
6. [opencode write] generates analysis.md in docs/
```

---

### 6.3 Paper Evaluation (Hybrid Workflow)

**User Prompt**: "Evaluate my LaTeX paper for Q1 journal submission"

**Tool Execution Flow**:
```
1. [opencode view] reads /path/to/paper.tex
2. [opencode agent] calls: crane.evaluate_q1_standards(paper_path="/path/to/paper.tex")
3. [CRANE] returns evaluation report (7-dimension scorecard)
4. [opencode view] reads generated evaluation.yaml
5. [opencode agent] calls: crane.generate_revision_report(paper_path="/path/to/paper.tex")
6. [CRANE] generates markdown revision report
7. [opencode edit] suggests revisions to user (if permitted)
```

---

## 7. Implementation Roadmap

### Phase 1: MCP Server Configuration (1-2 days)
- [ ] Add CRANE MCP server to `config.go`
- [ ] Test stdio transport with `uv run python -m crane.mcp_server`
- [ ] Verify tool discovery: list all 90 CRANE tools

### Phase 2: Tool Execution Integration (2-3 days)
- [ ] Implement `executeMCPCall()` in `tools.go`
- [ ] Add parameter translation layer
- [ ] Test with simple tools: `list_references`, `get_reference`, `list_tasks`

### Phase 3: Permission Integration (1-2 days)
- [ ] Extend `permission.go` to handle MCP tool calls
- [ ] Configure auto-approval for safe tools (read-only)
- [ ] Add interactive approval for write tools

### Phase 4: Testing & Documentation (2-3 days)
- [ ] Write integration test: search → add → annotate workflow
- [ ] Document MCP server setup for developers
- [ ] Create tool catalog with examples

---

## 8. Appendix: CRANE Tool Categories

### 8.1 Paper Management (20 tools)
- `search_papers`, `add_reference`, `list_references`, `get_reference`, `remove_reference`
- `download_paper`, `read_paper`, `annotate_reference`, `screen_reference`, `compare_papers`
- `verify_reference`, `check_all_references`, `semantic_search`, `semantic_search_by_paper`

### 8.2 Citation Analysis (8 tools)
- `build_citation_graph`, `visualize_citation_graph`, `get_citation_mermaid`
- `find_citation_gaps`, `ask_library`, `chunk_papers`, `check_citations`, `get_chunk_stats`

### 8.3 Evaluation & Quality (12 tools)
- `evaluate_q1_standards`, `evaluate_paper_v2`, `review_paper_sections`
- `parse_paper_structure`, `analyze_paper_for_journal`, `find_similar_papers_in_journal`
- `generate_revision_report`, `generate_feynman_session`, `simulate_submission_outcome`

### 8.4 Research Workflow (15 tools)
- `create_task`, `list_tasks`, `view_task`, `update_task`, `close_task`
- `report_progress`, `get_milestone_progress`, `workspace_status`
- `run_pipeline`, `run_submission_check`, `get_research_clusters`

### 8.5 Agent Management (7 tools)
- `list_agents`, `get_agent`, `get_agent_memory`, `add_agent_memory`, `clear_agent_memory`

### 8.6 Project & Session (12 tools)
- `init_research`, `get_project_info`, `create_session`, `save_session`
- `load_session`, `list_sessions`, `delete_session`
- `start_sse_server`, `stop_sse_server`, `get_sse_status`

### 8.7 Advanced Features (16 tools)
- `deconstruct_conventional_wisdom`, `generate_figure`, `generate_comparison`
- `analyze_apc`, `match_journal_v2`, `critique_permission_rules`
- `add_permission_rule`, `remove_permission_rule`, `evaluate_permission_action`
- `check_crane_version`, `upgrade_crane`, `rollback_crane`
- `start_remote_bridge`, `stop_remote_bridge`, `generate_bridge_jwt`, `get_bridge_status`

---

## 9. References

- opencode source: `/home/augchao/opencode-crane/opencode/internal/tools/`
- CRANE MCP server: `/home/augchao/opencode-crane/src/crane/tools/mcp_tool_orchestration.py`
- MCP Specification: https://modelcontextprotocol.io/
- Thesis GitHub issues: Issues #2, #4, #5, #9 (Phase 1-2 complete)
