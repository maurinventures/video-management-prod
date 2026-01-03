#!/usr/bin/env python3
"""
Diagnostic Report: Search & Context Pipeline
Perspective: Claude LLM Engineer + Surge.ai Data Engineer
"""
import sys
sys.path.insert(0, '/home/ec2-user/video-management')

from web.app import DatabaseSession, TranscriptSegment, Transcript, Video, search_transcripts_for_context

print("=" * 70)
print("DIAGNOSTIC REPORT: Why Caterpillar/Butterfly Content Not Reaching Model")
print("=" * 70)

# =============================================================================
# 1. DATA LAYER CHECK (Surge.ai perspective)
# =============================================================================
print("\n" + "=" * 70)
print("1. DATA LAYER: Is the content in the database?")
print("=" * 70)

with DatabaseSession() as db:
    cat_segs = db.query(TranscriptSegment).filter(
        TranscriptSegment.text.ilike("%caterpillar%")
    ).all()
    but_segs = db.query(TranscriptSegment).filter(
        TranscriptSegment.text.ilike("%butterfly%")
    ).all()

    print(f"✓ Segments with 'caterpillar': {len(cat_segs)}")
    print(f"✓ Segments with 'butterfly': {len(but_segs)}")

    print("\nSample caterpillar segments:")
    for i, s in enumerate(cat_segs[:3]):
        print(f"  {i+1}. \"{s.text[:100]}...\"")

# =============================================================================
# 2. SEARCH LAYER CHECK
# =============================================================================
print("\n" + "=" * 70)
print("2. SEARCH LAYER: Does search_transcripts_for_context find them?")
print("=" * 70)

results = search_transcripts_for_context("caterpillar butterfly")
print(f"Total results returned: {len(results)}")

cat_in_results = [r for r in results if "caterpillar" in r["text"].lower()]
but_in_results = [r for r in results if "butterfly" in r["text"].lower()]
print(f"Results containing 'caterpillar': {len(cat_in_results)}")
print(f"Results containing 'butterfly': {len(but_in_results)}")

if len(cat_in_results) < len(cat_segs):
    print(f"\n⚠️  WARNING: Only {len(cat_in_results)}/{len(cat_segs)} caterpillar segments found!")
    print("   Some segments may be filtered by year or status")

# =============================================================================
# 3. RANKING CHECK (Critical for LLM context)
# =============================================================================
print("\n" + "=" * 70)
print("3. RANKING: Where do caterpillar results appear in the list?")
print("=" * 70)

cat_positions = []
for i, r in enumerate(results):
    if "caterpillar" in r["text"].lower():
        cat_positions.append(i + 1)

if cat_positions:
    print(f"Caterpillar results at positions: {cat_positions[:10]}...")
    print(f"First caterpillar result: position {cat_positions[0]}")
    print(f"Last caterpillar result: position {cat_positions[-1]}")

    if cat_positions[0] > 50:
        print("\n⚠️  PROBLEM: Caterpillar content is buried deep in results!")
        print("   Model may not see it due to context limits")
else:
    print("❌ CRITICAL: No caterpillar results found!")

# =============================================================================
# 4. CONTEXT BUILDING SIMULATION
# =============================================================================
print("\n" + "=" * 70)
print("4. CONTEXT BUILDING: What actually gets sent to Claude?")
print("=" * 70)

# Simulate the context building with Claude's limits
max_segments = 300  # Claude limit
max_chars = 100000  # Claude limit

seen_passages = set()
total_chars = 0
segments_included = 0
cat_included = 0
but_included = 0

for t in results[:max_segments]:
    passage_key = (t['video_id'], round(t['start'], 0))
    if passage_key in seen_passages:
        continue
    seen_passages.add(passage_key)

    text = t["text"].strip()
    if len(text) < 15:
        continue

    # Build entry
    entry_len = len(text) + 100  # approx overhead

    if total_chars + entry_len > max_chars:
        print(f"Hit character limit at segment {segments_included}")
        break

    total_chars += entry_len
    segments_included += 1

    if "caterpillar" in text.lower():
        cat_included += 1
    if "butterfly" in text.lower():
        but_included += 1

print(f"Total segments included in context: {segments_included}")
print(f"Total characters: {total_chars}")
print(f"Caterpillar segments in context: {cat_included}")
print(f"Butterfly segments in context: {but_included}")

# =============================================================================
# 5. ROOT CAUSE ANALYSIS
# =============================================================================
print("\n" + "=" * 70)
print("5. ROOT CAUSE ANALYSIS")
print("=" * 70)

issues = []

if len(cat_in_results) == 0:
    issues.append("CRITICAL: Search returns 0 caterpillar results - check search function")
elif cat_included == 0:
    issues.append("CRITICAL: Caterpillar content filtered out during context building")
elif cat_included < 5:
    issues.append(f"WARNING: Only {cat_included} caterpillar segments reach model")

if cat_positions and cat_positions[0] > 30:
    issues.append(f"WARNING: Caterpillar content starts at position {cat_positions[0]} - may be lost in context")

# Check if surrounding context expansion is diluting
print("\nChecking surrounding context expansion...")
sample = cat_in_results[0] if cat_in_results else None
if sample:
    orig_text = sample['text']
    has_cat_in_expanded = "caterpillar" in orig_text.lower()
    print(f"Sample expanded text length: {len(orig_text)} chars")
    print(f"Contains 'caterpillar': {has_cat_in_expanded}")
    if not has_cat_in_expanded:
        issues.append("WARNING: Surrounding context expansion may be diluting keyword matches")

if issues:
    print("\n🔴 ISSUES FOUND:")
    for issue in issues:
        print(f"   • {issue}")
else:
    print("\n✓ Data pipeline looks correct")
    print("   Issue may be in system prompt or model behavior")

# =============================================================================
# 6. RECOMMENDATION
# =============================================================================
print("\n" + "=" * 70)
print("6. RECOMMENDATIONS")
print("=" * 70)

if cat_included > 0:
    print("""
The caterpillar/butterfly content IS reaching the model ({} segments).
The issue is likely:

1. PROMPT ISSUE: The system prompt tells model to "look for COMPLETE THOUGHTS"
   but caterpillar segments may start mid-sentence

2. MODEL BEHAVIOR: Model may be selecting "safer" clips about general topics
   instead of the specific caterpillar metaphor

3. CONTEXT DILUTION: {} other segments compete for attention

FIXES TO TRY:
- Boost ranking of keyword matches (put them FIRST in context)
- Add explicit instruction: "PRIORITIZE segments containing user's keywords"
- Reduce total context to make relevant content more prominent
""".format(cat_included, segments_included - cat_included))
else:
    print("""
CRITICAL: Caterpillar content not reaching the model.
Check the search_transcripts_for_context function.
""")
