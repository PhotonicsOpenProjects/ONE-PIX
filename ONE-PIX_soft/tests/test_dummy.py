# https://docs.pytest.org/en/7.4.x/getting-started.html#run-multiple-tests
class TestDummy:
    value = 0

    def test_one(self):
        self.value = 1
        assert self.value == 1

    def test_two(self):
        assert self.value == 0
