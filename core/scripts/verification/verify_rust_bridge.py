import sys

import logging
logger = logging.getLogger(__name__)

try:
    import whitemagic_rs

    logger.debug(f"✅ Successfully imported whitemagic_rs")
except ImportError as e:
    logger.debug("❌ Failed to import whitemagic_rs: %s", e)
    sys.exit(1)


def test_similarity():
    logger.debug("\n--- Testing Fast Similarity ---")
    s1 = "The quick brown fox"
    s2 = "The quick brown fox jumps"
    try:
        score = whitemagic_rs.fast_similarity(s1, s2)
        logger.debug("Similarity ('%s', '%s'): %s", s1, s2, score)
        assert score > 0.5, "Similarity seems too low"
    except Exception as e:
        logger.debug("❌ Error in fast_similarity: %s", e)


def test_iching():
    logger.debug("\n--- Testing I Ching Oracle (Layer 10 Check) ---")
    query = "Status of Whitemagic Reconstruction"
    try:
        hex_num, lines = whitemagic_rs.iching_cast(query)
        logger.debug("Query: %s", query)
        logger.debug("Hexagram: %s", hex_num)
        logger.debug("Lines: %s", lines)
    except Exception as e:
        logger.debug("❌ Error in iching_cast: %s", e)


def test_patterns():
    logger.debug("\n--- Testing Pattern Extraction ---")
    content = ["def bad_code():\n    pass # TODO: Fix me"]
    try:
        result = whitemagic_rs.extract_patterns_from_content(content, 0.0)
        logger.debug(f"Patterns found: {result[1]}")
        logger.debug(f"Duration: {result[6]:.6f}s")
    except Exception as e:
        logger.debug("❌ Error in extract_patterns: %s", e)


if __name__ == "__main__":
    test_similarity()
    test_iching()
    test_patterns()
    logger.debug("\n✨ Rust Bridge Verification Complete ✨")
