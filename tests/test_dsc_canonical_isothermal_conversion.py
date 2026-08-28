from __future__ import annotations

from polynexus.core.canonical_experiments import convert_mettler_isothermal_text, default_converter_registry


def _fixture() -> str:
    rows: list[str] = ["Sample Weight: 5.95 mg", "Curve Values:"]
    index = 0
    for setpoint, duration, sample_offset in (
        (255.0, 70, 0.03),
        (180.0, 80, 0.08),
        (255.0, 70, 0.02),
        (181.0, 85, 0.06),
    ):
        for second in range(duration + 1):
            heat_flow = 1.0 + (20.0 / (second + 5) if setpoint < 200 else 0.0)
            rows.append(
                f"{index} {index} {setpoint + sample_offset:.3f} {setpoint:.3f} {heat_flow:.6f}"
            )
            index += 1
    return "\n".join(rows)


def test_converter_selects_lower_temperature_holds_and_keeps_melt_provenance() -> None:
    outcome = convert_mettler_isothermal_text(_fixture(), source_artifact_id="source-sha256")

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert [segment["setpoint_C"] for segment in outcome.template.payload["segments"]] == [180.0, 181.0]
    assert outcome.template.payload["sample"]["mass_mg"] == 5.95
    assert outcome.template.payload["segments"][0]["source_range"] == {
        "start_row": 71,
        "end_row": 151,
        "start_time_s": 71.0,
        "end_time_s": 151.0,
    }
    assert [entry["role"] for entry in outcome.record.excluded_segments] == ["melt_hold", "melt_hold"]


def test_dsc_registry_uses_generic_thermal_program_template(tmp_path) -> None:
    source = tmp_path / "pa6.txt"
    source.write_text(_fixture(), encoding="utf-8")

    outcome = default_converter_registry().convert_path(
        source,
        technique="dsc",
        source_artifact_id="source-sha256",
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "thermal_program.v1"
    assert outcome.template.payload["segments"][0]["role"] == "isothermal_crystallization"


def test_converter_keeps_monotonic_thermal_cycle_segments(tmp_path) -> None:
    rows = ["Sample:", "  PA6, 5.5 mg", "Curve Values:"]
    index = 0
    for temperature in range(25, 201):
        rows.append(f"{index} {index} {temperature:.3f} {temperature:.3f} 1.0")
        index += 1
    for temperature in range(200, 79, -1):
        rows.append(f"{index} {index} {temperature:.3f} {temperature:.3f} 1.0")
        index += 1

    from polynexus.core.canonical_experiments import convert_mettler_isothermal_text

    outcome = convert_mettler_isothermal_text(
        "\n".join(rows),
        source_artifact_id="source-sha256",
        template_id="thermal_program.v1",
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert [segment["role"] for segment in outcome.template.payload["segments"]] == [
        "heating", "cooling"
    ]
    assert outcome.template.payload["sample"]["mass_mg"] == 5.5


def test_converter_blocks_when_no_hold_reaches_minimum_duration() -> None:
    text = "\n".join(
        f"{index} {index} 180.05 180.0 1.0" for index in range(10)
    )

    outcome = convert_mettler_isothermal_text(text, source_artifact_id="source-sha256")

    assert outcome.status == "blocked"
    assert outcome.template is None
    assert outcome.reason_codes == ("conversion_no_qualified_isothermal_hold",)


def test_converter_blocks_malformed_numeric_columns() -> None:
    outcome = convert_mettler_isothermal_text("0 0 180.0 180.0\n", source_artifact_id="source-sha256")

    assert outcome.status == "blocked"
    assert outcome.reason_codes == ("conversion_columns_missing",)


def test_converter_blocks_a_malformed_five_column_measurement_row() -> None:
    outcome = convert_mettler_isothermal_text(
        "Sample Weight: 5.95 mg\n0 0 180.0 180.0 1.0\n1 1 not-a-number 180.0 1.0",
        source_artifact_id="source-sha256",
    )

    assert outcome.status == "blocked"
    assert outcome.reason_codes == ("conversion_numeric_row_invalid",)


def test_converter_excludes_hold_with_excessive_temperature_span() -> None:
    rows = [f"{index} {index} 255.03 255.0 1.0" for index in range(61)]
    rows.extend(
        f"{index} {index} {179.6 if index % 2 else 180.4} 180.0 1.0"
        for index in range(61, 122)
    )

    outcome = convert_mettler_isothermal_text("\n".join(rows), source_artifact_id="source-sha256")

    assert outcome.status == "blocked"
    assert outcome.reason_codes == ("conversion_no_qualified_isothermal_hold",)
    assert outcome.record.excluded_segments[-1]["reason"] == "sample_temperature_span_exceeds_tolerance"


def test_converter_excludes_high_frequency_temperature_oscillation() -> None:
    rows = [f"{index} {index} 255.03 255.0 1.0" for index in range(61)]
    rows.extend(
        f"{index} {index} {179.8 if index % 2 else 180.2} 180.0 1.0"
        for index in range(61, 122)
    )

    outcome = convert_mettler_isothermal_text("\n".join(rows), source_artifact_id="source-sha256")

    assert outcome.status == "blocked"
    assert outcome.record.excluded_segments[-1]["reason"] == "sample_temperature_noise_exceeds_tolerance"


def test_converter_excludes_narrow_high_frequency_temperature_oscillation() -> None:
    rows = [f"{index} {index} 255.03 255.0 1.0" for index in range(61)]
    rows.extend(
        f"{index} {index} {179.94 if index % 2 else 180.06} 180.0 1.0"
        for index in range(61, 122)
    )

    outcome = convert_mettler_isothermal_text("\n".join(rows), source_artifact_id="source-sha256")

    assert outcome.status == "blocked"
    assert outcome.record.excluded_segments[-1]["reason"] == "sample_temperature_noise_exceeds_tolerance"


def test_converter_accepts_material_temperature_without_fixed_200c_preparation() -> None:
    rows = [f"{index} {index} 180.02 180.0 1.0" for index in range(181)]
    rows.extend(
        f"{index} {index} 80.30 80.0 {1.0 + index / 1000:.6f}"
        for index in range(181, 482)
    )

    outcome = convert_mettler_isothermal_text(
        "\n".join(rows), source_artifact_id="source-sha256", template_id="thermal_program.v1"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert [segment["setpoint_C"] for segment in outcome.template.payload["segments"]] == [180.0, 80.0]


def test_converter_extracts_mettler_sample_block_mass_and_coalesces_ramps() -> None:
    text = "\n".join(
        [f"{index} {index} {80 + index / 3:.3f} {80 + index / 3:.3f} 1.0" for index in range(10)]
        + [f"{index} {index} 255.03 255.0 1.0" for index in range(10, 71)]
        + [f"{index} {index} 180.05 180.0 1.0" for index in range(71, 152)]
        + ["Sample:", "  PA6-DWJJ, 5.9500 mg"]
    )

    outcome = convert_mettler_isothermal_text(text, source_artifact_id="source-sha256")

    assert outcome.template is not None
    assert outcome.template.payload["sample"]["mass_mg"] == 5.95
    assert outcome.record.excluded_segments[0]["role"] == "ramp"
    assert outcome.record.excluded_segments[0]["source_range"]["start_row"] == 0
    assert outcome.record.excluded_segments[0]["source_range"]["end_row"] == 9
