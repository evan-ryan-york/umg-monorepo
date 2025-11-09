# Prompt Management System

This directory contains YAML-based prompt templates for AI agents.

## Features

- **Hot-reload**: Changes take effect immediately without restarting the server
- **Version control**: All prompts are tracked in Git
- **Web UI**: Edit prompts at `http://localhost:3110/prompts`
- **YAML validation**: Syntax errors are caught before saving

## Directory Structure

```
prompts/
├── README.md              # This file
├── prompt_manager.py      # Python class for loading prompts
└── mentor_chat.yaml       # Mentor chat prompt configuration
```

## Usage

### In Code

```python
from prompts.prompt_manager import prompt_manager

# Build a prompt
prompt = prompt_manager.build_mentor_chat_prompt(
    message="What should I focus on today?",
    conversation_history=[],
    context={
        "core_identity": [...],
        "high_priority": [...],
        # ...
    }
)
```

### Web UI

1. Navigate to `http://localhost:3110/prompts`
2. Select a prompt from the sidebar
3. Edit the YAML content
4. Click "Save" to apply changes

Changes are applied immediately - the next API call will use the updated prompt.

## YAML Structure

Each prompt file follows this structure:

```yaml
# System role definition
system_role: |
  You are the Mentor - a strategic thinking partner...

# Context sections to include
context_sections:
  core_identity:
    enabled: true
    max_items: 5
    header: "User's Goals & Values:"

# Instructions for the model
instructions:
  - "Respond conversationally and helpfully"
  - "Reference specific entities from the knowledge graph"

# Critical guidelines
critical_guidelines:
  - "Ground responses in their actual work"
  - "Be direct and actionable, not generic"
```

## Best Practices

1. **Keep sections modular**: Each section can be enabled/disabled independently
2. **Use descriptive headers**: Make it clear what context is being provided
3. **Test changes**: Use the chat UI to verify prompt changes work as expected
4. **Commit changes**: Treat prompts like code - commit and document changes

## Troubleshooting

- **Syntax errors**: The API will return validation errors if YAML is invalid
- **Changes not applying**: Check file permissions and ensure hot-reload is working
- **Missing context**: Verify that the context sections match what the agent provides
