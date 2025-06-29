# Database Schema Documentation

This document describes the SQL tables created by the MCP Project Knowledge Server for managing Claude Desktop project knowledge and context.

## Overview

The MCP Project Knowledge Server creates four SQL tables in Claude Desktop's SQLite database to provide advanced project knowledge management capabilities. These tables are designed to integrate seamlessly with Claude Desktop while providing enhanced functionality for structured knowledge storage and retrieval.

**Database Location**: `~/Library/Application Support/Claude/claudeSQLite.db`

## Table Schemas

### 1. `notes` Table (Claude Desktop Integration)

**Purpose**: Direct integration with Claude Desktop's Project knowledge UI. Entries in this table appear in Claude Desktop's interface.

```sql
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Fields**:
- `id`: Auto-incrementing primary key
- `title`: Knowledge entry title (displayed in UI)
- `content`: Full knowledge content (formatted with metadata)
- `created_at`: Timestamp of creation

**Integration**: This table directly feeds Claude Desktop's "Project knowledge" section in the UI.

### 2. `project_knowledge` Table (Advanced Storage)

**Purpose**: Enhanced knowledge management with categorization, tagging, and importance scoring.

```sql
CREATE TABLE IF NOT EXISTS project_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    tags TEXT,  -- JSON array of tags
    importance INTEGER CHECK (importance BETWEEN 1 AND 5) DEFAULT 3,
    source TEXT DEFAULT 'conversation',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Fields**:
- `id`: Auto-incrementing primary key
- `title`: Knowledge entry title
- `content`: Raw knowledge content (without formatting)
- `category`: Classification (e.g., 'technical', 'business', 'preferences')
- `tags`: JSON array of tags for organization
- `importance`: Priority level (1=low, 5=critical)
- `source`: Origin of knowledge ('conversation', 'file', 'manual')
- `created_at`: Creation timestamp
- `updated_at`: Last modification timestamp

**Usage**: Enables advanced querying, filtering, and organization of knowledge entries.

### 3. `project_instructions` Table (Behavior Guidelines)

**Purpose**: Stores dynamic project instructions and behavior guidelines that can be updated programmatically.

```sql
CREATE TABLE IF NOT EXISTS project_instructions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section TEXT NOT NULL,
    content TEXT NOT NULL,
    priority INTEGER CHECK (priority BETWEEN 1 AND 5) DEFAULT 3,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Fields**:
- `id`: Auto-incrementing primary key
- `section`: Instruction category ('context', 'guidelines', 'constraints', 'objectives')
- `content`: Instruction content
- `priority`: Priority level (1=low, 5=critical)
- `active`: Whether instruction is currently active (1=active, 0=inactive)
- `created_at`: Creation timestamp
- `updated_at`: Last modification timestamp

**Usage**: Allows dynamic modification of how Claude should behave in specific project contexts.

### 4. `project_context` Table (Dynamic Context Tracking)

**Purpose**: Tracks current project focus, active tasks, and dynamic context information.

```sql
CREATE TABLE IF NOT EXISTS project_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_key TEXT UNIQUE NOT NULL,
    context_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Fields**:
- `id`: Auto-incrementing primary key
- `context_key`: Unique context identifier ('current_focus', 'active_task', 'last_discussion')
- `context_value`: Current value for the context
- `description`: Optional description of the context
- `updated_at`: Last update timestamp

**Usage**: Maintains real-time project state and context information.

## Data Flow and Integration

### Dual Storage Strategy

The MCP server uses a dual storage approach:

1. **UI Integration**: Knowledge entries are stored in the `notes` table with formatted content for Claude Desktop's UI
2. **Advanced Management**: The same entries are stored in `project_knowledge` with structured metadata for advanced querying

### Example Data Flow

When adding knowledge via `add_project_knowledge`:

