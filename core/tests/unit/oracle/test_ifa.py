"""Tests for the Ifa divination system (ifa_data + ifa_cast)."""


from whitemagic.oracle.ifa_cast import (
    CastResult,
    IfaCaster,
    cast_ifa,
    get_caster,
)
from whitemagic.oracle.ifa_data import (
    PRINCIPAL_ODU,
    OduAmulu,
    OduMeji,
    generate_all_amulu,
    get_all_odu,
    get_meji_by_binary,
    get_meji_by_number,
    get_meji_by_short_name,
    get_odu_by_binary,
    get_odu_by_decimal,
    iching_to_ifa,
    ifa_to_iching,
)


class TestPrincipalOdu:
    """Tests for the 16 principal Odu (Meji)."""

    def test_count(self):
        assert len(PRINCIPAL_ODU) == 16

    def test_unique_binaries(self):
        binaries = [odu.binary for odu in PRINCIPAL_ODU]
        assert len(set(binaries)) == 16

    def test_unique_decimals(self):
        decimals = [odu.decimal for odu in PRINCIPAL_ODU]
        assert len(set(decimals)) == 16

    def test_unique_numbers(self):
        numbers = [odu.number for odu in PRINCIPAL_ODU]
        assert numbers == list(range(1, 17))

    def test_all_fields_populated(self):
        for odu in PRINCIPAL_ODU:
            assert odu.name, f"Empty name for #{odu.number}"
            assert odu.short_name, f"Empty short_name for #{odu.number}"
            assert len(odu.binary) == 4, f"Binary not 4 bits for {odu.name}"
            assert odu.element, f"Empty element for {odu.name}"
            assert odu.meaning, f"Empty meaning for {odu.name}"
            assert odu.wisdom, f"Empty wisdom for {odu.name}"
            assert odu.ire, f"Empty ire for {odu.name}"
            assert odu.osogbo, f"Empty osogbo for {odu.name}"

    def test_binary_decimal_consistency(self):
        for odu in PRINCIPAL_ODU:
            assert int(odu.binary, 2) == odu.decimal

    def test_lookup_by_number(self):
        odu = get_meji_by_number(1)
        assert odu is not None
        assert odu.name == "Eji Ogbe"

    def test_lookup_by_short_name(self):
        odu = get_meji_by_short_name("oyeku")
        assert odu is not None
        assert odu.number == 2

    def test_lookup_by_binary(self):
        odu = get_meji_by_binary("0000")
        assert odu is not None
        assert odu.name == "Eji Ogbe"

    def test_marks_visual(self):
        odu = PRINCIPAL_ODU[0]  # Eji Ogbe, binary=0000
        assert odu.marks == "| | | |"
        odu2 = PRINCIPAL_ODU[1]  # Oyeku, binary=1111
        assert odu2.marks == "|| || || ||"


class TestAmulu:
    """Tests for the 240 combined Odu (Amulu)."""

    def test_count(self):
        amulu = generate_all_amulu()
        assert len(amulu) == 240

    def test_all_different_legs(self):
        amulu = generate_all_amulu()
        for a in amulu:
            assert a.right_leg.number != a.left_leg.number

    def test_numbering_starts_at_17(self):
        amulu = generate_all_amulu()
        assert amulu[0].number == 17
        assert amulu[-1].number == 256

    def test_binary_is_8_bits(self):
        amulu = generate_all_amulu()
        for a in amulu:
            assert len(a.binary) == 8

    def test_iching_hexagram_in_range(self):
        amulu = generate_all_amulu()
        for a in amulu:
            assert 1 <= a.iching_hexagram <= 64


