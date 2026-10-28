"""Buyurtma raqami YM-YYYY-NNNNNN: yil bo'yicha ketma-ket, atomar (javob Ж5)."""
from datetime import date

from django.test import TestCase

from apps.yashil.models import OrderSequence
from apps.yashil.services.numbering import next_order_number


class NumberingTest(TestCase):
    def test_first_number_of_year_and_increment(self):
        self.assertEqual(next_order_number(date(2027, 1, 11)), "YM-2027-000001")
        self.assertEqual(next_order_number(date(2027, 3, 1)), "YM-2027-000002")

    def test_sequence_restarts_each_year(self):
        next_order_number(date(2027, 12, 31))
        self.assertEqual(next_order_number(date(2028, 1, 1)), "YM-2028-000001")
        self.assertEqual(OrderSequence.objects.get(year=2027).last, 1)

    def test_numbers_are_never_reused(self):
        n1 = next_order_number(date(2027, 1, 1))
        OrderSequence.objects.filter(year=2027).update(last=5)
        n2 = next_order_number(date(2027, 1, 1))
        self.assertEqual((n1, n2), ("YM-2027-000001", "YM-2027-000006"))
