from datetime import datetime
import unittest

from slack2zaim.functions.slack2zaim.src.main import get_date


class TestSlack2Zaim(unittest.TestCase):
    def test_get_dateに年月日をゼロ詰めなしで指定(self):
        actual = get_date('2018/1/1')
        self.assertEqual(datetime(2018, 1, 1), actual)

    def test_get_dateに年月日をゼロ詰めありで指定(self):
        actual = get_date('2018/01/01')
        self.assertEqual(datetime(2018, 1, 1), actual)

    def test_get_dateに月日をゼロ詰めなしで指定(self):
        today = datetime.today()
        actual = get_date('1/1')
        self.assertEqual(datetime(today.year, 1, 1), actual)

    def test_get_dateに年月をゼロ詰めありで指定(self):
        today = datetime.today()
        actual = get_date('01/01')
        self.assertEqual(datetime(today.year, 1, 1), actual)

    def test_get_dateに年月ではない値を指定(self):
        today = datetime.today()
        actual = get_date('python')
        # datetime.today()と比較すると、時分秒まで考慮されてしまうので、年・月・日をそれぞれ比較
        self.assertEqual(today.year, actual.year)
        self.assertEqual(today.month, actual.month)
        self.assertEqual(today.day, actual.day)


if __name__ == '__main__':
    unittest.main()
