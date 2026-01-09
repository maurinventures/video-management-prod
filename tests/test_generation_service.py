#!/usr/bin/env python3
"""
Test script for Prompt 20: Generation Pipeline Service

Tests the long-form content generation pipeline:
- Job creation
- Pipeline stage execution
- Content assembly
- Status tracking
"""

import sys
import os
import json
import uuid
sys.path.append('.')

from scripts.generation_service import GenerationService

def test_job_creation():
    """Test creating a generation job."""
    print("\n=== Testing Job Creation ===")

    try:
        # Test job creation
        job_id = GenerationService.create_generation_job(
            brief="Write a comprehensive guide about the benefits of remote work, focusing on productivity, work-life balance, and cost savings for both employees and companies.",
            job_name="Remote Work Benefits Guide",
            job_type="article",
            content_format="blog_post",
            target_word_count=2000,
            target_audience="HR managers and remote workers",
            user_id=str(uuid.uuid4())  # Use a valid UUID
        )

        print(f"✅ Job created successfully: {job_id}")
        return job_id

    except Exception as e:
        print(f"❌ Job creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_job_status(job_id):
    """Test getting job status."""
    print(f"\n=== Testing Job Status ({job_id[:8]}...) ===")

    try:
        status = GenerationService.get_job_status(job_id)
        if status:
            print(f"✅ Job status retrieved:")
            print(f"   Status: {status['status']}")
            print(f"   Progress: {status['progress_percentage']:.1f}%")
            print(f"   Sections: {status['sections_completed']}/{status['sections_total']}")
            return True
        else:
            print("❌ Job not found")
            return False

    except Exception as e:
        print(f"❌ Job status check failed: {e}")
        return False

def test_pipeline_execution(job_id):
    """Test running the pipeline stages."""
    print(f"\n=== Testing Pipeline Execution ({job_id[:8]}...) ===")

    try:
        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")

            result = GenerationService.continue_pipeline(job_id, "claude-sonnet")

            if 'error' in result:
                print(f"❌ Pipeline error: {result['error']}")
                return False

            stage = result.get('stage', 'unknown')
            status = result.get('status', 'unknown')

            print(f"✅ Stage: {stage} | Status: {status}")

            if result.get('job_completed', False):
                print("🎉 Pipeline completed successfully!")
                return True

            if stage == 'sectional_generation' and 'sections_remaining' in result:
                print(f"   Sections remaining: {result['sections_remaining']}")

        print(f"⚠️  Pipeline did not complete within {max_iterations} iterations")
        return False

    except Exception as e:
        print(f"❌ Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_content_retrieval(job_id):
    """Test getting the final content."""
    print(f"\n=== Testing Content Retrieval ({job_id[:8]}...) ===")

    try:
        content = GenerationService.get_completed_content(job_id)
        if content:
            print(f"✅ Content retrieved:")
            print(f"   Word count: {content['word_count']}")
            print(f"   Target: {content['target_word_count']}")
            print(f"   Total cost: ${content['total_cost']:.4f}")
            print(f"   Continuity issues: {len(content.get('continuity_issues', []))}")
            print(f"   Content preview: {content['assembled_content'][:200]}...")
            return True
        else:
            print("❌ Content not found")
            return False

    except Exception as e:
        print(f"❌ Content retrieval failed: {e}")
        return False

def test_content_formats():
    """Test different content format templates."""
    print("\n=== Testing Content Format Templates ===")

    try:
        formats = GenerationService.CONTENT_FORMATS
        print(f"✅ Available formats: {len(formats)}")

        for format_name, format_info in formats.items():
            sections = format_info.get('typical_sections', [])
            word_count = format_info.get('typical_word_count', 0)
            style = format_info.get('style_notes', 'No style notes')

            print(f"   {format_name:15} | {word_count:4d} words | {len(sections)} sections | {style}")

        return True

    except Exception as e:
        print(f"❌ Content format test failed: {e}")
        return False

def test_pipeline_stages():
    """Test pipeline stage constants."""
    print("\n=== Testing Pipeline Stages ===")

    try:
        stages = GenerationService.PIPELINE_STAGES
        print(f"✅ Pipeline stages ({len(stages)} total):")

        for i, stage in enumerate(stages, 1):
            print(f"   {i}. {stage}")

        # Test stage validation
        if GenerationService.STAGE_BRIEF_ANALYSIS in stages:
            print("✅ Stage constants are accessible")
            return True
        else:
            print("❌ Stage constants not found")
            return False

    except Exception as e:
        print(f"❌ Pipeline stage test failed: {e}")
        return False

def run_all_tests():
    """Run the complete test suite."""
    print("🚀 Starting Prompt 20: Generation Pipeline Service Test Suite")

    test_results = []

    # Test 1: Content formats
    test_results.append(("Content Formats", test_content_formats()))

    # Test 2: Pipeline stages
    test_results.append(("Pipeline Stages", test_pipeline_stages()))

    # Test 3: Job creation
    job_id = test_job_creation()
    test_results.append(("Job Creation", job_id is not None))

    if job_id:
        # Test 4: Job status
        test_results.append(("Job Status", test_job_status(job_id)))

        # Test 5: Pipeline execution
        pipeline_success = test_pipeline_execution(job_id)
        test_results.append(("Pipeline Execution", pipeline_success))

        if pipeline_success:
            # Test 6: Content retrieval
            test_results.append(("Content Retrieval", test_content_retrieval(job_id)))

    # Report results
    print("\n" + "="*60)
    print("🎯 TEST RESULTS SUMMARY")
    print("="*60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:20} | {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Generation Pipeline Service is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)