# Module 1 worksheet — Design map

For each example question, decide the right architecture and what it would need. Fill the blanks
during the Module-1 discussion.

| User question | Best fit: agent / prompt-only LLM / classical ML? | Why | Modalities needed | Tool types (retrieval / analysis / viz) |
| --- | --- | --- | --- | --- |
| "Why have I been sleeping poorly this week?" | | needs to re-query + analyze on demand | sleep, screen_time, EMA | retrieval + analysis (+ viz) |
| "How does my activity compare to my goal?" | | | steps, users.goal | retrieval + analysis |
| "Classify each night as good/poor sleep" | | fixed label, lots of data | sleep | (classical ML) |
| "Summarize my week in one paragraph" | | one-shot, no follow-up | several | (prompt-only) |
| "Is my resting HR trend concerning?" | | safety-sensitive; must refuse advice | heart_rate | retrieval + analysis + REFUSAL |
| _your own question_ | | | | |

**Design tensions to keep in mind:** grounding (cite retrieved values), multimodal missingness,
latency/cost (tool calls add round-trips), and safety (refuse medical advice; never fabricate).

**Output:** a shared sense of *where an agent adds value* vs. prompt-only or classical ML.
