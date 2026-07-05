from polynexus.data.sample_db import SampleDB


def test_find_sample_by_name_matches_case_insensitively(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6", aliases=["nylon-6"])

    sample = db.find_sample_by_name("pa6")

    assert sample is not None
    assert sample["id"] == sample_id
    assert sample["polymer_name"] == "PA6"
