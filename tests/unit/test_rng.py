"""Unit tests for SeededRNG manager."""

from backend.simulation.rng import SeededRNG


def test_rng_determinism():
    rng1 = SeededRNG(42)
    rng2 = SeededRNG(42)

    stream1 = rng1.get_stream("test_stream")
    stream2 = rng2.get_stream("test_stream")

    samples1 = [stream1.random() for _ in range(50)]
    samples2 = [stream2.random() for _ in range(50)]

    assert samples1 == samples2


def test_rng_isolated_child_streams():
    rng = SeededRNG(100)
    stream_a = rng.get_stream("stream_a")
    stream_b = rng.get_stream("stream_b")

    # Drawing from stream_a should not perturb the state of stream_b
    _ = [stream_a.random() for _ in range(20)]

    rng_replica = SeededRNG(100)
    _ = rng_replica.get_stream("stream_a")
    stream_b_replica = rng_replica.get_stream("stream_b")

    val_b = stream_b.random()
    val_b_replica = stream_b_replica.random()

    assert val_b == val_b_replica


def test_rng_reset():
    rng = SeededRNG(999)
    stream = rng.get_stream("demo")
    first_seq = [stream.randint(1, 1000) for _ in range(10)]

    rng.reset()
    stream_reset = rng.get_stream("demo")
    second_seq = [stream_reset.randint(1, 1000) for _ in range(10)]

    assert first_seq == second_seq

