# Document Tools

The document tools allow the AI agent to interact with documents uploaded to a conversation.
They are automatically injected when documents are present and `DOCUMENT_TOOLS_ENABLED` is `true` (default).

## Environment Variables

| Variable                   | Description                                                              | Default  |
|----------------------------|--------------------------------------------------------------------------|----------|
| `DOCUMENT_TOOLS_ENABLED`   | Enable/disable document tools injection                                  | `true`   |
| `DOCUMENT_CONTENT_MAX_SIZE`| Maximum document size (bytes) for full-text retrieval. Larger docs use RAG | `200000` |

## document_list

Lists all documents available in the current conversation with their names, types, and sizes.

**Parameters:** None (uses conversation context)

**Returns:** A list of documents ordered by upload date (oldest first).

**When it's used:** The LLM calls this tool when the user asks about available documents,
wants to know which files were uploaded, or before referencing a document by name.

**Example user prompts:**
- "What documents do I have?"
- "Summarize the last document" (calls `document_list` first to find it)
- "List my uploaded files"

## document_get_content

Retrieves the full text content of a document by its name.

**Parameters:**

| Parameter       | Type   | Required | Description                                                |
|-----------------|--------|----------|------------------------------------------------------------|
| `document_name` | string | Yes      | Name (or partial name) of the document to retrieve         |
| `max_length`    | int    | No       | Maximum number of characters to return (truncates if longer)|

**Returns:** The full text content of the document.

**Size limit:** Documents larger than `DOCUMENT_CONTENT_MAX_SIZE` (default 200KB) are rejected
with a suggestion to use `document_search_rag` instead.

**When it's used:** The LLM calls this tool when the user wants to read, extract, or see
the full text of a document (not just search for specific passages).

**Example user prompts:**
- "Extract the text from this file"
- "Show me the content of report.pdf"
- "Read this document"

## document_analyze

Analyzes multiple documents together to compare, match, or cross-reference them.

**Parameters:**

| Parameter        | Type     | Required | Description                                               |
|------------------|----------|----------|-----------------------------------------------------------|
| `document_names` | string[] | Yes      | List of document names to analyze (at least 2 required)   |
| `analysis_type`  | string   | No       | Type of analysis (default: `"compare"`)                   |
| `instructions`   | string   | No       | Specific instructions for the analysis                    |

**Analysis types:**

| Type              | Description                                                  | Use case example                    |
|-------------------|--------------------------------------------------------------|-------------------------------------|
| `compare`         | Find similarities and differences between documents          | Comparing two versions of a contract|
| `match`           | Evaluate how well documents match each other                 | CV vs job posting                   |
| `compliance`      | Check if a document complies with reference documents        | Report vs specifications            |
| `extract`         | Extract and compare specific information across documents    | Comparing prices across quotes      |
| `cross_reference` | Cross-reference information between documents                | Building a unified view from sources|

**Size limit:** The cumulative size of all documents must not exceed `DOCUMENT_CONTENT_MAX_SIZE`.

**Example user prompts:**
- "Compare my CV with this job posting"
- "Check if the report complies with the specifications"
- "What are the differences between these two contracts?"

## Configuration

Document tools are not listed in the model's `tools` array. They are dynamically injected
by the agent when the conversation has uploaded documents and `DOCUMENT_TOOLS_ENABLED` is `true`.

No additional configuration is needed beyond the environment variables above.

## See Also

- [Tools Overview](../tools.md) - All available tools
- [Environment Variables](../env.md) - Configuration reference
