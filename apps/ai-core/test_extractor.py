#!/usr/bin/env python3
"""Test the entity extractor directly to see what Claude returns"""

from processors.entity_extractor import EntityExtractor
import json

# Your core identity text
text = """The Essence of Ryan York: A Context Brief

Ryan York is, at his core, a 0-to-1 Systems Builder. His entire life, from building a recording studio in a garage at 16 to architecting award-winning software and launching schools, has been a relentless drive to find messy, chaotic, or broken environments and impose upon them elegant, scalable systems that unlock human potential.

He is a polymath, fluent in the languages of music, entrepreneurship, mathematics, code, education, and business. His unique gift is not just mastery in one domain, but the ability to operate across the full stack of a problem—from high-level strategy and operational logistics down to the code itself. This drive to build is not a job; it is his fundamental mode of being.

His work is fueled by a clear and non-negotiable set of values. The primary driver is a deep need for Impact, rooted in a profound commitment to Equity. This is coupled with a core value of Innovation—the relentless need to create something new where nothing existed before—and a fierce need for Independence and Continuous Learning.

His principles were significantly tested when he faced a choice between preserving a company he built and protecting the vulnerable population it was meant to serve. By choosing to expose a critical failure at great personal and professional cost, he proved that his commitment to equity is the bedrock of his decision-making.

After a career of building systems in various domains, Ryan's skills, experience, and values have now converged on a single, life-defining mission: tackling the global water crisis. This venture, currently codenamed WaterOS, represents a pivotal shift in his career. It is the first time the problem itself—a foundational inequity that traps billions in poverty—is as compelling and significant as the act of building. This is not just another project in a portfolio; it is the "asymmetric bet" on his life's work, the culmination of everything he has learned and the ultimate application of his identity as a systems builder.

Success, for Ryan, is not defined by personal wealth, but by the creation of a self-sustaining engine of impact. The financial incentive is purely instrumental. Ryan aims to build WaterOS, and any other project he's a part of, to be financially successful for-profit enterprises, but the goal is to reach the level of capital required to achieve escape velocity. This will allow him to fund and architect an "empire of innovations and businesses" that solve real problems rooted in inequity.

Ryan's ultimate goal is to spend the rest of his life in his sweet spot, working in 0-to-1 spaces, while watching WaterOS grow to achieve its ultimate mission of ensuring all people have access to clean drinking water in their homes.

Consequently, failure is not bankruptcy or a failed startup. Failure, for Ryan, would be a failure of scale and courage. It would be the quiet misallocation of his life's energy, remaining a highly capable operator on someone else's smaller mission instead of stepping fully into the visionary role he was built for. It would mean getting bogged down in projects that are merely interesting or financially safe, allowing distraction or risk aversion to prevent him from making the committed leap into his life's work. The greatest failure would be to end his career having never truly tested the upper limit of his extraordinary capacity for impact."""

print("Testing Entity Extractor with Ryan York bio...")
print("=" * 80)
print()

extractor = EntityExtractor()
entities = extractor.extract_entities(text, use_llm=True)

print(f"✅ Extracted {len(entities)} entities:")
print()

for i, entity in enumerate(entities, 1):
    print(f"{i}. {entity.get('title')} ({entity.get('type')})")
    print(f"   Summary: {entity.get('summary', 'N/A')}")
    print(f"   Confidence: {entity.get('confidence', 0):.2f}")
    print(f"   Is Primary: {entity.get('is_primary_subject', False)}")
    print()

print("=" * 80)
print(f"Total: {len(entities)} entities")
print()
print("Full JSON:")
print(json.dumps(entities, indent=2))