```python
# 1. Create structured entry
entry = ProjectKnowledgeEntry(
    title="API Integration Guidelines",
    content="Always use error handling...",
    category="technical",
    tags=["api", "guidelines", "best-practices"],
    importance=4
)

# 2. Format for Claude Desktop UI
formatted_content = f"""Project: {project_name}
Category: {entry.category}
Importance: {entry.importance}/5
Tags: {', '.join(entry.tags)}

{entry.content}"""

# 3. Insert into both tables
cursor.execute("INSERT INTO notes (title, content) VALUES (?, ?)", 
               (entry.title, formatted_content))

cursor.execute("INSERT INTO project_knowledge (...) VALUES (...)",
               (entry.title, entry.content, entry.category, ...))
```

## MCP Tools and Database Operations

### Knowledge Management Tools

- **`add_project_knowledge`**: Inserts into both `notes` and `project_knowledge` tables
- **`search_project_knowledge`**: Queries `project_knowledge` with filtering
- **`get_project_overview`**: Aggregates data from all tables

### Instruction Management Tools

- **`update_project_instructions`**: Manages `project_instructions` table
- **`get_project_overview`**: Displays active instructions

### Context Management Tools

- **`update_project_context`**: Updates `project_context` table
- **`check_project_context`**: Displays current context state

## Database Maintenance

### Backup Considerations

Since the database is located in Claude Desktop's application support directory, consider:

1. **Automatic Backups**: Claude Desktop may handle this automatically
2. **Manual Backups**: Copy `claudeSQLite.db` before major operations
3. **Data Export**: Use MCP tools to export knowledge in structured formats

### Performance Optimization

The tables include appropriate indexes:
- Primary keys on all `id` columns
- Timestamps for chronological queries
- Unique constraints where appropriate (`context_key` in `project_context`)

### Data Integrity

- Foreign key relationships are implicit (no formal constraints to maintain Claude Desktop compatibility)
- Check constraints ensure data validity (importance levels, priority levels)
- NOT NULL constraints on essential fields

## Example Queries

### Finding High-Priority Knowledge

```sql
SELECT title, category, importance, created_at 
FROM project_knowledge 
WHERE importance >= 4 
ORDER BY importance DESC, created_at DESC;
```

### Getting Active Instructions by Priority

```sql
SELECT section, content, priority 
FROM project_instructions 
WHERE active = 1 
ORDER BY priority DESC, section;
```

### Recent Context Updates

```sql
SELECT context_key, context_value, updated_at 
FROM project_context 
ORDER BY updated_at DESC 
LIMIT 10;
```

## Migration and Compatibility

### Claude Desktop Compatibility

The database schema is designed to:
- Not interfere with Claude Desktop's existing functionality
- Use `CREATE TABLE IF NOT EXISTS` to avoid conflicts
- Store data in Claude Desktop's established database location

### Future Considerations

- Schema migrations should preserve existing data
- New columns should have default values
- Consider versioning for schema changes

## Security and Privacy

### Data Sensitivity

- Knowledge content may contain sensitive information
- Database is stored locally on user's machine
- No data is transmitted to external services (except via explicit user actions)

### Access Control

- Database access is restricted to:
  - Claude Desktop application
  - MCP servers with appropriate permissions
  - User with direct file system access

## Troubleshooting

### Common Issues

1. **Database Locked**: Ensure Claude Desktop is not running during direct database access
2. **Permission Issues**: Check file permissions on `claudeSQLite.db`
3. **Schema Conflicts**: Use `CREATE TABLE IF NOT EXISTS` to avoid conflicts
4. **Data Corruption**: Regular backups and validation queries recommended

### Diagnostic Queries

```sql
-- Check table existence
.tables

-- Verify data integrity
SELECT COUNT(*) FROM notes;
SELECT COUNT(*) FROM project_knowledge;
SELECT COUNT(*) FROM project_instructions;
SELECT COUNT(*) FROM project_context;

-- Check for orphaned records
SELECT n.id, n.title 
FROM notes n 
LEFT JOIN project_knowledge pk ON n.title = pk.title 
WHERE pk.id IS NULL;
```

## Conclusion

This database schema provides a robust foundation for advanced project knowledge management while maintaining compatibility with Claude Desktop's existing functionality. The dual storage approach ensures both UI integration and advanced capabilities, making it a powerful tool for organizing and accessing project-specific information.