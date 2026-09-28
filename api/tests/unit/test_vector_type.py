from sqlalchemy.dialects import postgresql

from underwriteflow.persistence.vector import Vector


# Verify vectors serialize to PostgreSQL text and deserialize to floats.
def test_vector_binds_and_reads_float_lists() -> None:
    vector = Vector(3)
    dialect = postgresql.dialect()
    bind = vector.bind_processor(dialect)
    result = vector.result_processor(dialect, None)

    assert bind is not None
    assert result is not None
    assert bind([1.0, 2.5, 3.0]) == "[1.0,2.5,3.0]"
    assert result("[1,2.5,3]") == [1.0, 2.5, 3.0]
