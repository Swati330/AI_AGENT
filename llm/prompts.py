"""
Prompt templates as constants/functions. Keeping prompts out of logic files
makes them easy to iterate on and review independently.
"""

INTENT_UNDERSTANDING_PROMPT = """You are an intent classifier for an AI agent. Given a user query, classify it into EXACTLY ONE of these intent types and extract relevant entities.

Intent types:
- "calculation": user wants a math expression evaluated (e.g. "what's 5 times 3", "calculate 20% of 450")
- "weather_query": user wants current weather for a location (e.g. "is it raining in Mumbai", "weather in Delhi")
- "knowledge_query": user wants a factual/encyclopedic answer about a topic (e.g. "who is Alan Turing", "what is photosynthesis")
- "unknown": query doesn't clearly match any of the above

Respond with ONLY valid JSON, no markdown fences, no extra text, in this EXACT shape:
{{
  "intent_type": "<one of: calculation, weather_query, knowledge_query, unknown>",
  "extracted_entities": {{}},
  "confidence": <float between 0 and 1>
}}

For calculation: extracted_entities should have "expression" as a valid Python-evaluable math string (e.g. "5 * 3", "450 * 0.20").
For weather_query: extracted_entities should have "city" as a string.
For knowledge_query: extracted_entities should have "topic" as a string containing ONLY the core subject/entity being asked about — a concise noun phrase suitable as a Wikipedia article title (e.g. "India", "Isaac Newton", "photosynthesis"), NOT the full question. Strip filler words like "what is", "who is", "the capital of" unless they're part of the actual entity name.
For unknown: extracted_entities should be an empty object {{}}.

User query: "{query}"

JSON response:"""

RESPONSE_GENERATION_PROMPT = """You are a helpful assistant. Convert this tool output into a short, natural, conversational answer for the user. Do not mention "tool", "data", "JSON", or any technical terms — just answer naturally like a helpful person would.

Tool used: {tool_name}
Data: {data}

Natural answer:"""

WIKI_FACT_EXTRACTION_PROMPT = """You are answering a user's question using ONLY the Wikipedia content provided below.

User's question: "{question}"

Wikipedia content:
{content}

Instructions:
- Answer the specific question directly and concisely, using only facts present in the content above.
- If the content does not contain the answer, say so honestly instead of guessing.
- Do not add outside knowledge not present in the content.

Answer:"""