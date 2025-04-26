# Claude Project Instructions Template

When setting up your Claude project, use the following template in your system prompt to ensure the memory context script works correctly:

```
# Project Instructions

[Your regular instructions here]

<!-- MEMORY CONTEXT START -->
You have a searchable memory. This section will be automatically updated by the memory context script.
<!-- MEMORY CONTEXT END -->

[Any additional instructions here]
```

The script will look for and replace everything between the `<!-- MEMORY CONTEXT START -->` and `<!-- MEMORY CONTEXT END -->` tags, so it's important to include these exact markers in your project system prompt.

## Example of Generated Memory Context

After the script runs, your memory context section might look like this:

```
<!-- MEMORY CONTEXT START -->
You have a searchable memory. 

Recent topics you remember include: programming, python, machine learning, data analysis, meeting notes.

Important long-term memories include:
- Project deadline for TechCorp is May 15th, 2025. Deliverables include API integration and dashboard...
- My daughter's birthday is June 12. She wants a science kit and books about space...
- Monthly team meeting agenda template: 1. Project updates 2. Roadblocks 3. Next sprint planning...

If the user mentions any of these topics or needs additional information, you can help them retrieve more from their memory by suggesting they ask about specific topics or use the memory search functions.
<!-- MEMORY CONTEXT END -->
```

## Tips for Structuring Your Project Instructions

1. Place the memory context section where it makes the most sense for your workflow - typically near the beginning so Claude is immediately aware of memory capabilities
2. Keep your other instructions separate from the memory section
3. You can still use all other Claude project features alongside memory context
4. The script preserves all your other instructions outside the marked section