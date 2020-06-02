import pytest
from assertpy import assert_that


@pytest.fixture
def int_queue(queue):
    queue.add_all(0, 1, 2)
    return queue


def test_none(queue):
    queue.add(None)

    assert_that(len(queue)).is_equal_to(0)
    assert_that(queue.next()).is_none()


def test_add(queue):
    assert_that(queue.add('any')).is_equal_to(1)

    assert_that(len(queue)).is_equal_to(1)
    assert_that(queue.next()).is_equal_to('any')


def test_order(int_queue):
    assert_that(int_queue.next()).is_equal_to(0)
    assert_that(int_queue.next()).is_equal_to(1)
    assert_that(int_queue.next()).is_equal_to(2)
    assert_that(int_queue.next()).is_none()


def test_slice(int_queue):
    assert_that(int_queue[-1]).is_equal_to(2)
    assert_that(int_queue[:2]).is_equal_to([0, 1])
    assert_that(int_queue[:5]).is_equal_to([0, 1, 2])


def test_last(int_queue):
    assert_that(int_queue.last()).is_none()

    for i in range(3):
        item = int_queue.next()
        assert_that(int_queue.last()).is_same_as(item)

    int_queue.forget()
    assert_that(int_queue.last()).is_none()


def test_memory(int_queue):
    assert_that(int_queue.memory()).is_empty()

    expected = []
    for i in range(3):
        expected.append(int_queue.next())
        assert_that(int_queue.memory()).is_equal_to(expected)

    int_queue.forget()
    assert_that(int_queue.memory()).is_empty()


def test_replace(int_queue):
    assert_that(int_queue.offer(3, lambda n: n == 1)).is_equal_to(2)
    assert_that(int_queue).is_equal_to([0, 3, 2])


def test_replace_first_match(int_queue):
    assert_that(int_queue.offer(3, lambda n: n > 1)).is_equal_to(3)
    assert_that(int_queue).is_equal_to([0, 1, 3])


def test_replace_no_match(int_queue):
    assert_that(int_queue.offer(3, lambda n: n > 2)).is_equal_to(4)
    assert_that(int_queue).is_equal_to([0, 1, 2, 3])


def test_replace_already_dumped(int_queue):
    item = int_queue.next()
    assert_that(int_queue.offer(item, lambda n: n > 1)).is_equal_to(0)  # cannot replace
    assert_that(int_queue.offer(item, lambda n: n > 2)).is_equal_to(0)  # cannot add
    assert_that(int_queue).is_equal_to([1, 2])


def test_replace_unique(int_queue):
    assert_that(int_queue.offer(0, lambda n: n > 1)).is_equal_to(-1)  # cannot replace
    assert_that(int_queue.offer(1, lambda n: n > 2)).is_equal_to(-2)  # cannot add


def test_bump(int_queue):
    assert_that(int_queue.bump(lambda n: n == 1)).is_true()
    assert_that(int_queue).is_equal_to([1, 0, 2])


def test_bump_first_match(int_queue):
    assert_that(int_queue.bump(lambda n: n > 1)).is_true()
    assert_that(int_queue).is_equal_to([2, 0, 1])


def test_bump_no_match(int_queue):
    assert_that(int_queue.bump(lambda n: n > 2)).is_false()
    assert_that(int_queue).is_equal_to([0, 1, 2])


def test_find(int_queue):
    assert_that(int_queue.find(lambda n: n > 0)).is_equal_to(2)
    assert_that(int_queue.find(lambda n: n > 1)).is_equal_to(2)
    assert_that(int_queue.find(lambda n: n > 2)).is_none()


def test_mandela(int_queue):
    int_queue.mandela(5)
    assert_that(int_queue.last()).is_equal_to(5)
    assert_that(int_queue.memory()).is_equal_to([5])

    int_queue.next()
    assert_that(int_queue.last()).is_equal_to(0)
    assert_that(int_queue.memory()).is_equal_to([5, 0])

    int_queue.mandela(6)
    assert_that(int_queue.last()).is_equal_to(6)
    assert_that(int_queue.memory()).is_equal_to([5, 6])