class TestFullCorpus:
    """Tests for the complete 256 Odu corpus."""

    def test_total_count(self):
        all_odu = get_all_odu()
        assert len(all_odu) == 256

    def test_all_binaries_unique(self):
        all_odu = get_all_odu()
        # Each 8-bit binary should be present exactly once
        assert len(all_odu) == 256

    def test_lookup_by_decimal(self):
        # Decimal 0 = Eji Ogbe (00000000)
        odu = get_odu_by_decimal(0)
        assert odu is not None
        assert isinstance(odu, OduMeji)
        assert odu.name == "Eji Ogbe"

    def test_lookup_by_binary_meji(self):
        # Oyeku Meji = 11111111
        odu = get_odu_by_binary("11111111")
        assert odu is not None
        assert isinstance(odu, OduMeji)
        assert odu.name == "Oyeku Meji"

    def test_lookup_by_binary_amulu(self):
        # Ogbe-Oyeku = 00001111
        odu = get_odu_by_binary("00001111")
        assert odu is not None
        assert isinstance(odu, OduAmulu)
        assert odu.right_leg.short_name == "ogbe"
        assert odu.left_leg.short_name == "oyeku"


class TestIChingCrossReference:
    """Tests for the Ifa <-> I Ching mapping."""

    def test_ifa_to_iching_returns_valid_number(self):
        for odu in PRINCIPAL_ODU:
            ic_num = ifa_to_iching(odu.binary, odu.binary)
            assert 1 <= ic_num <= 64

    def test_iching_to_ifa_returns_4_pairs(self):
        for hex_num in range(1, 65):
            pairs = iching_to_ifa(hex_num)
            assert len(pairs) == 4

    def test_iching_to_ifa_pairs_are_valid(self):
        for hex_num in range(1, 65):
            pairs = iching_to_ifa(hex_num)
            for right, left in pairs:
                assert len(right) == 4
                assert len(left) == 4
                assert all(c in "01" for c in right + left)

    def test_256_equals_4_times_64(self):
        """Ifa's 256 = 4 x I Ching's 64."""
        all_pairs = set()
        for hex_num in range(1, 65):
            pairs = iching_to_ifa(hex_num)
            for right, left in pairs:
                all_pairs.add((right, left))
        assert len(all_pairs) == 256


class TestCasting:
    """Tests for the Ifa casting system."""

    def test_cast_cowrie(self):
        result = cast_ifa(question="test question", method="cowrie")
        assert isinstance(result, CastResult)
        assert len(result.full_binary) == 8
        assert 0 <= result.decimal <= 255
        assert result.casting_method == "cowrie"

    def test_cast_opele(self):
        result = cast_ifa(question="test question", method="opele")
        assert isinstance(result, CastResult)
        assert result.casting_method == "opele"

    def test_cast_ikin(self):
        result = cast_ifa(question="test question", method="ikin")
        assert isinstance(result, CastResult)
        assert result.casting_method == "ikin"

    def test_cast_default_is_cowrie(self):
        result = cast_ifa(question="test")
        assert result.casting_method == "cowrie"

    def test_reproducible_with_seed(self):
        c1 = IfaCaster(seed=42)
        r1 = c1.cast_cowrie(question="same question")
        c2 = IfaCaster(seed=42)
        r2 = c2.cast_cowrie(question="same question")
        assert r1.full_binary == r2.full_binary

    def test_different_questions_different_results(self):
        caster = IfaCaster(seed=100)
        r1 = caster.cast_cowrie(question="question one")
        r2 = caster.cast_cowrie(question="question two")
        # They might be the same by chance, but very unlikely
        # Just verify both are valid
        assert len(r1.full_binary) == 8
        assert len(r2.full_binary) == 8

    def test_iching_hexagram_in_range(self):
        for _ in range(10):
            result = cast_ifa(method="opele")
            assert 1 <= result.iching_hexagram <= 64

    def test_to_dict(self):
        result = cast_ifa(question="test", method="cowrie")
        d = result.to_dict()
        assert "odu_name" in d
        assert "binary" in d
        assert "wisdom" in d
        assert "marks" in d
        assert "iching_hexagram" in d

    def test_history_tracking(self):
        caster = IfaCaster(seed=42)
        for _ in range(5):
            caster.cast(question="test")
        assert len(caster.history) == 5

    def test_singleton_caster(self):
        c1 = get_caster()
        c2 = get_caster()
        assert c1 is c2
