"""Static rotating fun-facts about LLMs and prompting."""
from __future__ import annotations

import random

FACTS: list[str] = [
    "LLMs don't actually 'think' — they predict the next most-likely token based on billions of training examples.",
    "The term 'prompt engineering' was coined around 2021 as people discovered that small wording changes dramatically alter LLM outputs.",
    "GPT stands for Generative Pre-trained Transformer — the Transformer architecture was introduced by Google in 2017.",
    "Claude, ChatGPT, and Gemini all use a variant of the same Transformer architecture under the hood.",
    "A 'token' is roughly ¾ of a word in English — 'Hello, world!' is about 4 tokens.",
    "Temperature controls randomness: 0 = deterministic, 1 = creative, >1 = chaotic!",
    "The largest LLMs have been trained on more text than any human could read in thousands of lifetimes.",
    "Chain-of-thought prompting (asking an LLM to 'think step by step') can double accuracy on math problems.",
    "Role prompts like 'Act as a doctor' can significantly shift an LLM's vocabulary and reasoning style.",
    "Few-shot prompting — giving 2–5 examples before your question — often outperforms zero-shot prompting.",
    "LLMs have a 'context window' — a limit to how much text they can consider at once, measured in tokens.",
    "Hallucination happens when an LLM confidently generates plausible-sounding but incorrect information.",
    "RLHF (Reinforcement Learning from Human Feedback) is how models like ChatGPT learned to be helpful and polite.",
    "The word 'Transformer' in LLM architecture refers to the self-attention mechanism, not a robot in disguise.",
    "Asking an LLM to 'take a deep breath and think carefully' has been shown to measurably improve accuracy.",
    "System prompts are instructions given before the conversation starts — that's exactly what this game uses!",
    "Claude is trained by Anthropic with a focus on being Helpful, Harmless, and Honest — the '3 H's'.",
    "The number of parameters in an LLM roughly correlates with its capability — GPT-4 is estimated at ~1.7 trillion.",
    "Prompt injection is a security attack where hidden text in input tries to override the system prompt.",
    "LLMs are stateless between conversations — they have no true memory unless given tools or context.",
    "The 'emergent abilities' of large models (like arithmetic and code) weren't explicitly trained — they appeared spontaneously.",
    "Retrieval-Augmented Generation (RAG) lets LLMs look things up in real time instead of relying solely on training data.",
    "A well-crafted persona prompt can make any LLM maintain a fictional character for an entire conversation.",
    "Multimodal models can process images, audio, and text — blurring the line between AI systems.",
    "The average human reads ~250 words/min. GPT-4 can generate ~50 words/second. That's 12× reading speed.",
]


def get_random_fact() -> str:
    return random.choice(FACTS)


def get_facts_page(count: int = 3) -> list[str]:
    return random.sample(FACTS, min(count, len(FACTS)))
